"""Apply source-verified corrections and freeze a source-stratified pilot packet."""
from __future__ import annotations

import collections
import json
import platform
import random
from pathlib import Path

from import_sources import ANDERSON, PRIVATE, RAW, ROOT, lexical_id, normalize, now, published_source, sha, write_json
from wordnet_source import WordNet

SEED = 20261010
PILOT = PRIVATE / 'pilot-20261010'
CHALLENGES = [
    'kind', 'unkind', 'friendly', 'unfriendly', 'patient', 'impatient',
    'happy', 'unhappy', 'valuable', 'invaluable', 'attentive', 'inattentive',
    'unattentive', 'care', 'careless', 'careful', 'uniform', 'uncouth', 'angry', 'cold',
    # Deterministic reserves if a primary challenge was drawn randomly.
    'unruly', 'wise', 'unwise', 'normal', 'abnormal', 'able', 'unable',
]
CASES = [
    {'case_id': 'simple', 'words': ['kind', 'unkind'], 'purpose': 'straightforward candidate affixation'},
    {'case_id': 'immediate_base', 'words': ['friendly', 'unfriendly'], 'purpose': 'pairing base is friendly, not friend'},
    {'case_id': 'cross_pos', 'words': ['patient', 'impatient'], 'purpose': 'adjective interpretation versus other uses and rating target'},
    {'case_id': 'sense_alignment', 'words': ['happy', 'unhappy'], 'purpose': 'multiple dictionary senses need compatible interpretation alignment'},
    {'case_id': 'semantic_nonopposition', 'words': ['valuable', 'invaluable'], 'purpose': 'apparent negation need not make opposing evaluated meanings'},
    {'case_id': 'shared_base', 'words': ['attentive', 'inattentive', 'unattentive'], 'purpose': 'one base with more than one affixed counterpart'},
    {'case_id': 'nominal_base', 'words': ['care', 'careless', 'careful'], 'purpose': 'nominal base and separately derived adjective opposite'},
    {'case_id': 'false_prefix', 'words': ['uniform'], 'purpose': 'initial letters do not establish negative affixation'},
    {'case_id': 'source_gap', 'words': ['uncouth'], 'purpose': 'check source absence separately from dictionary evidence for counterpart'},
    {'case_id': 'temporal', 'words': ['angry'], 'purpose': 'temporary state versus enduring disposition and temporal target'},
    {'case_id': 'physical_psychological', 'words': ['cold'], 'purpose': 'eligible interpretation need not share source word rating target'},
]


def detector(word, source_words, dictionary):
    results = []
    seen = set()
    for affix in ('non-', 'non', 'un', 'im', 'il', 'ir', 'in', 'dis'):
        if word.startswith(affix) and len(word) > len(affix)+1:
            base = word[len(affix):].lstrip('-')
            key = (affix.rstrip('-'), base)
            if key not in seen:
                results.append({'affix': affix.rstrip('-')+'-', 'base': base, 'method': 'prefix_string_candidate'})
                seen.add(key)
    if word.endswith('less') and len(word) > 5:
        results.append({'affix': '-less', 'base': word[:-4].rstrip('-'), 'method': 'suffix_string_candidate'})
    for candidate in results:
        base = candidate['base']
        candidate['base_in_sources'] = base in source_words
        candidate['base_in_dictionary'] = bool(dictionary.lookup(base))
        candidate['base_has_dictionary_adjective'] = bool(dictionary.adjectives(base))
        candidate['flags'] = []
        if not candidate['base_in_sources']:
            candidate['flags'].append('counterpart_absent_from_sources')
        if not candidate['base_in_dictionary']:
            candidate['flags'].append('counterpart_absent_from_dictionary')
        candidate['semantic_status'] = 'not_yet_coded'
    return results


def finalize_import():
    ar = json.loads((PRIVATE / 'import-v2/anderson_ocr_words.json').read_text())
    wr = json.loads((PRIVATE / 'import-v2/warriner_words.json').read_text())
    corrections = json.loads((ROOT / 'scripts/lexical_frame/anderson-corrections.json').read_text())
    if corrections['anderson_pdf_sha256'] != sha(ANDERSON):
        raise ValueError('Anderson source differs from inspected image source')
    patch = {r['source_entry_id']: r for r in corrections['corrections']}
    found = set()
    for row in ar:
        if row['source_entry_id'] in patch:
            change = patch[row['source_entry_id']]
            if row['ocr_word'] != change['before']:
                raise ValueError('OCR correction precondition failed: ' + row['source_entry_id'])
            row['original_word'] = change['after']
            row['normalized_word'] = normalize(change['after'])
            row['lexical_id'] = lexical_id(change['after'])
            row['correction_reason'] = change['reason']
            found.add(row['source_entry_id'])
        row['extraction_status'] = 'word_column_visually_verified'
    if found != set(patch) or len(ar) != 555:
        raise ValueError('Source accounting failed; do not force a 555-row frame')
    aliases = {r['printed']: r['dictionary_lookup_alias'] for r in corrections['printed_variants_preserved']}
    merged = {}
    for row in ar + wr:
        term = row['normalized_word']
        record = merged.setdefault(term, {'form_id': lexical_id(term), 'word': term,
                                         'source_entries': [], 'sources': set(), 'original_spellings': set()})
        record['source_entries'].append(row['source_entry_id'])
        record['sources'].add(row['source'])
        record['original_spellings'].add(row['original_word'])
    for term, record in merged.items():
        record['sources'] = sorted(record['sources'])
        record['original_spellings'] = sorted(record['original_spellings'])
        record['source_entries'].sort()
        record['case_variant_group'] = len({x.lower() for x in record['original_spellings']}) < len(record['original_spellings'])
        record['dictionary_lookup_alias'] = aliases.get(term)
    return ar, wr, merged, corrections


