"""Official Meta oEmbed availability diagnostic (metadata only, no media download)."""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

def inspect(url):
    endpoint = "https://graph.facebook.com/v25.0/instagram_oembed?" + urllib.parse.urlencode({"url": url})
    request = urllib.request.Request(endpoint, headers={"User-Agent": "Percept-Instagram-Diagnostics/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            data = json.load(response)
            return {"status": "EMBED_AVAILABLE", "http_status": response.status,
                    "provider": data.get("provider_name"), "media_downloaded": False}
    except urllib.error.HTTPError as exc:
        return {"status": "EMBED_UNAVAILABLE", "http_status": exc.code,
                "media_downloaded": False}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"status": "CHECK_FAILED", "error_type": type(exc).__name__,
                "media_downloaded": False}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    args = parser.parse_args()
    result = inspect(args.url)
    print(json.dumps(result, indent=2))
    if result["status"] != "EMBED_AVAILABLE":
        sys.exit(1)

if __name__ == "__main__":
    main()
