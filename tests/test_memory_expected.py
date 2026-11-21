"""Checks the memory manager against the hand-worked and published cases in expected_results/."""

import json
from pathlib import Path

import pytest

from src.core.models import Process
from src.managers.memory_manager import MemoryManager

ROOT = Path(__file__).parent.parent
EXPECTED = json.loads((ROOT / "expected_results" / "memory.json").read_text())
CASES = [(case, policy) for case in EXPECTED["cases"] for policy in case["policies"]]


def read_trace(path):
    lines = (ROOT / path).read_text().splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def run_trace(addresses, policy, page_size, frames, fault_latency):
    manager = MemoryManager()
    manager.configure({"algorithm": policy, "page_size": page_size, "total_frames": frames,
                       "fault_latency": fault_latency})
    manager.load(addresses)
    process = Process(pid="P1", owner_id="u", arrival_time=0, burst_time=10**6, priority=1)
    tick = 0
    while manager.trace_pointer < len(manager.trace) and tick < 10**5:
        manager.step(tick, process)
        tick += 1
    return manager.metrics()


def summary(metrics, keys):
    names = {"references": "total_memory_references", "hits": "page_hits", "faults": "page_faults",
             "evictions": "eviction_count", "fault_rate_percent": "page_fault_rate",
             "hit_rate_percent": "page_hit_rate", "avg_access_time_ms": "avg_access_time"}
    return {key: metrics[names[key]] for key in keys}


@pytest.mark.parametrize("case, policy", CASES, ids=[f"{case['name']}-{policy}" for case, policy in CASES])
def test_memory_case(case, policy):
    addresses = [str(a) for a in case["addresses"]] if "addresses" in case else read_trace(case["trace_file"])
    expected = case["policies"][policy]["summary"]
    metrics = run_trace(addresses, policy, case["page_size"], case["frames"], case["fault_latency"])
    assert summary(metrics, expected) == pytest.approx(expected, abs=1e-3)
