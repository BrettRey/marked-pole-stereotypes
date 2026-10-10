import unittest
from import_sources import lexical_id, normalize


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


if __name__ == '__main__':
    unittest.main()
