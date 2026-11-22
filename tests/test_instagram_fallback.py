"""Regression tests for Instagram retrieval safety; no network needed."""
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from instagram_fallback import canonical_url, valid_mp4, retrieve, MIN_BYTES

class RetrievalTests(unittest.TestCase):
    def test_canonical_url_strips_tracking(self):
        self.assertEqual(canonical_url("https://www.instagram.com/reel/DgAtwVTM2Zb/?gwpx=test"),
                         "https://www.instagram.com/reel/DgAtwVTM2Zb/")
    def test_rejects_html_disguised_as_mp4(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "login.mp4"
            p.write_bytes(b"<html>" + b"x" * MIN_BYTES)
            self.assertFalse(valid_mp4(p))
    def test_rejects_tiny_mp4(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "tiny.mp4"
            p.write_bytes(b"\x00\x00\x00\x18ftypisom")
            self.assertFalse(valid_mp4(p))
    def test_accepts_header_and_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "valid.mp4"
            p.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"x" * MIN_BYTES)
            self.assertTrue(valid_mp4(p))
    @patch("instagram_fallback.subprocess.run")
    def test_all_fail_is_failure(self, run):
        run.return_value = Mock(returncode=1, stderr="HTTP Error 403")
        with tempfile.TemporaryDirectory() as tmp:
            result = retrieve("https://www.instagram.com/reel/DgAtwVTM2Zb/", tmp)
            self.assertEqual(result["status"], "FAILED")
            self.assertEqual(len(result["attempts"]), 3)
            self.assertEqual(result["attempts"][0]["error"], "http error 403")

if __name__ == "__main__":
    unittest.main()
