"""Frozen vocabulary selection and pinned dictionary evidence for production v1.

No rating columns or detector outputs are read. Network entry points require
published lexical code; parser/selection tests and local inspection do not.
All mutable retrieval work is serialized by a process lock. Fixtures in the
companion tests exercise transport/parser behaviour, never replace source data.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import copy
import csv
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import fcntl
import hashlib
import json
import platform
import re
import time
from pathlib import Path
from urllib.parse import urlencode

import requests

from import_sources import PRIVATE, RAW, ROOT, now, published_source, register, sha, source_row, write_json
from wordnet_source import WordNet

VERSION = 'lexical-production-20261011-v1'
SOURCE = PRIVATE / 'pilot-20261010'
OUT = PRIVATE / 'production-20261011-v1'
RAW_OUT = RAW / 'production-20261011-v1'
API = 'https://en.wiktionary.org/w/api.php'
USER_AGENT = 'LexicalFrameProduction/1.0 (https://github.com/BrettRey/marked-pole-stereotypes/issues; academic dictionary research)'
LICENCE = 'English Wiktionary contributors; CC BY-SA 4.0; https://creativecommons.org/licenses/by-sa/4.0/'
RESPONSE_LICENCE = 'Wiktionary text where present: CC BY-SA 4.0; API metadata and transport-error responses retained for provenance; no blanket licence claim for error content'
FORM_FIELDS = {'case_variant_group', 'dictionary_lookup_alias', 'form_id', 'original_spellings', 'source_entries', 'sources', 'word'}
POS = {'Adjective': 'a', 'Noun': 'n', 'Proper noun': 'n', 'Verb': 'v', 'Adverb': 'r',
       'Pronoun': 'pronoun', 'Determiner': 'determiner', 'Article': 'article',
       'Preposition': 'preposition', 'Conjunction': 'conjunction', 'Interjection': 'interjection',
       'Numeral': 'numeral', 'Particle': 'particle', 'Prefix': 'prefix', 'Suffix': 'suffix',
       'Infix': 'infix', 'Affix': 'affix', 'Circumfix': 'circumfix', 'Combining form': 'combining_form',
       'Proverb': 'proverb', 'Phrase': 'phrase', 'Idiom': 'idiom', 'Symbol': 'symbol',
       'Letter': 'letter', 'Abbreviation': 'abbreviation', 'Contraction': 'contraction'}
HEADING = re.compile(r'^(={2,6})\s*(.*?)\s*\1\s*(?:<!--.*?-->\s*)?$')
DEFINITION = re.compile(r'^(#+)(?![:*#])\s*(\S.*)$')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _write_once(path, value):
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError(f'Frozen artifact differs: {path}')
    else:
        write_json(path, value)


def parse_wiktionary(page):
    """Return exact, line-addressed English definitions and explicit parser coverage.

    Raw wikitext is retained: no template expansion or lexical interpretation is
    invented. Nested definitions retain parent IDs. Categories/headings remain
    distinct even when their POS labels agree. Unknown-category definitions are
    retained with pos='unknown' and make parser completeness false.
    """
    issues, senses, headings = [], [], []
    revisions = page.get('revisions', [])
    if len(revisions) != 1:
        return {'definitions': [], 'headings': [], 'english_present': False,
                'parser_complete': False, 'parser_issues': ['expected_one_pinned_revision']}
    rev = revisions[0]
    content = rev.get('slots', {}).get('main', {}).get('content')
    if not isinstance(content, str) or not rev.get('revid') or not rev.get('timestamp'):
        return {'definitions': [], 'headings': [], 'english_present': False,
                'parser_complete': False, 'parser_issues': ['missing_revision_content_or_identity']}
    title = page.get('title', '')
    url = 'https://en.wiktionary.org/w/index.php?' + urlencode({'title': title, 'oldid': rev['revid']})
    lines = content.splitlines()
    # Commented or literal markup is not attested dictionary content. Preserve
    # offsets/newlines so accepted glosses still address exact original bytes.
    def blank_markup(match):
        return re.sub(r'[^\n]', ' ', match[0])
    masked = re.sub(r'<!--.*?(?:-->|\Z)', blank_markup, content, flags=re.S)
    masked = re.sub(r'<(nowiki|pre|syntaxhighlight)\b[^>]*>.*?(?:</\1\s*>|\Z)', blank_markup, masked, flags=re.S | re.I)
    if content.count('<!--') != content.count('-->'):
        issues.append('unbalanced_comment_markup')
    scan_lines = masked.splitlines()
    stack, parents, english_sections = [], {}, 0
    english = False
    index = 0
    while index < len(lines):
        line = lines[index]
        line_number = index + 1
        scan_line = scan_lines[index]
        heading = HEADING.match(scan_line)
        if heading:
            level, name = len(heading[1]), heading[2].strip()
            while stack and stack[-1]['level'] >= level:
                stack.pop()
            entry = {'level': level, 'title': name, 'line': line_number}
            stack.append(entry)
            if level == 2:
                english = name == 'English'
                if english:
                    english_sections += 1
            if english:
                headings.append(dict(entry, heading_path=[dict(h) for h in stack],
                                     category=POS.get(name)))
            parents = {}
            index += 1
            continue
        if not english:
            index += 1
            continue
        # A malformed heading must not let a subsequent category inherit silently.
        if scan_line.startswith('==') and not heading:
            issues.append(f'unparsed_heading_at_line_{line_number}')
            stack = [h for h in stack if h['level'] == 2]
            parents = {}
        definition = DEFINITION.match(scan_line)
        if definition:
            depth = len(definition[1])
            gloss = line[definition.start(2):]
            raw_lines = [line]
            # Preserve literal multiline templates/links/comments as one definition.
            def unfinished(text):
                return (text.count('{{') > text.count('}}') or text.count('[[') > text.count(']]')
                        or text.count('<!--') > text.count('-->'))
            while unfinished(gloss) and index + 1 < len(lines):
                candidate = lines[index + 1]
                if HEADING.match(candidate) or candidate.startswith('#'):
                    break
                index += 1
                raw_lines.append(candidate)
                gloss += '\n' + candidate
            local_issues = []
            if unfinished(gloss):
                issues.append(f'unbalanced_definition_markup_at_line_{line_number}')
                local_issues.append('unbalanced_markup')
            # POS applies only directly below the POS heading, not e.g. Translations.
            category = stack[-1] if stack and stack[-1]['title'] in POS else None
            if not category:
                issues.append(f'uncategorized_definition_at_line_{line_number}')
            sid = f"wikt:{rev['revid']}:en:L{line_number}"
            parent = parents.get(depth - 1) if depth > 1 else None
            if depth > 1 and not parent:
                issues.append(f'orphan_nested_definition_at_line_{line_number}')
            parents = {k: v for k, v in parents.items() if k < depth}
            parents[depth] = sid
            templates = sorted(set(re.findall(r'\{\{\s*([^{}|\n]+)', gloss)))
            if templates:
                local_issues.append('unexpanded_templates')
            senses.append({'sense_id': sid, 'pos': POS[category['title']] if category else 'unknown',
                           'lemmas': [title], 'gloss': gloss, 'source_text': '\n'.join(raw_lines),
                           'source_line_start': line_number, 'source_line_end': index + 1,
                           'definition_depth': depth, 'parent_sense_id': parent,
                           'heading_path': [dict(h) for h in stack],
                           'category_heading': dict(category) if category else None,
                           'etymology_heading': next((dict(h) for h in reversed(stack) if h['title'].startswith('Etymology')), None),
                           'source_url': url, 'revision_id': rev['revid'], 'revision_timestamp': rev['timestamp'],
                           'source': 'English Wiktionary', 'gloss_format': 'exact original wikitext',
                           'unexpanded_templates': templates, 'evidence_flags': local_issues})
        index += 1
    if not english_sections:
        issues.append('no_english_section')
    if english_sections > 1:
        issues.append('multiple_english_sections')
    category_lines = {h['line'] for h in headings if h['category']}
    represented = {s['category_heading']['line'] for s in senses if s['category_heading']}
    for missing in sorted(category_lines - represented):
        issues.append(f'category_without_extracted_definition_at_line_{missing}')
    return {'definitions': senses, 'headings': headings, 'english_present': bool(english_sections),
            'parser_complete': not issues, 'parser_issues': sorted(set(issues))}


def _provenance():
    with (ROOT / 'data/manifests/sources.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        if row['id'] == 'lexical_wordnet31' or row['id'].startswith('lexical_wikt_'):
            if not all(row.get(key) for key in ('url', 'access_date', 'sha256', 'licence', 'local_path')):
                raise ValueError(f'Incomplete dictionary provenance: {row["id"]}')
            if sha(ROOT / row['local_path']) != row['sha256']:
                raise ValueError(f'Pinned dictionary hash differs: {row["id"]}')
    return rows


def _public_source(row):
    return {key: row[key] for key in ('id', 'url', 'access_date', 'sha256', 'licence')}


def pinned_cache():
    """Read the 21 existing pinned entry inputs without normalizing their titles."""
    result = {}
    for row in _provenance():
        if not row['id'].startswith('lexical_wikt_'):
            continue
        path = ROOT / row['local_path']
        if path.parent != RAW / 'wiktionary':
            continue
        page = json.loads(path.read_text())
        parsed = parse_wiktionary(page)
        title = page['title']
        if title in result:
            raise ValueError(f'Multiple pinned revisions for title: {title}')
        result[title] = {'requested_title': title, 'returned_title': title, 'title_mappings': [],
                         'status': 'retrieved' if parsed['parser_complete'] else 'ambiguous',
                         'retrieval_complete': True, 'page': page, 'parsed': parsed,
                         'sources': [_public_source(row)], 'request_sources': [], 'issues': []}
    return result


def load_inputs():
    parent = json.loads((SOURCE / 'manifest.json').read_text())
    for filename in ('all_candidate_forms.json', 'terms.json'):
        if sha(SOURCE / filename) != parent['artifact_hashes'][filename]:
            raise ValueError(f'Frozen vocabulary input differs: {filename}')
    if sha(RAW / 'wn3.1.dict.tar.gz') != parent['source_hashes']['wordnet_archive']:
        raise ValueError('WordNet archive differs from frozen vocabulary import')
    forms = json.loads((SOURCE / 'all_candidate_forms.json').read_text())
    if any(set(row) != FORM_FIELDS for row in forms):
        raise ValueError('Vocabulary input contains fields outside the frozen vocabulary-only schema')
    if len({r['form_id'] for r in forms}) != len(forms) or len({r['word'] for r in forms}) != len(forms):
        raise ValueError('Duplicate vocabulary forms/IDs')
    # This existing packet contains vocabulary/dictionary evidence, no outcome data.
    excluded = {row['form_id'] for row in json.loads((SOURCE / 'terms.json').read_text())}
    return forms, excluded, WordNet(RAW / 'wn3.1.dict.tar.gz')


def select_forms(forms, excluded_ids, dictionary):
    """Pure deterministic balanced selection; unsuccessful forms are never replaced."""
    strata = {'wordnet_adjective': [], 'category_gap': []}
    for form in forms:
        if form['form_id'] in excluded_ids:
            continue
        stratum = 'wordnet_adjective' if dictionary.adjectives(form['word']) else 'category_gap'
        strata[stratum].append(form)
    selected, packets = [], []
    for stratum, prefix in (('wordnet_adjective', 'wnadj'), ('category_gap', 'gap')):
        ranked = sorted(strata[stratum], key=lambda r: (hashlib.sha256((VERSION + '|' + r['form_id']).encode()).hexdigest(), r['form_id']))
        if len(ranked) < 100:
            raise ValueError(f'Insufficient forms in {stratum}')
        for index, form in enumerate(ranked[:100]):
            packet_id = f'{prefix}-{index // 10 + 1:02d}'
            selected.append({'item_id': form['form_id'], 'word': form['word'], 'stratum': stratum,
                             'selection_rank': index + 1, 'packet_id': packet_id,
                             'rank_sha256': hashlib.sha256((VERSION + '|' + form['form_id']).encode()).hexdigest()})
        packets.extend({'packet_id': f'{prefix}-{i+1:02d}', 'stratum': stratum,
                        'item_ids': [r['form_id'] for r in ranked[i*10:(i+1)*10]]} for i in range(10))
    return {'instrument_version': VERSION, 'selection': selected, 'packets': packets,
            'stratum_available_after_pilot_exclusion': {s: len(r) for s, r in strata.items()},
            'pilot_excluded_count': len(excluded_ids), 'selection_rule': 'sha256(instrument_version + "|" + form_id)',
            'rating_or_commonness_values_read': False}


def prepare_selection(out=OUT):
    """Freeze 200 IDs and 20 homogeneous packet assignments; return selection dict."""
    forms, excluded, dictionary = load_inputs()
    selection = select_forms(forms, excluded, dictionary)
    selection['input_hashes'] = {name: sha(SOURCE / name) for name in ('all_candidate_forms.json', 'terms.json', 'manifest.json')}
    selection['wordnet_archive_sha256'] = sha(RAW / 'wn3.1.dict.tar.gz')
    _write_once(Path(out) / 'selection.json', selection)
    return selection


@contextmanager
def _serial_lock(out=OUT):
    Path(out).mkdir(parents=True, exist_ok=True)
    with (Path(out) / 'retrieval.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield
        fcntl.flock(stream, fcntl.LOCK_UN)


def _retry_after(value, current=None):
    if not value:
        return 0.0
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            return max(0.0, (parsedate_to_datetime(value) - (current or datetime.now(timezone.utc))).total_seconds())
        except (ValueError, TypeError):
            return 0.0


class Retriever:
    """Serial grouped MediaWiki retrieval; each HTTP request gets <=3 attempts.

    A successful status code is only transport success. Coverage remains
    incomplete on any warning, missing title/result/revision, broken mapping,
    unhandled continuation, or parser defect. Usable definitions are retained.
    """
    def __init__(self, session=None, sleep=time.sleep, raw_out=RAW_OUT, persist=True):
        self.session = session or requests.Session()
        self.sleep = sleep
        self.raw_out = Path(raw_out)
        self.persist = persist
        self.attempts = []

    def _save_response(self, response, params, group_id, sequence, attempt):
        raw = response.content
        raw_hash = hashlib.sha256(raw).hexdigest()
        record = {'http_status': response.status_code, 'sha256': raw_hash,
                  'url': getattr(response, 'url', None) or API + '?' + urlencode(params),
                  'group_id': group_id, 'sequence': sequence, 'attempt': attempt,
                  'retrieved_at': now(), 'retry_after': response.headers.get('Retry-After')}
        if self.persist:
            path = self.raw_out / 'responses' / f'{group_id}-{sequence:03d}-{attempt}-{raw_hash[:16]}.bin'
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_bytes(raw)
            row = source_row('lexical_prod_response_' + raw_hash, 'Wiktionary API response (including unsuccessful retrievals)',
                             API, '', path, RESPONSE_LICENCE,
                             'Original response bytes; exact request URL, requested-title/revision mappings and warning/continuation accounting remain in the private production cache. API endpoint only here to avoid publishing source vocabulary.')
            register(row)
            record['source'] = _public_source(row)
        return record

    def _request(self, params, group_id, sequence):
        attempts = []
        for attempt in range(1, 4):
            try:
                response = self.session.get(API, params=params,
                    headers={'User-Agent': USER_AGENT, 'Accept-Encoding': 'gzip, deflate'}, timeout=60)
                record = self._save_response(response, params, group_id, sequence, attempt)
                attempts.append(record)
                self.attempts.append(record)
                try:
                    payload = response.json()
                except ValueError:
                    payload = None
                error = payload.get('error', {}) if isinstance(payload, dict) else {}
                retryable = response.status_code in (429, 500, 502, 503, 504) or error.get('code') in ('maxlag', 'ratelimited', 'readonly')
                if 200 <= response.status_code < 300 and isinstance(payload, dict) and not error:
                    return payload, attempts, None
                detail = f'http_{response.status_code}' if not error else 'api_' + str(error.get('code', 'unknown'))
                if payload is None:
                    detail += '_invalid_json'
                if not retryable:
                    return None, attempts, detail
                delay = max(_retry_after(response.headers.get('Retry-After')), float(error.get('lag', 0) or 0), 2 ** attempt)
                # Honour the final provider delay before another group's request.
                self.sleep(delay)
                if attempt == 3:
                    return None, attempts, detail
            except (requests.RequestException, OSError) as exc:
                record = {'group_id': group_id, 'sequence': sequence, 'attempt': attempt,
                          'exception': type(exc).__name__, 'detail': str(exc), 'retrieved_at': now()}
                attempts.append(record)
                self.attempts.append(record)
                if attempt == 3:
                    return None, attempts, 'transport_failed'
                self.sleep(2 ** attempt)
        raise AssertionError('unreachable')

    def fetch_group(self, titles):
        """Return title->coverage record; caller serializes and records trigger first."""
        if not 1 <= len(titles) <= 50 or len(set(titles)) != len(titles):
            raise ValueError('Each group needs 1..50 distinct, unnormalized requested titles')
        if any('|' in title or '\n' in title for title in titles):
            raise ValueError('Invalid MediaWiki grouped title delimiter')
        group_id = digest(titles)[:16]
        base = {'action': 'query', 'prop': 'revisions', 'rvprop': 'ids|timestamp|content',
                'rvslots': 'main', 'titles': '|'.join(titles), 'redirects': 1,
                'format': 'json', 'formatversion': 2, 'maxlag': 5}
        continuation, seen_continuations, all_pages, mappings, warnings, attempts, issues = {}, set(), {}, [], [], [], []
        finished = False
        for sequence in range(1, 101):
            payload, records, failure = self._request(dict(base, **continuation), group_id, sequence)
            attempts.extend(records)
            if failure:
                issues.append(failure)
                break
            if payload.get('warnings'):
                warnings.append(payload['warnings'])
            query = payload.get('query')
            if not isinstance(query, dict) or not isinstance(query.get('pages'), list):
                issues.append('missing_query_pages')
                break
            for kind in ('normalized', 'converted', 'redirects'):
                for mapping in query.get(kind, []):
                    if not isinstance(mapping, dict) or 'from' not in mapping or 'to' not in mapping:
                        issues.append('invalid_title_mapping')
                    else:
                        mappings.append(dict(mapping, mapping_kind=kind))
            for page in query['pages']:
                title = page.get('title')
                if not isinstance(title, str):
                    issues.append('result_without_title')
                    continue
                if title in all_pages and all_pages[title] != page:
                    # Repeated continuation fragments may omit content or duplicate it.
                    old = all_pages[title]
                    old_revs = old.get('revisions', [])
                    new_revs = page.get('revisions', [])
                    if old_revs and new_revs and old_revs != new_revs:
                        issues.append('conflicting_page_revision_fragments:' + title)
                    elif new_revs:
                        all_pages[title] = page
                else:
                    all_pages[title] = page
            continuation = payload.get('continue')
            if not continuation:
                finished = True
                break
            if not isinstance(continuation, dict) or not all(isinstance(v, (str, int)) for v in continuation.values()):
                issues.append('invalid_continuation')
                break
            token = digest(continuation)
            if token in seen_continuations:
                issues.append('repeated_continuation')
                break
            seen_continuations.add(token)
        if not finished:
            issues.append('continuation_or_request_incomplete')
        if warnings:
            issues.append('api_warnings_require_review')
        edges = {}
        for mapping in mappings:
            if mapping['from'] in edges and edges[mapping['from']] != mapping['to']:
                issues.append('conflicting_title_mappings')
            edges[mapping['from']] = mapping['to']
        output, accounted = {}, set()
        for requested in titles:
            resolved, visited, chain = requested, set(), []
            local_issues = list(issues)
            while resolved in edges:
                if resolved in visited:
                    local_issues.append('title_mapping_cycle')
                    break
                visited.add(resolved)
                chain.extend(m for m in mappings if m['from'] == resolved)
                resolved = edges[resolved]
            page = all_pages.get(resolved)
            parsed = None
            if page is None:
                status = 'failed' if not finished else 'ambiguous'
                local_issues.append('requested_title_unaccounted')
            else:
                accounted.add(resolved)
                if 'missing' in page:
                    status = 'missing'
                elif 'invalid' in page:
                    status = 'ambiguous'
                    local_issues.append('invalid_title_result')
                else:
                    parsed = parse_wiktionary(page)
                    local_issues.extend(parsed['parser_issues'])
                    status = 'retrieved' if parsed['parser_complete'] and not local_issues else 'ambiguous'
            output[requested] = {'requested_title': requested, 'returned_title': resolved if page else None,
                'title_mappings': chain, 'status': status, 'retrieval_complete': finished and not issues and page is not None,
                'page': page, 'parsed': parsed, 'sources': [],
                'request_sources': [a['source'] for a in attempts if 'source' in a],
                'warnings': warnings, 'issues': sorted(set(local_issues)), 'transport_attempts': attempts}
        unaccounted = sorted(set(all_pages) - accounted)
        if unaccounted:
            for result in output.values():
                result['issues'].append('unrequested_result_pages:' + '|'.join(unaccounted))
                result['retrieval_complete'] = False
                if result['status'] == 'retrieved':
                    result['status'] = 'ambiguous'
        for result in output.values():
            page = result['page']
            if self.persist and page and page.get('revisions'):
                rev_id = page['revisions'][0].get('revid', 'unknown')
                path = self.raw_out / 'pages' / f'{digest(page)[:24]}-{rev_id}.json'
                _write_once(path, page)
                # Extracted pages are derived artifacts, not additional raw inputs.
                # Only complete API responses enter the public source registry.
                result['page_artifact'] = {'local_path': str(path.relative_to(ROOT)), 'sha256': sha(path),
                    'parent_response_source_ids': [r['id'] for r in result['request_sources']],
                    'pinned_url': 'https://en.wiktionary.org/w/index.php?' + urlencode({'title': page['title'], 'oldid': rev_id})}
                result['sources'] = result['request_sources']
        return output


def _read_cache(out=OUT):
    path = Path(out) / 'cache.json'
    if not path.exists():
        return pinned_cache()
    cache = json.loads(path.read_text())
    registry = {r['id']: r for r in _provenance()}
    unique_sources = {r['id']: r for e in cache.values() for r in e.get('sources', []) + e.get('request_sources', [])}
    parent_pages = {}
    for source in unique_sources.values():
        record = registry.get(source['id'])
        if not record or record['sha256'] != source['sha256'] or sha(ROOT / record['local_path']) != source['sha256']:
            raise ValueError('Cached retrieval source provenance differs')
        if source['id'].startswith('lexical_prod_response_'):
            try:
                response = json.loads((ROOT / record['local_path']).read_bytes())
                parent_pages[source['id']] = {digest(p) for p in response.get('query', {}).get('pages', [])}
            except (ValueError, AttributeError):
                parent_pages[source['id']] = set()
    for entry in cache.values():
        artifact = entry.get('page_artifact')
        if artifact:
            path = ROOT / artifact['local_path']
            if sha(path) != artifact['sha256']:
                raise ValueError('Derived cached page hash differs')
            if not set(artifact['parent_response_source_ids']) <= set(unique_sources):
                raise ValueError('Derived page lacks registered raw-response parents')
            page = json.loads(path.read_text())
            if not any(digest(page) in parent_pages.get(parent, set()) for parent in artifact['parent_response_source_ids']):
                raise ValueError('Derived page is absent from registered parent responses')
        else:
            page = entry.get('page')
            if page and entry.get('sources'):
                source = registry[entry['sources'][0]['id']]
                if json.loads((ROOT / source['local_path']).read_text()) != page:
                    raise ValueError('Cached page differs from registered source')
        if page and entry.get('parsed') != parse_wiktionary(page):
            raise ValueError('Cached extracted definitions differ from pinned page')
    return cache


def _log_trigger(out, record):
    path = Path(out) / 'retrieval-triggers.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as stream:
        stream.write(json.dumps(dict(record, recorded_at=now()), ensure_ascii=False, sort_keys=True) + '\n')
        stream.flush()


def _collect(titles, cache, out, trigger, retriever):
    missing = [title for title in dict.fromkeys(titles) if title not in cache]
    attempted, stop_reason = [], None
    stop_file = Path(out) / 'retrieval-stop.json'
    if stop_file.exists():
        stop = json.loads(stop_file.read_text())
        return {'attempted_titles': [], 'unattempted_titles': missing, 'stop_reason': stop['stop_reason']}
    for start in range(0, len(missing), 50):
        group = missing[start:start + 50]
        _log_trigger(out, {'trigger': trigger, 'requested_titles': group})
        result = retriever.fetch_group(group)
        # Full original pages live once under data/raw; cached extraction is small.
        for entry in result.values():
            if entry.get('page_artifact'):
                entry.pop('page', None)
        cache.update(result)
        attempted.extend(group)
        write_json(Path(out) / 'cache.json', cache)
        global_issues = set.intersection(*(set(r['issues']) for r in result.values())) if result else {'empty_group_result'}
        systemic = [issue for issue in sorted(global_issues) if
                    issue.startswith(('api_', 'http_', 'transport_', 'continuation_', 'invalid_continuation',
                                      'repeated_continuation', 'missing_query', 'conflicting_', 'unrequested_',
                                      'invalid_title_mapping', 'result_without_title'))]
        if systemic or (result and all(r['status'] == 'failed' for r in result.values())):
            stop_reason = ';'.join(systemic) or 'all_requested_titles_failed'
        write_json(Path(out) / 'retrieval-progress.json', {'updated_at': now(), 'trigger': trigger,
                   'completed_titles': len(attempted), 'queued_titles': len(missing),
                   'unattempted_titles': missing[start + len(group):], 'stop_reason': stop_reason,
                   'statuses': dict(Counter(r['status'] for r in cache.values()))})
        if stop_reason:
            write_json(stop_file, {'stopped_at': now(), 'trigger': trigger, 'stop_reason': stop_reason,
                       'failed_group_titles': group, 'unattempted_titles': missing[start + len(group):],
                       'resume_policy': 'Inspect and resolve the shared defect before explicitly clearing this stop; terminal title outcomes remain retained.'})
            break
    # Retain initial pinned inputs even when the requested queue is empty.
    write_json(Path(out) / 'cache.json', cache)
    return {'attempted_titles': attempted, 'unattempted_titles': [t for t in missing if t not in cache],
            'stop_reason': stop_reason}


def collect_category_gaps(out=OUT):
    """Retrieve the full fixed category-gap queue serially; return public counts.

    Existing terminal failures are retained rather than silently retried on resume.
    Interruptions resume only unattempted titles. Every trigger precedes retrieval.
    """
    commit = published_source()
    started = now()
    with _serial_lock(out):
        forms, _, dictionary = load_inputs()
        cache = _read_cache(out)
        titles = sorted(r['word'] for r in forms if not dictionary.adjectives(r['word']))
        cached_before = sum(t in cache for t in titles)
        retrieved = _collect(titles, cache, out, 'no_direct_wordnet_adjective', Retriever())
        summary = {'started_at': started, 'completed_at': now(), 'source_commit': commit,
                   'python': platform.python_version(), 'requests': requests.__version__,
                   'category_gap_forms': len(titles), 'already_cached': cached_before,
                   'new_title_attempts': len(retrieved['attempted_titles']),
                   'unattempted_titles': len(retrieved['unattempted_titles']), 'stop_reason': retrieved['stop_reason'],
                   'statuses': dict(Counter(cache[t]['status'] for t in titles if t in cache)),
                   'cache_sha256': sha(Path(out) / 'cache.json'), 'rating_or_commonness_values_read': False,
                   'script_sha256': sha(__file__)}
        write_json(Path(out) / 'category-gap-summary.json', summary)
        write_json(ROOT / 'logs/lexical-production-category-gaps-20261011.json', summary)
        return summary


def _wordnet_source():
    return next(_public_source(r) for r in _provenance() if r['id'] == 'lexical_wordnet31')


def _assemble_item(form, dictionary, cache, required=False, wn_source=None):
    senses = [dict(s, source='Princeton WordNet 3.1') for s in dictionary.packet(form['word'])]
    adjective = any(s['pos'] in ('a', 's') for s in senses)
    supplement = cache.get(form['word'])
    issues = []
    status = 'not_supplied'
    source_records = [wn_source or _wordnet_source()]
    headings, mappings = [], []
    if supplement:
        status = supplement['status']
        parsed = supplement.get('parsed')
        if parsed:
            senses.extend(parsed['definitions'])
            headings = parsed['headings']
        issues = list(supplement.get('issues', [])) + (parsed['parser_issues'] if parsed else [])
        source_records.extend(supplement['sources'])
        mappings = supplement['title_mappings']
    supplement_required = required or not adjective
    complete = ((not supplement_required) or bool(supplement and status == 'retrieved' and supplement['retrieval_complete'])) and not issues
    alias = form['dictionary_lookup_alias']
    return {'item_id': form['form_id'], 'word': form['word'], 'dictionary_senses': senses,
            'coverage': {'wordnet': 'present' if dictionary.packet(form['word']) else 'missing',
                         'supplement': status, 'supplement_required': supplement_required,
                         'review_complete': complete, 'parser_issues': sorted(set(issues))},
            'sources': source_records, 'category_evidence': headings,
            'lookup_mappings': {'original_spellings': form['original_spellings'],
                                'case_variant_group': form['case_variant_group'],
                                'dictionary_lookup_alias': alias,
                                'alias_is_same_lexical_identity': 'not_assessed',
                                'supplement_requested_title': form['word'] if supplement else None,
                                'supplement_returned_title': supplement.get('returned_title') if supplement else None,
                                'supplement_title_mappings': mappings},
            'alias_dictionary_senses': dictionary.packet(alias) if alias else []}


def _packet_composition(packets):
    return [{'packet_id': p['packet_id'], 'stratum': p['stratum'], 'forms': len(p['items']),
             'senses': sum(len(i['dictionary_senses']) for i in p['items']),
             'gloss_characters': sum(len(s['gloss']) for i in p['items'] for s in i['dictionary_senses'])}
            for p in packets]


def build_packets(out=OUT):
    """Return immutable initial packets, freezing them once after queue completion.

    Once the initial manifest exists, verify its selection, file hashes, ordered
    IDs, strata and composition. Later supplementary cache changes never rebuild
    or mutate initial evidence. Revised evidence belongs to the runner's separate
    packet round and cannot retroactively alter its initial-call denominator.
    """
    out = Path(out)
    selection = prepare_selection(out)
    manifest_path = out / 'packet-manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest.get('instrument_version') != VERSION or manifest.get('selection_sha256') != sha(out / 'selection.json'):
            raise ValueError('Initial packet manifest differs from frozen selection/instrument')
        expected_ids = [p['packet_id'] for p in selection['packets']]
        if set(manifest.get('packet_hashes', {})) != set(expected_ids) or len(set(expected_ids)) != len(expected_ids):
            raise ValueError('Initial packet manifest has missing, extra or duplicate packets')
        packets = []
        for specification in selection['packets']:
            packet_id = specification['packet_id']
            path = out / 'packets' / f'{packet_id}.json'
            if sha(path) != manifest['packet_hashes'][packet_id]:
                raise ValueError(f'Frozen initial packet hash differs: {packet_id}')
            packet = json.loads(path.read_text())
            if (packet.get('packet_id') != packet_id or packet.get('stratum') != specification['stratum']
                    or [i['item_id'] for i in packet.get('items', [])] != specification['item_ids']):
                raise ValueError(f'Frozen initial packet assignment differs: {packet_id}')
            packets.append(packet)
        if _packet_composition(packets) != manifest.get('packet_composition'):
            raise ValueError('Frozen initial packet composition differs from manifest')
        return packets
    forms, _, dictionary = load_inputs()
    cache = _read_cache(out)
    pending = [r['word'] for r in forms if not dictionary.adjectives(r['word']) and r['word'] not in cache]
    if pending:
        raise ValueError(f'Category-gap queue incomplete: {len(pending)} titles still unattempted')
    by_id = {r['form_id']: r for r in forms}
    source = _wordnet_source()
    packets = []
    for specification in selection['packets']:
        packet = {'packet_id': specification['packet_id'], 'stratum': specification['stratum'],
                  'items': [_assemble_item(by_id[item_id], dictionary, cache, wn_source=source) for item_id in specification['item_ids']]}
        _write_once(out / 'packets' / f'{packet["packet_id"]}.json', packet)
        packets.append(packet)
    (out / 'WORDNET-LICENSE.txt').write_text(dictionary.license + '\n')
    (out / 'WIKTIONARY-LICENSE.txt').write_text(LICENCE + '\nOriginal, unexpanded wikitext excerpts; pinned page/revision URLs accompany each definition.\n')
    _write_once(manifest_path, {'instrument_version': VERSION,
                'selection_sha256': sha(out / 'selection.json'),
                'packet_hashes': {p['packet_id']: sha(out / 'packets' / f'{p["packet_id"]}.json') for p in packets},
                'packet_composition': _packet_composition(packets)})
    return packets


def supplement_packet(packet, item_ids, out=OUT):
    """Supplement a locally synchronized request union; no repeated retrieval.

    Returns {packet, changed, requested_item_ids, unavailable_item_ids}. ``changed``
    concerns actual supplied lexical/category evidence, not request bookkeeping.
    The orchestrator freezes one result and dispatches at most one revised round.
    Existing fixed supplements, including terminal failures, are never requested
    again. Both judges receive the same resulting packet.
    """
    published_source()
    requested = sorted(set(item_ids))
    packet_ids = {i['item_id'] for i in packet['items']}
    if not set(requested) <= packet_ids:
        raise ValueError('Supplement requests contain IDs outside this packet')
    with _serial_lock(out):
        forms, _, dictionary = load_inputs()
        by_id = {r['form_id']: r for r in forms}
        cache = _read_cache(out)
        _log_trigger(out, {'trigger': 'broader_relevant_category_interpretation_or_identity',
                          'packet_id': packet['packet_id'], 'item_ids': requested,
                          'requested_titles': [by_id[i]['word'] for i in requested]})
        _collect([by_id[i]['word'] for i in requested], cache, out,
                 'broader_relevant_category_interpretation_or_identity', Retriever())
        augmented = copy.deepcopy(packet)
        source = _wordnet_source()
        for index, original in enumerate(packet['items']):
            if original['item_id'] in requested:
                augmented['items'][index] = _assemble_item(by_id[original['item_id']], dictionary, cache, True, source)
        def substantive(p):
            return [{'item_id': i['item_id'], 'dictionary_senses': i['dictionary_senses'],
                     'category_evidence': i.get('category_evidence', [])} for i in p['items']]
        return {'packet': augmented, 'changed': digest(substantive(packet)) != digest(substantive(augmented)),
                'requested_item_ids': requested,
                'unavailable_item_ids': [i['item_id'] for i in augmented['items'] if i['item_id'] in requested and not i['coverage']['review_complete']]}


def verify_pinned():
    cache = pinned_cache()
    if len(cache) != 21:
        raise ValueError(f'Expected 21 existing pinned entries, found {len(cache)}')
    for entry in cache.values():
        content = entry['page']['revisions'][0]['slots']['main']['content']
        for sense in entry['parsed']['definitions']:
            if sense['gloss'] not in content or sense['source_text'] not in content:
                raise ValueError('Extracted definition is not exact source text')
    return {'pinned_entries': len(cache), 'definitions': sum(len(e['parsed']['definitions']) for e in cache.values()),
            'statuses': dict(Counter(e['status'] for e in cache.values())),
            'parser_issues': {t: e['parsed']['parser_issues'] for t, e in cache.items() if e['parsed']['parser_issues']},
            'unexpanded_template_definitions': sum(bool(s['unexpanded_templates']) for e in cache.values() for s in e['parsed']['definitions'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('verify-pinned', 'selection', 'collect', 'packets'))
    args = parser.parse_args()
    if args.action == 'verify-pinned':
        result = verify_pinned()
    elif args.action == 'selection':
        published_source()
        result = prepare_selection()
        result = {'selected_forms': len(result['selection']), 'packets': len(result['packets']), 'selection_sha256': sha(OUT / 'selection.json')}
    elif args.action == 'collect':
        result = collect_category_gaps()
    else:
        published_source()
        packets = build_packets()
        result = {'packets': len(packets), 'forms': sum(len(p['items']) for p in packets)}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
