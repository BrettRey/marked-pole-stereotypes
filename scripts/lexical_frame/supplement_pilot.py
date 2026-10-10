"""A fixed secondary-resource route for every pilot word with no WordNet adjective."""
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlencode

import requests

from import_sources import PRIVATE, RAW, ROOT, now, published_source, register, sha, source_row, write_json
from wordnet_source import WordNet

SOURCE = PRIVATE / 'pilot-20261010'
TARGET = PRIVATE / 'pilot-20261010-v2'
POS = {'Adjective': 'a', 'Noun': 'n', 'Proper noun': 'n', 'Verb': 'v', 'Adverb': 'r'}


def definitions(page):
    rev = page['revisions'][0]
    text = rev['slots']['main']['content']
    match = re.search(r'^==English==\s*\n(.*?)(?=^==[^=].*?==\s*$|\Z)', text, re.M | re.S)
    if not match:
        return []
    output, current, ordinal = [], None, 0
    for line in match[1].splitlines():
        heading = re.match(r'^(={3,})([^=]+)\1\s*$', line)
        if heading:
            name = heading[2].strip()
            # Subsections such as Usage notes must not enter coding input.
            current = POS.get(name)
        definition = re.match(r'^#+ (.+)$', line)
        if current and definition:
            ordinal += 1
            output.append({'sense_id': f"wikt:{rev['revid']}:en:{current}:{ordinal}",
                           'pos': current, 'lemmas': [page['title']], 'gloss': definition[1],
                           'source_url': f"https://en.wiktionary.org/w/index.php?title={page['title']}&oldid={rev['revid']}",
                           'revision_id': rev['revid'], 'revision_timestamp': rev['timestamp'],
                           'source': 'English Wiktionary', 'gloss_format': 'original wikitext definition; usage notes omitted'})
    return output


def main():
    commit = published_source()
    if TARGET.exists():
        raise FileExistsError('Retain existing supplementary packet; do not silently replace it')
    dictionary = WordNet(RAW / 'wn3.1.dict.tar.gz')
    terms = json.loads((SOURCE/'terms.json').read_text())
    requested = sorted(r['word'] for r in terms if not dictionary.adjectives(r['word']))
    params = {'action': 'query', 'prop': 'revisions', 'rvprop': 'ids|timestamp|content',
              'rvslots': 'main', 'titles': '|'.join(requested), 'format': 'json', 'formatversion': 2}
    url = 'https://en.wiktionary.org/w/api.php?' + urlencode(params)
    response = requests.get(url, headers={'User-Agent': 'LexicalFramePilot/0.1 (academic source verification)'}, timeout=45)
    response.raise_for_status()
    payload = response.json()
    raw_path = RAW/'wiktionary-pilot-gaps-20261010.json'
    if raw_path.exists():
        raise FileExistsError('Pinned source response already exists')
    raw_path.write_bytes(response.content)
    pages = {r['title']: r for r in payload['query']['pages']}
    source_records = []
    for title in requested:
        page = pages.get(title)
        if not page or 'revisions' not in page:
            source_records.append({'word': title, 'status': 'missing', 'definitions': []})
            continue
        path = RAW/'wiktionary'/f'{title}.json'
        write_json(path, page)
        revision = page['revisions'][0]
        source_url = f"https://en.wiktionary.org/w/index.php?title={title}&oldid={revision['revid']}"
        register(source_row('lexical_wikt_'+title, f'English Wiktionary entry {title}, revision {revision["revid"]}',
                            source_url, '', path, 'Wiktionary text: CC BY-SA 4.0; retain attribution and share-alike notice',
                            'Pilot supplement selected because WordNet had no adjective sense; original English definition text retained; usage notes omitted from coding packet.'))
        source_records.append({'word': title, 'status': 'retrieved', 'revision_id': revision['revid'],
                               'source_url': source_url, 'sha256': sha(path), 'definitions': definitions(page)})
    by_word = {r['word']: r for r in source_records}
    TARGET.mkdir(parents=True)
    for filename in ('source_entries.json', 'all_candidate_forms.json', 'challenge_cases.json', 'detector_candidates.json', 'WORDNET-LICENSE.txt'):
        shutil.copy2(SOURCE/filename, TARGET/filename)
    for term in terms:
        term['dictionary_senses'] = dictionary.packet(term['word'])
        term['supplement'] = by_word.get(term['word'])
        if term['supplement']:
            term['dictionary_senses'].extend(term['supplement']['definitions'])
    write_json(TARGET/'terms.json', terms)
    write_json(TARGET/'supplementary_sources.json', source_records)
    (TARGET/'WIKTIONARY-LICENSE.txt').write_text('Definition text is from English Wiktionary contributors under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). Entry URLs and pinned revisions are in supplementary_sources.json. Original wikitext definition lines are excerpted; usage notes and examples are omitted. No claim is made that the extraction preserves every distinction in the full entry.\n')
    original_manifest = json.loads((SOURCE/'manifest.json').read_text())
    all_forms = json.loads((TARGET/'all_candidate_forms.json').read_text())
    summary = dict(original_manifest['summary'])
    summary['all_candidates_with_wordnet_adjective'] = sum(bool(dictionary.adjectives(x['word'])) for x in all_forms)
    summary['supplement_requested'] = requested
    summary['supplement_no_adjective_definition'] = [r['word'] for r in terms if not any(s['pos'] in ('a','s') for s in r['dictionary_senses'])]
    summary['supplement_missing_entries'] = [r['word'] for r in source_records if r['status']=='missing']
    manifest = {'created_at': now(), 'source_commit': commit, 'seed': original_manifest['seed'],
                'parent_manifest_sha256': sha(SOURCE/'manifest.json'), 'summary': summary,
                'supplement_raw_sha256': sha(raw_path), 'source_hashes': original_manifest['source_hashes'],
                'script_hashes': {p.name: sha(p) for p in (ROOT/'scripts/lexical_frame').glob('*.py')},
                'artifact_hashes': {p.name: sha(p) for p in TARGET.glob('*') if p.is_file()}}
    write_json(TARGET/'manifest.json', manifest)
    write_json(ROOT/'logs/lexical-frame-pilot-supplement-20261010.json', manifest)
    print(json.dumps(summary, indent=2))
    print('Supplementary definition counts:', {r['word']: len(r['definitions']) for r in source_records})


if __name__ == '__main__':
    main()
