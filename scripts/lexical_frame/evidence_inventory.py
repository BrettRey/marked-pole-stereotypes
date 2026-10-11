"""Inventory existing lexical evidence without eligibility judgments or new retrievals."""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
import json
import math
import platform
from pathlib import Path

import requests

from import_sources import PRIVATE, RAW, ROOT, normalize, now, published_source, sha, write_json
from prepare_pilot import detector
from supplement_pilot import definitions
from wordnet_source import WordNet

SOURCE = PRIVATE / 'pilot-20261010'
OUT = PRIVATE / 'evidence-inventory-20261011'
FIELDS = {'case_variant_group', 'dictionary_lookup_alias', 'form_id',
          'original_spellings', 'source_entries', 'sources', 'word'}


def validate_forms(rows):
    if any(set(row) != FIELDS for row in rows):
        raise ValueError('Input is not the frozen vocabulary-only schema')
    for key in ('form_id', 'word'):
        if len({row[key] for row in rows}) != len(rows):
            raise ValueError(f'Duplicate {key}; do not force an inventory join')
    if any(normalize(row['word']) != row['word'] for row in rows):
        raise ValueError('Source normalization differs')


def distribution(values):
    values = sorted(values)
    if not values:
        return {'n': 0, 'total': 0, 'median': None, 'p95': None, 'maximum': None}
    n = len(values)
    return {'n': n, 'total': sum(values),
            'median': (values[(n-1)//2]+values[n//2])/2,
            'p95': values[math.ceil(.95*n)-1], 'maximum': values[-1]}


def cached_supplements(provenance):
    by_form = defaultdict(list)
    used = []
    for row in provenance:
        if not row['id'].startswith('lexical_wikt_'):
            continue
        path = ROOT / row['local_path']
        if path.parent != RAW / 'wiktionary' or sha(path) != row['sha256']:
            raise ValueError('Pinned supplementary source path/hash differs')
        if not all(row[key] for key in ('url', 'access_date', 'licence')):
            raise ValueError('Incomplete supplementary provenance')
        page = json.loads(path.read_text())
        revision = page['revisions'][0]
        by_form[normalize(page['title'])].append({
            'source_id': row['id'], 'source_url': row['url'],
            'revision_id': revision['revid'], 'revision_timestamp': revision['timestamp'],
            'sha256': row['sha256'], 'definitions': definitions(page)})
        used.append(row)
    return by_form, used


def inventory_row(form, dictionary, supplements):
    word = form['word']
    senses = dictionary.packet(word)
    alias = form['dictionary_lookup_alias']
    alias_senses = dictionary.packet(alias) if alias else []
    cached = supplements.get(word, [])
    adj = [s for s in senses if s['pos'] in ('a', 's')]
    cached_adj = [s for source in cached for s in source['definitions'] if s['pos'] in ('a', 's')]
    return {
        'source_form': form, 'wordnet_senses': senses,
        'alias_wordnet_senses': alias_senses, 'cached_wiktionary': cached,
        'coverage': {'wordnet_entry': bool(senses), 'wordnet_adjective': bool(adj),
                     'wordnet_sense_count': len(senses), 'wordnet_adjective_sense_count': len(adj),
                     'cached_supplement': bool(cached),
                     'cached_supplement_adjective': bool(cached_adj),
                     'category_gap_retrieval_pending': not adj and not cached,
                     'alias_adjective_evidence': any(s['pos'] in ('a', 's') for s in alias_senses)},
        'evidence_lengths': {
            'wordnet_adjective_gloss_characters': sum(len(s['gloss']) for s in adj),
            'cached_wiktionary_definition_characters': sum(len(s['gloss']) for source in cached for s in source['definitions'])},
        'inventory_adjudicates_eligibility': False,
        'broader_scope_and_alignment_trigger_assessment': 'not_performed_by_inventory',
        'lexical_identity_and_interpretation_grouping': 'not_performed_by_inventory',
    }


def main():
    commit = published_source()
    if OUT.exists():
        raise FileExistsError('Keep the first inventory; give any revision its own directory')
    started = now()
    source_file = SOURCE / 'all_candidate_forms.json'
    parent = json.loads((SOURCE / 'manifest.json').read_text())
    if sha(source_file) != parent['artifact_hashes'][source_file.name]:
        raise ValueError('Candidate forms differ from their frozen import')
    if sha(RAW / 'wn3.1.dict.tar.gz') != parent['source_hashes']['wordnet_archive']:
        raise ValueError('WordNet archive differs from the pilot input')
    forms = json.loads(source_file.read_text())
    validate_forms(forms)
    if len(forms) != parent['summary']['union_normalized_forms']:
        raise ValueError('Parent vocabulary count differs')
    with (ROOT / 'data/manifests/sources.csv').open(newline='') as stream:
        provenance = list(csv.DictReader(stream))
    dictionary = WordNet(RAW / 'wn3.1.dict.tar.gz')
    supplements, used_sources = cached_supplements(provenance)
    required = {'lexical_anderson1968_pdf', 'lexical_warriner2013_esm', 'lexical_wordnet31'}
    source_records = [r for r in provenance if r['id'] in required]
    if {r['id'] for r in source_records} != required:
        raise ValueError('Original input provenance is missing')
    expected = dict(zip(('lexical_anderson1968_pdf', 'lexical_warriner2013_esm', 'lexical_wordnet31'),
                        (parent['source_hashes'][key] for key in ('anderson_pdf', 'warriner_zip', 'wordnet_archive'))))
    for record in source_records:
        if record['sha256'] != expected[record['id']] or not all(record[k] for k in ('url', 'access_date', 'licence')):
            raise ValueError('Original source provenance differs or is incomplete')
    records = [inventory_row(row, dictionary, supplements) for row in sorted(forms, key=lambda r:r['word'])]
    by_word = {row['word']:row for row in forms}
    candidates = []
    for form in sorted(forms, key=lambda r:r['word']):
        for candidate in detector(form['word'], by_word, dictionary):
            base = by_word.get(candidate['base'])
            candidates.append(dict(candidate, form_id=form['form_id'], source_form=form['word'],
                                   base_form_id=base['form_id'] if base else None,
                                   both_members_have_direct_wordnet_adjective_evidence=bool(
                                       base and dictionary.adjectives(form['word']) and dictionary.adjectives(base['word'])),
                                   inventory_verifies_morphology_or_pair_eligibility=False))
    OUT.mkdir(parents=True)
    for name, rows in [('form-evidence.jsonl', records), ('string-candidates.jsonl', candidates)]:
        with (OUT / name).open('w') as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True)+'\n')
    write_json(OUT / 'sources.json', source_records+used_sources)
    (OUT / 'WORDNET-LICENSE.txt').write_text(dictionary.license+'\n')
    (OUT / 'WIKTIONARY-LICENSE.txt').write_text(
        'English Wiktionary contributors, CC BY-SA 4.0. Pinned entry URLs and revisions accompany each excerpt. '
        'Original wikitext definition lines are extracted; this does not preserve every entry distinction.\n')
    coverage = Counter(key for row in records for key, value in row['coverage'].items() if value is True)
    summary = {
        'candidate_forms':len(forms), 'source_rows':sum(len(row['source_entries']) for row in forms),
        'source_membership':dict(Counter('+'.join(row['sources']) for row in forms)),
        'case_variant_groups':sum(row['case_variant_group'] for row in forms),
        'forms_with_lookup_alias':sum(bool(row['dictionary_lookup_alias']) for row in forms),
        'forms_by_coverage':dict(coverage),
        'forms_without_direct_wordnet_adjective':len(forms)-coverage['wordnet_adjective'],
        'category_gap_with_cached_source_but_no_extracted_adjective':sum(
            not r['coverage']['wordnet_adjective'] and r['coverage']['cached_supplement']
            and not r['coverage']['cached_supplement_adjective'] for r in records),
        'direct_wordnet_adjective_evidence_rows':sum(r['coverage']['wordnet_adjective_sense_count'] for r in records),
        'distinct_direct_wordnet_adjective_sense_ids':len({s['sense_id'] for r in records for s in r['wordnet_senses'] if s['pos'] in ('a','s')}),
        'cached_wiktionary_sources':len(used_sources),
        'evidence_lengths':{key:distribution([r['evidence_lengths'][key] for r in records]) for key in records[0]['evidence_lengths']},
        'form_packet_utf8_bytes':distribution([len((json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n').encode()) for r in records]),
        'string_candidates':len(candidates),
        'string_candidates_with_both_source_forms':sum(c['base_in_sources'] for c in candidates),
        'string_candidates_with_both_direct_wordnet_adjectives':sum(c['both_members_have_direct_wordnet_adjective_evidence'] for c in candidates),
        'string_candidates_by_affix':dict(Counter(c['affix'] for c in candidates)),
        'dictionary_counts_are_eligibility_counts':False, 'sense_ids_are_lexical_units':False,
        'independent_pair_discovery_audit_complete':False,
        'new_retrievals':0, 'model_calls':0, 'rating_or_commonness_values_read':False,
        'frame_frozen':False,
    }
    manifest = {
        'started_at':started, 'completed_at':now(), 'source_commit':commit,
        'python':platform.python_version(), 'requests':requests.__version__, 'randomization':'none; deterministic sorting',
        'input_hashes':{str(p.relative_to(ROOT)):sha(p) for p in (
            source_file, SOURCE/'manifest.json', ROOT/'data/manifests/sources.csv', RAW/'wn3.1.dict.tar.gz',
            ROOT/'notes/lexical-protocol-decisions-2026-10-11.md', ROOT/'notes/next-stage-decisions-2026-10-11.md')},
        'script_hashes':{p.name:sha(p) for p in (ROOT/'scripts/lexical_frame').glob('*.py')},
        'artifact_hashes':{p.name:sha(p) for p in OUT.iterdir() if p.is_file()}, 'summary':summary,
    }
    write_json(OUT/'manifest.json',manifest)
    write_json(ROOT/'logs/lexical-evidence-inventory-20261011.json',manifest)
    print(json.dumps(summary,indent=2,sort_keys=True))


if __name__ == '__main__':
    main()
