import unittest
from import_sources import lexical_id, normalize
from prepare_pilot import detector


class DictionaryFixture:
    def lookup(self, word):
        return [word] if word in {'friendly', 'care', 'confident'} else []

    def adjectives(self, word):
        return [word] if word in {'friendly', 'confident'} else []


class NormalizationTests(unittest.TestCase):
    def test_reversible_scope(self):
        self.assertEqual(normalize('  Self ‑ controlled  '), 'self-controlled')
        self.assertEqual(normalize('PATIENT'), 'patient')
        self.assertNotEqual(lexical_id('friendly'), lexical_id('unfriendly'))
        self.assertNotEqual(normalize('not friendly'), normalize('unfriendly'))
        self.assertNotEqual(normalize('care'), normalize('careful'))

    def test_ids_independent_of_order(self):
        self.assertEqual(lexical_id('Kind'), lexical_id('kind'))
        self.assertEqual(lexical_id('self‑controlled'), lexical_id('self-controlled'))

    def test_base_not_root(self):
        result = detector('unfriendly', {'friendly'}, DictionaryFixture())
        self.assertEqual(result[0]['base'], 'friendly')
        self.assertEqual(result[0]['semantic_status'], 'not_yet_coded')

    def test_source_and_dictionary_absence_are_separate(self):
        source_gap = detector('unfriendly', set(), DictionaryFixture())[0]
        self.assertEqual(source_gap['flags'], ['counterpart_absent_from_sources'])
        dictionary_gap = detector('uniform', {'iform'}, DictionaryFixture())[0]
        self.assertEqual(dictionary_gap['flags'], ['counterpart_absent_from_dictionary'])

    def test_nominal_base_does_not_create_adjective_opposite(self):
        result = detector('careless', {'care', 'careful'}, DictionaryFixture())[0]
        self.assertEqual(result['base'], 'care')
        self.assertFalse(result['base_has_dictionary_adjective'])
        self.assertEqual(result['semantic_status'], 'not_yet_coded')

    def test_hyphenated_prefix_deduplicated(self):
        self.assertEqual(len(detector('non-confident', {'confident'}, DictionaryFixture())), 1)


if __name__ == '__main__':
    unittest.main()
