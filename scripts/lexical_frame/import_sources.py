"""Import source vocabulary with provenance; never print or export rating values."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import platform
import re
import subprocess
import tarfile
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data/raw/lexical_frame'
PRIVATE = ROOT / 'private/lexical_frame'
WARRINER_URL = 'https://media.springernature.com/original/springer-static/esm/art%3A10.3758%2Fs13428-012-0314-x/MediaObjects/13428_2012_314_MOESM1_ESM.zip'
WORDNET_URL = 'https://wordnetcode.princeton.edu/wn3.1.dict.tar.gz'
ANDERSON = ROOT / 'literature/anderson_1968_likableness_555_trait_words.pdf'


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n')


def normalize(word):
    value = unicodedata.normalize('NFKC', word).strip().lower()
    value = value.translate(str.maketrans({'–': '-', '—': '-', '‐': '-', '‑': '-', '’': "'"}))
    value = re.sub(r'\s*-\s*', '-', value)
    return re.sub(r'\s+', ' ', value)


def lexical_id(word):
    return 'lex-' + hashlib.sha256(normalize(word).encode()).hexdigest()[:12]


def published_source():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', 'scripts/lexical_frame'], cwd=ROOT, check=True)
    untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', 'scripts/lexical_frame'], cwd=ROOT, text=True)
    if untracked.strip():
        raise RuntimeError('Unpublished lexical-frame code exists')
    subprocess.run(['git', 'merge-base', '--is-ancestor', head, 'origin/master'], cwd=ROOT, check=True)
    return head


def download(url, target):
    target = Path(target)
    if target.exists():
        return {'cached': True, 'sha256': sha(target), 'bytes': target.stat().st_size}
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + '.partial')
    temp.write_bytes(response.content)
    temp.replace(target)
    return {'cached': False, 'sha256': sha(target), 'bytes': target.stat().st_size,
            'resolved_url': response.url, 'content_type': response.headers.get('content-type')}


def register(row):
    path = ROOT / 'data/manifests/sources.csv'
    with path.open(newline='') as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        matches = [r for r in reader if r['id'] == row['id']]
    if matches:
        if matches[0]['sha256'] != row['sha256']:
            raise RuntimeError('Source id already registered with different hash: ' + row['id'])
        return
    with path.open('a', newline='') as handle:
        csv.DictWriter(handle, fieldnames=fields, lineterminator='\n').writerow(row)


def source_row(source_id, description, url, doi, path, licence, notes):
    return {'id': source_id, 'description': description, 'url': url, 'doi': doi,
            'access_date': now()[:10], 'sha256': sha(path), 'licence': licence,
            'local_path': str(Path(path).relative_to(ROOT)), 'status': 'downloaded; vocabulary import only',
            'notes': notes}


def fetch():
    results = {}
    for key, url, filename in [('warriner2013_esm', WARRINER_URL, 'warriner2013_esm.zip'),
                               ('wordnet31', WORDNET_URL, 'wn3.1.dict.tar.gz')]:
        results[key] = download(url, RAW / filename)
    register(source_row('lexical_anderson1968_pdf', 'Anderson (1968) original table of 555 personality descriptors',
                        'https://doi.org/10.1037/h0025907', '10.1037/h0025907', ANDERSON,
                        'Copyright APA; no redistribution permission established',
                        'Existing portfolio PDF supplied before this stage; accessed locally. This access date is not a claimed original download date. Vocabulary only; no ratings exported.'))
    register(source_row('lexical_warriner2013_esm', 'Warriner et al. (2013) publisher electronic supplement',
                        WARRINER_URL, '10.3758/s13428-012-0314-x', RAW / 'warriner2013_esm.zip',
                        'Publisher publicly downloadable supplement; licence inspection pending; no redistribution assumed',
                        'Original publisher archive; vocabulary-only export for eligibility coding.'))
    register(source_row('lexical_wordnet31', 'Princeton WordNet 3.1 dictionary archive', WORDNET_URL, '',
                        RAW / 'wn3.1.dict.tar.gz', 'Princeton WordNet licence in archive; attribution required',
                        'Pinned source bytes; sense identifiers are evidence identifiers, not automatically study units.'))
    return results


def inventory():
    with zipfile.ZipFile(RAW / 'warriner2013_esm.zip') as archive:
        zip_inventory = [{'name': i.filename, 'bytes': i.file_size} for i in archive.infolist()]
        headers = {}
        for name in archive.namelist():
            if name.lower().endswith('.csv'):
                with archive.open(name) as h:
                    row = next(csv.reader(io.TextIOWrapper(h, encoding='utf-8-sig')))
                    headers[name] = row
    with tarfile.open(RAW / 'wn3.1.dict.tar.gz') as archive:
        tar_inventory = [{'name': i.name, 'bytes': i.size} for i in archive.getmembers() if i.isfile()]
    return {'warriner_members': zip_inventory, 'warriner_headers': headers, 'wordnet_members': tar_inventory}


def read_warriner():
    rows = []
    with zipfile.ZipFile(RAW / 'warriner2013_esm.zip') as archive:
        candidates = [name for name in archive.namelist() if name.lower().endswith('.csv') and not name.startswith('__MACOSX/')]
        if len(candidates) != 1:
            raise ValueError(f'Expected one original vocabulary CSV; found {candidates}')
        name = candidates[0]
        raw = archive.read(name)
        reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        word_fields = [f for f in reader.fieldnames or [] if f.lower() in ('word', 'lemma')]
        if len(word_fields) != 1:
            raise ValueError('Cannot uniquely identify source word column')
        for i, row in enumerate(reader, 2):
            word = row[word_fields[0]]
            if not word.strip():
                raise ValueError(f'Empty source word at CSV row {i}')
            rows.append({'source': 'warriner2013', 'source_entry_id': f'warriner2013:{i}',
                         'source_member': name, 'source_row': i, 'original_word': word,
                         'normalized_word': normalize(word), 'lexical_id': lexical_id(word)})
    return rows, {'member': name, 'member_sha256': hashlib.sha256(raw).hexdigest(), 'columns': reader.fieldnames}


def anderson_ocr():
    xml_path = RAW / 'anderson_table_bbox.xml'
    subprocess.run(['pdftotext', '-f', '2', '-l', '6', '-bbox-layout', str(ANDERSON), str(xml_path)], check=True)
    pages = ET.parse(xml_path).findall('.//{*}page')
    records = []
    for page_number, page in enumerate(pages, 2):
        words = page.findall('.//{*}word')
        headers = [w for w in words if w.text == 'Word' and 80 < float(w.attrib['yMin']) < 120
                   and (115 < float(w.attrib['xMin']) < 140 or 315 < float(w.attrib['xMin']) < 340)]
        if len(headers) != 2:
            raise ValueError(f'Cannot identify both word columns on PDF page {page_number}')
        for column, header in enumerate(sorted(headers, key=lambda w: float(w.attrib['xMin'])), 1):
            left = float(header.attrib['xMin']) - 28
            right = float(header.attrib['xMin']) + 51
            top = float(header.attrib['yMax']) + 1
            bottom = 647 if page_number < 6 else 295
            candidates = [w for w in words if left <= float(w.attrib['xMin']) < right
                          and top < float(w.attrib['yMin']) < bottom
                          and float(w.attrib['yMax']) - float(w.attrib['yMin']) <= 9
                          and re.search('[A-Za-z]', w.text or '')]
            lines = []
            for word in sorted(candidates, key=lambda w: (float(w.attrib['yMin']), float(w.attrib['xMin']))):
                y = float(word.attrib['yMin'])
                if lines and abs(y-lines[-1][0]) < 2:
                    lines[-1][1].append(word)
                else:
                    lines.append((y, [word]))
            for row_in_column, (y, terms) in enumerate(lines, 1):
                raw = ' '.join(w.text or '' for w in sorted(terms, key=lambda w: float(w.attrib['xMin'])))
                records.append({'source': 'anderson1968', 'source_entry_id': f'anderson1968:p{page_number}:c{column}:r{row_in_column}',
                                'pdf_page': page_number, 'printed_page': page_number+271, 'column': column,
                                'row_in_column': row_in_column, 'y_min': y, 'word_left': left, 'word_right': right,
                                'ocr_word': raw, 'original_word': raw, 'normalized_word': normalize(raw),
                                'lexical_id': lexical_id(raw), 'extraction_status': 'requires_image_verification'})
    return records


def import_words():
    wr, info = read_warriner()
    ar = anderson_ocr()
    write_json(PRIVATE / 'import-v1/warriner_words.json', wr)
    write_json(PRIVATE / 'import-v1/anderson_ocr_words.json', ar)
    words = {r['normalized_word'] for r in wr}
    summary = {'warriner_entries': len(wr), 'warriner_unique_normalized': len(words),
               'anderson_ocr_rows_pending_verification': len(ar),
               'anderson_rows_by_page_column': {f'{p}-{c}': sum(r['pdf_page']==p and r['column']==c for r in ar) for p in range(2,7) for c in (1,2)},
               'warriner_columns_imported': ['Word'], 'warriner_member': info,
               'ratings_exported': False, 'frame_frozen': False}
    write_json(PRIVATE / 'import-v1/summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['fetch', 'inventory', 'import'])
    args = parser.parse_args()
    commit = published_source()
    started = now()
    RAW.mkdir(parents=True, exist_ok=True)
    result = {'fetch': fetch, 'inventory': inventory, 'import': import_words}[args.action]()
    log = {'started_at': started, 'finished_at': now(), 'action': args.action, 'source_commit': commit,
           'script_sha256': sha(__file__), 'python': platform.python_version(), 'platform': platform.platform(),
           'requests_version': requests.__version__, 'result': result}
    output = ROOT / 'logs' / f'lexical-frame-{args.action}-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}.json'
    write_json(output, log)
    print(json.dumps(result, indent=2))
    print('Log:', output.relative_to(ROOT))


if __name__ == '__main__':
    main()
