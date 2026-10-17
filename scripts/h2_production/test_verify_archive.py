"""File-format and register fixtures, never stand-in research observations."""
import io
import tempfile
import unittest
from pathlib import Path
import numpy as np
from common import dump, sha
from verify_archive import posterior_header, reconciled_register, VERIFIER_ERROR


class ArchiveTests(unittest.TestCase):
    def test_public_header_readers(self):
        for writer in (np.lib.format.write_array_header_1_0, np.lib.format.write_array_header_2_0):
            stream = io.BytesIO()
            writer(stream, dict(descr='<f8', fortran_order=False, shape=(4, 1000, 2)))
            stream.seek(0)
            shape, _, dtype = posterior_header(stream)
            self.assertEqual(shape, (4, 1000, 2))
            self.assertEqual(dtype, np.dtype('float64'))
        self.assertNotIn('np.lib.format._read_array_header',
                         Path(__file__).with_name('verify_archive.py').read_text())

    def test_invalid_header_rejected(self):
        for shape, descr in [((1, 1000), '<f8'), ((4, 1000), '|O')]:
            stream = io.BytesIO()
            np.lib.format.write_array_header_1_0(stream, dict(descr=descr, fortran_order=False, shape=shape))
            stream.seek(0)
            with self.assertRaises(ValueError): posterior_header(stream)

    def test_reconciliation_preserves_original_and_rejects_changed_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            register, proof = root/'register.json', root/'proof.json'
            row = dict(state='failed', owner='hf-1', error=VERIFIER_ERROR)
            dump(register, dict(jobs={'nicolas-s0-c1':row}))
            original = register.read_bytes()
            evidence = dict(state='verified',job='nicolas-s0-c1',original_register_sha256=sha(register),
                original_row=row,all_file_hashes_match=True,posterior_zip_crc=True,
                manifest_sha256='verified-manifest',fit_elapsed_seconds=10,fit_ended_at='observed')
            dump(proof,evidence)
            fixed = reconciled_register(register,proof)
            self.assertEqual(fixed['jobs']['nicolas-s0-c1']['state'],'complete')
            self.assertEqual(fixed['jobs']['nicolas-s0-c1']['original_registration'],row)
            self.assertEqual(register.read_bytes(),original)
            evidence['original_register_sha256']='changed'
            dump(proof,evidence)
            with self.assertRaises(ValueError): reconciled_register(register,proof)


if __name__ == '__main__':
    unittest.main()
