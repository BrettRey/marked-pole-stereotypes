"""Mechanical fixtures only; no fixture is an empirical lexical observation."""
import copy
import json
import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile
from datetime import datetime, timezone

import requests

from production_evidence import (Retriever, _assemble_item, _retry_after, _collect, supplement_packet, digest,
    parse_wiktionary, select_forms, verify_pinned, build_packets, VERSION)


def page(text, title='fixture', revision=123):
    return {'title': title, 'pageid': 7, 'ns': 0, 'revisions': [{'revid': revision,
        'timestamp': '2026-10-11T00:00:00Z', 'slots': {'main': {'content': text}}}]}


def payload(pages, **extra):
    return {'query': {'pages': pages}, **extra}


class Response:
    def __init__(self, value, status=200, headers=None):
        self.value, self.status_code, self.headers = value, status, headers or {}
        self.content = json.dumps(value).encode()
        self.url = 'https://en.wiktionary.org/w/api.php?fixture=transport-test'

    def json(self):
        return self.value


class Session:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class Dictionary:
    def adjectives(self, word):
        return self.packet(word) if word.startswith('adj') else []

    def packet(self, word):
        return [{'sense_id': 'wn31:a:' + word, 'pos': 'a', 'gloss': 'fixture lexical evidence', 'lemmas': [word]}] if word.startswith('adj') else []


class ParserTests(unittest.TestCase):
    def test_nested_definitions_keep_hierarchy_and_exact_text(self):
        source = page('==French==\n===Adjective===\n# Not English.\n==English==\n===Etymology 1===\n====Adjective====\n# Outer [[meaning]].\n## {{lb|en|rare}} Inner meaning.\n##: an example\n# Second meaning.\n=====Translations=====\n* not a definition\n===Etymology 2===\n====Noun====\n# A noun.\n==German==\n===Adjective===\n# Not English either.')
        parsed = parse_wiktionary(source)
        self.assertTrue(parsed['parser_complete'])
        senses = parsed['definitions']
        self.assertEqual([s['pos'] for s in senses], ['a', 'a', 'a', 'n'])
        self.assertEqual(senses[1]['parent_sense_id'], senses[0]['sense_id'])
        self.assertEqual(senses[1]['definition_depth'], 2)
        self.assertEqual(senses[1]['etymology_heading']['title'], 'Etymology 1')
        self.assertEqual(senses[3]['etymology_heading']['title'], 'Etymology 2')
        self.assertEqual(senses[1]['unexpanded_templates'], ['lb'])
        self.assertEqual(senses[1]['source_text'], '## {{lb|en|rare}} Inner meaning.')
        self.assertEqual(senses[1]['gloss'], '{{lb|en|rare}} Inner meaning.')
        self.assertTrue(all(s['gloss'] in source['revisions'][0]['slots']['main']['content'] for s in senses))

    def test_comment_and_literal_blocks_do_not_attest_categories(self):
        text = '==English==\n<!--\n===Adjective===\n# Hidden.\n-->\n<nowiki>\n===Adjective===\n# Literal.\n</nowiki>\n===Noun===\n# An actual noun.'
        parsed = parse_wiktionary(page(text))
        self.assertTrue(parsed['parser_complete'])
        self.assertEqual([s['pos'] for s in parsed['definitions']], ['n'])
        self.assertEqual(parsed['definitions'][0]['source_line_start'], 11)

    def test_unknown_heading_is_retained_and_incomplete(self):
        parsed = parse_wiktionary(page('==English==\n===Unrecognized category===\n# Cannot silently omit.'))
        self.assertFalse(parsed['parser_complete'])
        self.assertEqual(parsed['definitions'][0]['pos'], 'unknown')
        self.assertIn('uncategorized_definition_at_line_3', parsed['parser_issues'])

    def test_no_english_and_category_without_definitions_are_not_negative_evidence(self):
        for text in ('==French==\n===Noun===\n# x', '==English==\n===Adjective===\n{{unparsed-transclusion}}'):
            self.assertFalse(parse_wiktionary(page(text))['parser_complete'])

    def test_subsection_does_not_inherit_category(self):
        parsed = parse_wiktionary(page('==English==\n===Adjective===\n# Meaning.\n====Usage notes====\n# This numbered note is not a sense.'))
        self.assertEqual([s['pos'] for s in parsed['definitions']], ['a', 'unknown'])
        self.assertFalse(parsed['parser_complete'])

    def test_orphan_multiline_and_unbalanced_markup(self):
        parsed = parse_wiktionary(page('==English==\n===Adjective===\n# {{form of|en|\nparticiple|term}}\n## Submeaning.'))
        self.assertTrue(parsed['parser_complete'])
        self.assertEqual(parsed['definitions'][0]['gloss'], '{{form of|en|\nparticiple|term}}')
        self.assertEqual(parsed['definitions'][0]['source_line_end'], 4)
        for text in ('==English==\n===Adjective===\n## Orphan.', '==English==\n===Adjective===\n# {{unclosed'):
            self.assertFalse(parse_wiktionary(page(text))['parser_complete'])

    def test_pinned_sources_are_exact_and_complete(self):
        result = verify_pinned()
        self.assertEqual(result['pinned_entries'], 21)
        self.assertEqual(result['definitions'], 129)
        self.assertEqual(result['statuses'], {'retrieved': 21})
        self.assertEqual(result['parser_issues'], {})


