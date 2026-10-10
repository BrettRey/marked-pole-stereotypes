import copy
import unittest
from code_pilot import validate

class EvidenceChecks(unittest.TestCase):
    def setUp(self):
        self.records=[{'word':'fixture','dictionary_senses':[{'sense_id':'synthetic:a:1','pos':'a','gloss':'showing care'}]}]
        self.result={'words':[{'word':'fixture','word_status':'eligible','senses':[{'sense_id':'synthetic:a:1','status':'eligible','evidence_quote':'showing care'}],
                              'interpretation_groups':[{'label':'care','sense_ids':['synthetic:a:1']}]}]}
    def test_complete(self): self.assertEqual(validate(self.result,self.records,'word'),[])
    def test_missing_sense(self):
        self.result['words'][0]['senses']=[]
        self.assertTrue(validate(self.result,self.records,'word'))
    def test_hallucinated_quote(self):
        self.result['words'][0]['senses'][0]['evidence_quote']='imagined passage'
        self.assertTrue(validate(self.result,self.records,'word'))
    def test_noneligible_group(self):
        self.result['words'][0]['interpretation_groups'][0]['sense_ids']=['not-present']
        self.assertTrue(validate(self.result,self.records,'word'))
    def test_wrong_word_status(self):
        self.result['words'][0]['word_status']='ineligible'
        self.assertTrue(validate(self.result,self.records,'word'))
    def test_pair_evidence_wrong_word(self):
        pair={'analyses':[{'word':'fixture','immediate_base':'other','evidence':[{'word':'other','sense_id':'synthetic:a:1','quote':'showing care'}],
                           'possible_sense_alignments':[]}]}
        self.assertTrue(validate(pair,self.records,'pair'))

if __name__=='__main__': unittest.main()
