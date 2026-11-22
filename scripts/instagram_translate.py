"""Translate validated Instagram video speech to English; fail closed."""
import json
import pathlib
import sys

from instagram_fallback import valid_mp4, valid_videos

def main():
    output = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "osint-output")
    files = valid_videos(output)
    if not files:
        print("ERROR: no verified MP4 >=50 KB with ftyp header", file=sys.stderr)
        sys.exit(1)
    from faster_whisper import WhisperModel
    import av
    original_open = av.open
    def compatible_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return original_open(*args, **kwargs)
    av.open = compatible_open
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(files[0]), task="translate",
                                      beam_size=1, vad_filter=True)
    rows = [{"start": s.start, "end": s.end, "text": s.text.strip()}
            for s in segments if s.text.strip()]
    english = " ".join(row["text"] for row in rows).strip()
    if not english:
        print("ERROR: verified MP4 contained no transcribable speech", file=sys.stderr)
        sys.exit(1)
    result = {"source_file": files[0].name, "source_language": info.language,
              "english_text": english, "english_segments": rows}
    (output / "transcript.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "english.txt").write_text(english + "\n", encoding="utf-8")
    (output / "transcript.md").write_text("# Verified English transcript\n\n" + english + "\n", encoding="utf-8")
    print("Verified MP4 and non-empty English transcript generated.")

if __name__ == "__main__":
    main()
