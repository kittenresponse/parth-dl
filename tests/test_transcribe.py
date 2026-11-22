"""Offline regression tests for optional transcription component."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from parth_dl.transcribe import transcribe_file


class TranscriptionTest(unittest.TestCase):
    def test_missing_file_fails_without_fake_transcript(self):
        with self.assertRaises(FileNotFoundError):
            transcribe_file("/this/path/does/not/exist.mp4")

    def test_empty_file_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "empty.mp4"
            path.touch()
            with self.assertRaisesRegex(ValueError, "empty"):
                transcribe_file(path)

    def test_timestamped_transcript(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "recording.mp4"
            path.write_bytes(b"sample")
            segment = mock.Mock(start=0.25, end=2.75, text=" Hello world ")
            info = mock.Mock(language="en", language_probability=0.99)
            model = mock.Mock()
            model.transcribe.return_value = ([segment], info)
            module = mock.Mock(WhisperModel=mock.Mock(return_value=model))
            with mock.patch.dict("sys.modules", {"faster_whisper": module}):
                result = transcribe_file(path)
            self.assertEqual(result["text"], "Hello world")
            self.assertEqual(result["segments"][0]["start"], 0.25)
            self.assertEqual(result["language"], "en")
            self.assertEqual(result["status"], "transcribed")
            json.dumps(result)


if __name__ == "__main__":
    unittest.main()