class RetrievalTests(unittest.TestCase):
    def test_normalization_redirects_and_case_are_explicit(self):
        target = page('==English==\n===Noun===\n# A fixture noun.', 'Target')
        answer = {'query': {'normalized': [{'from': 'alias_', 'to': 'alias '}],
            'redirects': [{'from': 'alias ', 'to': 'Target'}], 'pages': [target]}}
        session = Session(Response(answer))
        result = Retriever(session, persist=False).fetch_group(['alias_'])['alias_']
        self.assertEqual(result['status'], 'retrieved')
        self.assertEqual(result['requested_title'], 'alias_')
        self.assertEqual(result['returned_title'], 'Target')
        self.assertEqual(len(result['title_mappings']), 2)
        self.assertTrue(result['retrieval_complete'])
        request = session.calls[0][1]
        self.assertEqual(request['params']['maxlag'], 5)
        self.assertIn('github.com', request['headers']['User-Agent'])
        self.assertIn('gzip', request['headers']['Accept-Encoding'])

    def test_distinct_case_titles_never_silently_merge(self):
        lower = page('==English==\n===Noun===\n# Lower.', 'case', 1)
        upper = page('==English==\n===Proper noun===\n# Upper.', 'Case', 2)
        result = Retriever(Session(Response(payload([lower, upper]))), persist=False).fetch_group(['case', 'Case'])
        self.assertEqual(set(result), {'case', 'Case'})
        self.assertNotEqual(result['case']['parsed']['definitions'][0]['sense_id'], result['Case']['parsed']['definitions'][0]['sense_id'])

    def test_warning_or_unaccounted_title_prevents_completeness(self):
        p = page('==English==\n===Noun===\n# A noun.')
        warned = payload([p], warnings={'query': {'warnings': 'Truncated result'}})
        result = Retriever(Session(Response(warned)), persist=False).fetch_group(['fixture'])['fixture']
        self.assertEqual(result['status'], 'ambiguous')
        self.assertFalse(result['retrieval_complete'])
        self.assertEqual(len(result['parsed']['definitions']), 1)
        result = Retriever(Session(Response(payload([]))), persist=False).fetch_group(['fixture'])['fixture']
        self.assertEqual(result['status'], 'ambiguous')
        self.assertIn('requested_title_unaccounted', result['issues'])

    def test_unrequested_result_invalid_and_missing_revision(self):
        p = page('==English==\n===Noun===\n# A noun.')
        for pages in ([p, dict(p, title='extra')], [{'title': 'fixture', 'invalid': True}], [{'title': 'fixture', 'pageid': 7}]):
            result = Retriever(Session(Response(payload(pages))), persist=False).fetch_group(['fixture'])['fixture']
            self.assertEqual(result['status'], 'ambiguous')

    def test_explicit_missing_is_not_adjective_absence(self):
        result = Retriever(Session(Response(payload([{'title': 'fixture', 'missing': True}]))), persist=False).fetch_group(['fixture'])['fixture']
        self.assertEqual(result['status'], 'missing')
        form = {'word': 'fixture', 'form_id': 'id', 'original_spellings': ['fixture'], 'dictionary_lookup_alias': None, 'case_variant_group': False}
        item = _assemble_item(form, Dictionary(), {'fixture': result}, wn_source={'id': 'fixture-wordnet'})
        self.assertFalse(item['coverage']['review_complete'])
        self.assertTrue(item['coverage']['supplement_required'])

    def test_continuation_is_followed_and_complete_only_at_end(self):
        a = page('==English==\n===Noun===\n# A.', 'a', 1)
        b = page('==English==\n===Noun===\n# B.', 'b', 2)
        session = Session(Response(payload([a], **{'continue': {'continue': '||', 'rvcontinue': 'next'}})), Response(payload([b])))
        result = Retriever(session, persist=False).fetch_group(['a', 'b'])
        self.assertTrue(all(r['retrieval_complete'] for r in result.values()))
        self.assertEqual(session.calls[1][1]['params']['rvcontinue'], 'next')

    def test_repeated_continuation_preserves_evidence_but_blocks_completion(self):
        p = page('==English==\n===Adjective===\n# A.')
        fragment = payload([p], **{'continue': {'continue': '||', 'rvcontinue': 'same'}})
        result = Retriever(Session(Response(fragment), Response(fragment)), persist=False).fetch_group(['fixture'])['fixture']
        self.assertEqual(result['status'], 'ambiguous')
        self.assertFalse(result['retrieval_complete'])
        self.assertIn('repeated_continuation', result['issues'])
        self.assertEqual(len(result['parsed']['definitions']), 1)

    def test_transport_maximum_three_and_retry_after(self):
        sleeps = []
        session = Session(*[Response({'error': {'code': 'maxlag', 'lag': 6}}, headers={'Retry-After': '9'}) for _ in range(3)])
        result = Retriever(session, sleep=sleeps.append, persist=False).fetch_group(['fixture'])['fixture']
        self.assertEqual(len(session.calls), 3)
        self.assertEqual(sleeps, [9, 9, 9])
        self.assertEqual(result['status'], 'failed')
        session = Session(*[requests.Timeout('fixture timeout') for _ in range(3)])
        result = Retriever(session, sleep=lambda _: None, persist=False).fetch_group(['fixture'])['fixture']
        self.assertEqual(len(session.calls), 3)
        self.assertEqual(result['status'], 'failed')

    def test_nonretryable_http_does_not_repeat(self):
        session = Session(Response({'error': {'code': 'badvalue'}}, status=400))
        result = Retriever(session, persist=False).fetch_group(['fixture'])['fixture']
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(result['status'], 'failed')

    def test_group_limit_and_retry_after_date(self):
        retriever = Retriever(Session(), persist=False)
        for titles in ([], ['x'] * 2, [str(i) for i in range(51)], ['bad|title']):
            with self.assertRaises(ValueError):
                retriever.fetch_group(titles)
        self.assertEqual(_retry_after('Sun, 11 Oct 2026 00:01:00 GMT', datetime(2026, 10, 11, tzinfo=timezone.utc)), 60)


