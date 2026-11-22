"""Transcribe a locally available video/audio file with optional faster-whisper.

Install: pip install faster-whisper
Run: python -m parth_dl.transcribe recording.mp4 --model small --output transcript.json

This does not circumvent Instagram access restrictions. It processes files
already available to the user and never fabricates words on download failure.
"""
import argparse
import json
from pathlib import Path


def transcribe_file(path, model_name="small", language=None):
    media = Path(path)
    if not media.is_file():
        raise FileNotFoundError(f"Media file not found: {media}")
    if media.stat().st_size == 0:
        raise ValueError("Media file is empty")
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "Speech recognition is not installed. Run: pip install faster-whisper"
        ) from exc

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(media), language=language, beam_size=5,
        vad_filter=True, condition_on_previous_text=False,
    )
    rows = [
        {"start": round(seg.start, 2), "end": round(seg.end, 2),
         "text": seg.text.strip()}
        for seg in segments if seg.text.strip()
    ]
    return {
        "source": media.name,
        "language": info.language,
        "language_probability": round(info.language_probability, 4),
        "segments": rows,
        "text": " ".join(row["text"] for row in rows),
        "status": "transcribed" if rows else "no_speech_detected",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Transcribe local audio/video")
    parser.add_argument("media", help="Path to a local audio or video file")
    parser.add_argument("--model", default="small",
                        help="Whisper model size (default: small)")
    parser.add_argument("--language", default=None,
                        help="Optional language code; auto-detect by default")
    parser.add_argument("--output", default=None,
                        help="Optional JSON output path")
    args = parser.parse_args(argv)
    try:
        result = transcribe_file(args.media, args.model, args.language)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Transcription failed: {exc}\n")
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
