"""Peak Python memory of one artifact security-filter call.

include_artifacts and artifact_security_filter both default on. The filter runs
on the full artifact before _render_artifacts truncates it to max_artifact_bytes
(20 KiB). Artifacts larger than artifact_size_threshold (32 KiB) are stored as
files and loaded whole, so a captured benchmark stdout of 128 KiB is a normal
large artifact. The text is the shipped MLX evaluator source, tiled, with the
ANSI codes, long tokens, API-key shapes, and password assignments the filter
redacts.
"""

import sys
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from openevolve.config import PromptConfig  # noqa: E402
from openevolve.prompt.sampler import PromptSampler  # noqa: E402

TARGET_BYTES = 128 * 1024
RUNS = 5


def build_log():
    source = (ROOT / "examples" / "mlx_metal_kernel_opt" / "evaluator.py").read_text(
        encoding="utf-8"
    )
    lines = []
    index = 0
    while sum(len(line) + 1 for line in lines) < TARGET_BYTES + 4096:
        for line in source.splitlines():
            if index % 20 == 0:
                lines.append(
                    f"\x1b[32mINFO\x1b[0m bench {index} score={index / 10:.4f} token={'a' * 36}"
                )
            elif index % 35 == 0:
                lines.append(f"password=hunter{index} token=sk-{'b' * 48}")
            else:
                lines.append(line)
            index += 1
            if sum(len(item) + 1 for item in lines) >= TARGET_BYTES + 4096:
                break
    raw = "\n".join(lines).encode("utf-8")[:TARGET_BYTES]
    while raw:
        try:
            text = raw.decode("utf-8")
            break
        except UnicodeDecodeError:
            raw = raw[:-1]
    else:
        raise SystemExit("could not decode the log prefix")
    # Pad with spaces so the filtered buffer is exactly 128 KiB of input.
    text += " " * (TARGET_BYTES - len(text.encode("utf-8")))
    if len(text.encode("utf-8")) != TARGET_BYTES:
        raise SystemExit(f"log is {len(text.encode('utf-8'))} bytes, expected {TARGET_BYTES}")
    return text


def peak_bytes(function):
    tracemalloc.clear_traces()
    tracemalloc.reset_peak()
    function()
    _current, peak = tracemalloc.get_traced_memory()
    return peak


def main():
    log = build_log()
    sampler = PromptSampler(PromptConfig())
    filtered = sampler._apply_security_filter(log)
    if "REDACTED" not in filtered:
        raise SystemExit("filter did not redact the planted tokens")
    if len(filtered) < TARGET_BYTES // 2:
        raise SystemExit("filter dropped most of the log")

    tracemalloc.start()
    peak_bytes(lambda: sampler._apply_security_filter(log))
    samples = [peak_bytes(lambda: sampler._apply_security_filter(log)) for _ in range(RUNS)]
    tracemalloc.stop()

    ordered = sorted(samples)
    median = ordered[len(ordered) // 2]
    noise = (ordered[-1] - ordered[0]) / median * 100.0 if median else 0.0
    print("metric_kind=peak_memory_bytes")
    print(f"baseline_value={median}")
    print(f"baseline_noise_pct={noise:.4f}")
    print("samples=" + ",".join(str(sample) for sample in samples))


if __name__ == "__main__":
    main()