class SelectionTests(unittest.TestCase):
    def test_reproducible_balanced_homogeneous_and_excludes_pilot(self):
        forms = [{'form_id': f'lex-{prefix}-{i}', 'word': f'{prefix}{i}'} for prefix in ('adj', 'gap') for i in range(130)]
        excluded = {r['form_id'] for r in forms[:10]}
        first = select_forms(forms, excluded, Dictionary())
        second = select_forms(list(reversed(forms)), excluded, Dictionary())
        self.assertEqual(first, second)
        self.assertEqual(len(first['selection']), 200)
        self.assertEqual(len(first['packets']), 20)
        self.assertFalse(excluded & {r['item_id'] for r in first['selection']})
        for packet in first['packets']:
            self.assertEqual(len(packet['item_ids']), 10)
            self.assertEqual({r['stratum'] for r in first['selection'] if r['item_id'] in packet['item_ids']}, {packet['stratum']})
        for stratum in ('wordnet_adjective', 'category_gap'):
            self.assertEqual(sum(r['stratum'] == stratum for r in first['selection']), 100)

    def test_supported_adjective_survives_failed_required_supplement(self):
        form = {'word': 'adjfixture', 'form_id': 'id', 'original_spellings': ['Adjfixture'], 'dictionary_lookup_alias': 'adjalias', 'case_variant_group': True}
        cache = {'adjfixture': {'status': 'failed', 'retrieval_complete': False, 'parsed': None,
            'sources': [], 'issues': ['transport_failed'], 'title_mappings': [], 'returned_title': None}}
        initial = _assemble_item(form, Dictionary(), {}, wn_source={'id': 'fixture-wordnet'})
        result = _assemble_item(form, Dictionary(), cache, required=True, wn_source={'id': 'fixture-wordnet'})
        self.assertTrue(initial['coverage']['review_complete'])
        self.assertFalse(result['coverage']['review_complete'])
        self.assertEqual(initial['dictionary_senses'], result['dictionary_senses'])
        self.assertEqual(result['alias_dictionary_senses'][0]['lemmas'], ['adjalias'])
        self.assertEqual(result['lookup_mappings']['alias_is_same_lexical_identity'], 'not_assessed')
        self.assertEqual(set(result) & {'source_entries', 'source_rows', 'ratings', 'sources_membership'}, set())


