"""Honest, reproducible throughput check — a replay script, not a formal
load-testing framework. Report the real number, not a target."""
import itertools
import sys
import time
import urllib.request


def load_sample_lines(sample_file: str) -> list[bytes]:
    lines = []
    with open(sample_file, "rb") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith(b"#"):
                continue
            lines.append(stripped)
    if not lines:
        raise ValueError(f"no usable sample lines found in {sample_file}")
    return lines


def run_benchmark(sample_file: str, target_url: str, n: int = 10_000) -> None:
    lines = load_sample_lines(sample_file)
    cycled = itertools.islice(itertools.cycle(lines), n)

    start = time.perf_counter()
    for line in cycled:
        req = urllib.request.Request(target_url, data=line, method="POST")
        urllib.request.urlopen(req).read()
    elapsed = time.perf_counter() - start

    print(f"{n} events in {elapsed:.2f}s = {n / elapsed:.0f} events/sec")
    print(f"Extrapolated: {(n / elapsed) * 86400:,.0f} events/day on this hardware")


if __name__ == "__main__":
    sample_file = sys.argv[1] if len(sys.argv) > 1 else "testdata/sample_logs.txt"
    target_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000/ingest"
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 1_000
    run_benchmark(sample_file, target_url, n)
