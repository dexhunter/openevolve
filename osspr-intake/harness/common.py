"""Shared helpers for intake benchmarks. Does not import openevolve."""

import importlib.machinery
import importlib.util
import statistics
import subprocess
import sys
import sysconfig
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load_alloccount():
    """Load the object-allocation counter, building it once if needed."""
    tag = f"cpython-{sys.version_info.major}{sys.version_info.minor}"
    so_path = HERE / f"alloccount.{tag}.so"
    if not so_path.exists():
        include = sysconfig.get_path("include")
        subprocess.check_call(
            [
                "gcc",
                "-shared",
                "-fPIC",
                "-O2",
                f"-I{include}",
                "-o",
                str(so_path),
                str(HERE / "alloccount.c"),
            ]
        )
    loader = importlib.machinery.ExtensionFileLoader("alloccount", str(so_path))
    spec = importlib.util.spec_from_loader("alloccount", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def summarize(samples):
    """Median and full spread, (max-min)/median*100, over the measured calls."""
    ordered = sorted(samples)
    median = statistics.median(ordered)
    if median == 0:
        noise = 0.0
    else:
        noise = (ordered[-1] - ordered[0]) / median * 100.0
    return median, noise


def emit(metric_kind, samples):
    median, noise = summarize(samples)
    rendered = []
    for sample in samples:
        if isinstance(sample, float) and not sample.is_integer():
            rendered.append(f"{sample:.6f}")
        else:
            rendered.append(str(int(sample)))
    median_text = f"{median:.6f}" if isinstance(median, float) and not float(median).is_integer() else str(int(median))
    print(f"metric_kind={metric_kind}")
    print(f"baseline_value={median_text}")
    print(f"baseline_noise_pct={noise:.4f}")
    print("samples=" + ",".join(rendered))
    return median, noise
