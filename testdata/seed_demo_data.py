"""Seed a running ULPF API with testdata/demo_logs.txt — 64 realistic
perimeter-device events (normal traffic, a denied port-scan burst, and 3
unrecognized-format lines for the AI-assist demo) so the dashboard, search,
drift, and compliance tabs have real content instead of an empty state."""
import json
import sys
import urllib.request


def load_lines(path: str) -> list[bytes]:
    lines = []
    with open(path, "rb") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith(b"#"):
                continue
            lines.append(stripped)
    return lines


def seed(sample_file: str, target_url: str) -> None:
    lines = load_lines(sample_file)
    results: dict[str, int] = {}
    for line in lines:
        req = urllib.request.Request(target_url, data=line, method="POST")
        try:
            body = json.loads(urllib.request.urlopen(req).read())
            status = body.get("status", "unrecognized_response")
        except Exception as e:
            status = "error"
            print(f"  failed: {e}", file=sys.stderr)
        results[status] = results.get(status, 0) + 1
    print(f"seeded {len(lines)} events from {sample_file} -> {results}")


if __name__ == "__main__":
    sample_file = sys.argv[1] if len(sys.argv) > 1 else "testdata/demo_logs.txt"
    target_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000/ingest"
    seed(sample_file, target_url)
