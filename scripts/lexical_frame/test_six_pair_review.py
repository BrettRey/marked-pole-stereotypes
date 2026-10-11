import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import six_pair_review as review

class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.packet={'pair_id':'test','base':'base','word':'derived',
          'saved_proposals':[{'proposal_id':'p1','base_sense_id':'b','word_sense_id':'w'}],
          'dictionary_entries':[
            {'word':'base','dictionary_senses':[{'sense_id':'b','gloss':'base meaning'}]},
            {'word':'derived','dictionary_senses':[{'sense_id':'w','gloss':'derived meaning'}]}]}
        self.row={'proposal_id':'p1','base_sense_id':'b','word_sense_id':'w',
          'base_interpretation':'base','word_interpretation':'derived','status':'unresolved','reason':'insufficient',
          'evidence':[{'word':'base','sense_id':'b','quote':'base meaning'},
                      {'word':'derived','sense_id':'w','quote':'derived meaning'}],
          'targets':[{'temporal':'unresolved','base_domain':'unknown','word_domain':'unknown',
            'domain_match':'unresolved','shared_domain':'unknown','inapplicability_note':'unknown',
            'can_both':'undetermined','can_neither':'undetermined','opposition_reason':'unknown',
            'complement_scope':'unresolved'}]}
        self.result={'pair_id':'test','saved_alignments':[self.row],
          'additional_alignments':[],'lexical_identity_note':'unknown','remaining_gap':'unknown'}
    def test_unknown_is_valid(self):
        self.assertEqual(review.validate(self.result,self.packet),[])
    def test_missing_or_mutated_proposal_fails(self):
        self.result['saved_alignments']=[]
        self.assertIn('saved proposal accounting',review.validate(self.result,self.packet))
        self.result['saved_alignments']=[self.row];self.row['base_sense_id']='w'
        self.assertTrue(any('mutated' in x for x in review.validate(self.result,self.packet)))
    def test_false_evidence_and_missing_pole_fail(self):
        self.row['evidence'][0]['quote']='invented'
        self.assertTrue(any('invalid quote' in x for x in review.validate(self.result,self.packet)))
        self.row['evidence']=self.row['evidence'][1:]
        self.assertTrue(any('missing direct pole' in x for x in review.validate(self.result,self.packet)))
    def test_new_alignment_allowed_without_replacing_saved(self):
        new=copy.deepcopy(self.row);new['proposal_id']='new-01'
        self.result['additional_alignments']=[new]
        self.assertEqual(review.validate(self.result,self.packet),[])
    def test_incompatible_domains_cannot_be_classified(self):
        self.row['targets'][0].update(domain_match='incompatible',can_both='no')
        self.assertIn('opposition classified across incompatible domains',review.validate(self.result,self.packet))
    def test_scope_requires_complementarity(self):
        self.row['targets'][0]['complement_scope']='conditional_domain'
        self.assertIn('complement scope without complementarity',review.validate(self.result,self.packet))
    def test_timeout_one_process_no_retry(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp, patch.object(review.subprocess,'Popen') as create, patch.object(review.os,'killpg') as kill:
            p=create.return_value;p.pid=123;p.communicate.side_effect=[subprocess.TimeoutExpired('test',300),(None,None)]
            self.assertEqual(review.run_process(['test'],{},tmp,'x',Path(tmp)),'timeout')
            self.assertEqual(create.call_count,1);kill.assert_called_once_with(123,review.signal.SIGKILL)
    def test_authorized_scope(self):
        pairs=review.saved_pairs()
        self.assertEqual(len(pairs),6);self.assertEqual(sum(len(x['saved_proposals']) for x in pairs),16)

if __name__=='__main__': unittest.main()
