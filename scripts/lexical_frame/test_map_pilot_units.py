import json
import unittest
import map_pilot_units as mapping

class MappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.terms=json.loads((mapping.SOURCE/'terms.json').read_text())
        cls.audits={x['word']:x for x in json.loads((mapping.AUDIT/'word-audit.json').read_text())}
        cls.rows={x['word']:x for x in mapping.build(cls.terms,cls.audits,{})}
    def test_all_source_links_preserved(self):
        self.assertEqual(len(self.rows),40)
        for t in self.terms:self.assertEqual(self.rows[t['word']]['source_entry_ids'],t['source_entries'])
    def test_no_synset_or_presentation_inflation(self):
        for r in self.rows.values():
            self.assertEqual(r['description_presentations'],[])
            self.assertIsNone(r['word_cue_presentation']['inherits_interpretation_id'])
            for item in r['lexical_identity_records']:self.assertIsNone(item['analysis_weight'])
    def test_noun_and_adjective_are_distinct(self):
        r=self.rows['liar'];self.assertIn('noun',r['attested_categories'])
        self.assertEqual(r['lexical_identity_records'],[])
    def test_one_source_sense_can_require_split(self):
        r=self.rows['responsible'];self.assertEqual(len(r['interpretations']),2)
        self.assertEqual(r['interpretations'][0]['source_sense_ids'],r['interpretations'][1]['source_sense_ids'])
        self.assertEqual({x['eligibility'] for x in r['interpretations']},{'eligible','ineligible'})

if __name__=='__main__':unittest.main()