def select(merged):
    rng = random.Random(SEED)
    a = sorted(k for k, v in merged.items() if 'anderson1968' in v['sources'])
    random_a = rng.sample(a, 10)
    w = sorted(k for k, v in merged.items() if 'warriner2013' in v['sources'] and k not in random_a)
    random_w = rng.sample(w, 10)
    selected = random_a + random_w
    challenge = []
    for word in CHALLENGES:
        if word in merged and word not in selected:
            challenge.append(word)
            selected.append(word)
        if len(challenge) == 20:
            break
    if len(selected) != 40 or len(set(selected)) != 40:
        raise ValueError('Cannot build 40 distinct source terms under fixed rule')
    for case in CASES:
        if not set(case['words']).issubset(selected):
            raise ValueError(f'Challenge case incomplete: {case}')
    return random_a, random_w, challenge


def main():
    commit = published_source()
    if (PILOT / 'manifest.json').exists():
        raise FileExistsError('Pilot is already prepared; retain it and create an explicit new version')
    started = now()
    ar, wr, merged, corrections = finalize_import()
    dictionary = WordNet(RAW / 'wn3.1.dict.tar.gz')
    ra, rw, challenge = select(merged)
    records = []
    for stratum, words in [('random_anderson', ra), ('random_warriner', rw), ('challenge', challenge)]:
        for word in words:
            item = dict(merged[word])
            item['selection_stratum'] = stratum
            item['dictionary_senses'] = dictionary.packet(word)
            if item['dictionary_lookup_alias']:
                item['alias_senses'] = dictionary.packet(item['dictionary_lookup_alias'])
            records.append(item)
    records.sort(key=lambda r: r['word'])
    write_json(PILOT / 'source_entries.json', ar+wr)
    write_json(PILOT / 'all_candidate_forms.json', [merged[k] for k in sorted(merged)])
    write_json(PILOT / 'terms.json', records)
    write_json(PILOT / 'challenge_cases.json', CASES)
    # These detector decisions are not part of the coding or independent-audit packets.
    write_json(PILOT / 'detector_candidates.json', {r['word']: detector(r['word'], merged, dictionary) for r in records})
    (PILOT / 'WORDNET-LICENSE.txt').write_text(dictionary.license+'\n')
    a = {r['normalized_word'] for r in ar}; w = {r['normalized_word'] for r in wr}
    source_gaps = [r['word'] for r in records if not r['dictionary_senses']]
    no_adj = [r['word'] for r in records if not any(s['pos'] in ('a','s') for s in r['dictionary_senses'])]
    summary = {'anderson_rows': len(ar), 'anderson_normalized_forms': len(a),
               'warriner_rows': len(wr), 'warriner_normalized_forms': len(w),
               'overlap_normalized_forms': len(a&w), 'union_normalized_forms': len(a|w),
               'case_variant_groups': sum(r['case_variant_group'] for r in merged.values()),
               'ocr_corrections': len(corrections['corrections']),
               'printed_spelling_variants_retained': len(corrections['printed_variants_preserved']),
               'pilot_terms': len(records), 'pilot_by_stratum': dict(collections.Counter(r['selection_stratum'] for r in records)),
               'pilot_no_dictionary_entry': source_gaps, 'pilot_no_dictionary_adjective_sense': no_adj,
               'all_candidates_with_wordnet_adjective': sum(bool(dictionary.adjectives(k)) for k in merged),
               'no_predominant_pos_filter': True, 'ratings_exported': False, 'frame_frozen': False}
    manifest = {'started_at': started, 'completed_at': now(), 'seed': SEED, 'source_commit': commit,
                'python': platform.python_version(), 'summary': summary,
                'source_hashes': {'anderson_pdf': sha(ANDERSON), 'warriner_zip': sha(RAW/'warriner2013_esm.zip'),
                                  'wordnet_archive': sha(RAW/'wn3.1.dict.tar.gz')},
                'script_hashes': {p.name: sha(p) for p in (ROOT/'scripts/lexical_frame').glob('*.py')},
                'artifact_hashes': {p.name: sha(p) for p in PILOT.glob('*') if p.is_file()}}
    write_json(PILOT/'manifest.json', manifest)
    write_json(ROOT/'logs/lexical-frame-pilot-preparation-20261010.json', manifest)
    print(json.dumps(summary, indent=2))
    print('Random Anderson:', ra)
    print('Random Warriner:', rw)
    print('Challenge:', challenge)


if __name__ == '__main__':
    main()
