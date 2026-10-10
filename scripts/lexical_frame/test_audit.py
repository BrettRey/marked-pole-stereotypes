import unittest
from audit_pilot import wiki_display, reading_errors

class AuditChecks(unittest.TestCase):
    def test_link_display(self): self.assertEqual(wiki_display('A [[lemma|display]] and [[word]].'),'A display and word.')
    def test_no_template_inference(self): self.assertEqual(wiki_display('{{unknown|x}}'),'{{unknown|x}}')
    def test_complement_requires_exhaustive_exclusive(self):
        self.assertTrue(reading_errors({'reading':'complementary','can_neither':'undetermined','can_both':'no'}))
    def test_contrary_allows_neither(self):
        self.assertEqual(reading_errors({'reading':'contrary','can_neither':'yes','can_both':'no'}),[])
    def test_uncertainty_not_forced(self):
        self.assertEqual(reading_errors({'reading':'unresolved','can_neither':'undetermined','can_both':'undetermined'}),[])

if __name__=='__main__': unittest.main()
