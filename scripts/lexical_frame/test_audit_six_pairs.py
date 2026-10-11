import unittest
from audit_six_pairs import reading

class ReadingTests(unittest.TestCase):
    def test_exhaustive_exclusive_keeps_domain_qualification(self):
        self.assertEqual(reading({'can_both':'no','can_neither':'no'}),
                         'complementary_within_recorded_domain')
    def test_contrary_and_overlap_separate(self):
        self.assertEqual(reading({'can_both':'no','can_neither':'yes'}),'contrary_within_recorded_domain')
        self.assertEqual(reading({'can_both':'yes','can_neither':'no'}),'overlap_possible')
    def test_one_unknown_cannot_establish_contrary(self):
        self.assertEqual(reading({'can_both':'undetermined','can_neither':'yes'}),'unresolved')

if __name__=='__main__':unittest.main()