class CollectionAndSupplementTests(unittest.TestCase):
    def test_frozen_initial_packets_ignore_later_augmented_cache(self):
        form = {'word': 'adjfixture', 'form_id': 'id', 'original_spellings': ['adjfixture'],
                'dictionary_lookup_alias': None, 'case_variant_group': False}
        selection = {'instrument_version': VERSION, 'packets': [
            {'packet_id': 'fixture-packet', 'stratum': 'wordnet_adjective', 'item_ids': ['id']} ]}
        dictionary = Dictionary()
        dictionary.license = 'Mechanical test fixture'
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            (out / 'selection.json').write_text(json.dumps(selection))
            with patch('production_evidence.prepare_selection', return_value=selection), patch('production_evidence.load_inputs', return_value=([form], set(), dictionary)), patch('production_evidence._read_cache', return_value={}) as read_cache, patch('production_evidence._wordnet_source', return_value={'id': 'fixture-wordnet'}):
                first = build_packets(out)
                initial_bytes = (out / 'packets/fixture-packet.json').read_bytes()
                # A later fixed-resource supplement changes the mutable cache.
                (out / 'cache.json').write_text(json.dumps({'adjfixture': {'status': 'retrieved',
                    'parsed': parse_wiktionary(page('==English==\n===Adjective===\n# Additional meaning.', 'adjfixture'))}}))
                read_cache.side_effect = AssertionError('Frozen packet loading must not inspect augmented cache')
                second = build_packets(out)
                self.assertEqual(first, second)
                self.assertEqual(initial_bytes, (out / 'packets/fixture-packet.json').read_bytes())
                self.assertEqual(read_cache.call_count, 1)
                self.assertEqual(second[0]['items'][0]['coverage']['supplement'], 'not_supplied')
                manifest_path = out / 'packet-manifest.json'
                manifest = json.loads(manifest_path.read_text())
                manifest['packet_composition'][0]['forms'] += 1
                manifest_path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, 'composition'):
                    build_packets(out)

    def test_systemic_failure_stops_and_latches_before_next_group(self):
        class FailedRetriever:
            def __init__(self):
                self.calls = 0
            def fetch_group(self, titles):
                self.calls += 1
                return {t: {'status': 'failed', 'issues': ['http_403', 'requested_title_unaccounted']} for t in titles}
        with tempfile.TemporaryDirectory() as folder:
            retriever = FailedRetriever()
            cache = {}
            titles = [f'fixture-{i}' for i in range(101)]
            result = _collect(titles, cache, Path(folder), 'mechanical_fixture', retriever)
            self.assertEqual(retriever.calls, 1)
            self.assertEqual(len(result['attempted_titles']), 50)
            self.assertEqual(len(result['unattempted_titles']), 51)
            self.assertIn('http_403', result['stop_reason'])
            again = _collect(titles, cache, Path(folder), 'mechanical_fixture', retriever)
            self.assertEqual(retriever.calls, 1)
            self.assertEqual(len(again['unattempted_titles']), 51)

    def test_missing_pages_do_not_stop_other_groups(self):
        class MissingRetriever:
            def __init__(self):
                self.calls = 0
            def fetch_group(self, titles):
                self.calls += 1
                return {t: {'status': 'missing', 'issues': []} for t in titles}
        with tempfile.TemporaryDirectory() as folder:
            retriever = MissingRetriever()
            result = _collect([f'fixture-{i}' for i in range(101)], {}, Path(folder), 'mechanical_fixture', retriever)
            self.assertEqual(retriever.calls, 3)
            self.assertFalse(result['unattempted_titles'])
            self.assertIsNone(result['stop_reason'])

    def test_failed_missing_and_repeated_supplements_do_not_change_evidence(self):
        form = {'word': 'adjfixture', 'form_id': 'id', 'original_spellings': ['adjfixture'],
                'dictionary_lookup_alias': None, 'case_variant_group': False}
        wn_source = {'id': 'fixture-wordnet'}
        original = {'packet_id': 'fixture-packet', 'stratum': 'wordnet_adjective',
                    'items': [_assemble_item(form, Dictionary(), {}, wn_source=wn_source)]}
        for status in ('failed', 'missing'):
            cache = {'adjfixture': {'status': status, 'retrieval_complete': status == 'missing',
                'parsed': None, 'sources': [], 'issues': ['transport_failed'] if status == 'failed' else [],
                'title_mappings': [], 'returned_title': 'adjfixture' if status == 'missing' else None}}
            with tempfile.TemporaryDirectory() as folder, patch('production_evidence.published_source', return_value='fixture-commit'), patch('production_evidence.load_inputs', return_value=([form], set(), Dictionary())), patch('production_evidence._read_cache', return_value=cache), patch('production_evidence._wordnet_source', return_value=wn_source), patch('production_evidence._collect'):
                result = supplement_packet(original, ['id'], out=Path(folder))
                self.assertFalse(result['changed'])
                self.assertFalse(result['packet']['items'][0]['coverage']['review_complete'])
                self.assertEqual(result['unavailable_item_ids'], ['id'])
        supplementary = parse_wiktionary(page('==English==\n===Adjective===\n# New supplied meaning.', 'adjfixture'))
        cache = {'adjfixture': {'status': 'retrieved', 'retrieval_complete': True, 'parsed': supplementary,
            'sources': [], 'issues': [], 'title_mappings': [], 'returned_title': 'adjfixture'}}
        with tempfile.TemporaryDirectory() as folder, patch('production_evidence.published_source', return_value='fixture-commit'), patch('production_evidence.load_inputs', return_value=([form], set(), Dictionary())), patch('production_evidence._read_cache', return_value=cache), patch('production_evidence._wordnet_source', return_value=wn_source), patch('production_evidence._collect'):
            augmented = supplement_packet(original, ['id'], out=Path(folder))
            self.assertTrue(augmented['changed'])
            repeated = supplement_packet(augmented['packet'], ['id'], out=Path(folder))
            self.assertFalse(repeated['changed'])
            self.assertEqual(repeated['unavailable_item_ids'], [])


if __name__ == '__main__':
    unittest.main()
