"""Independent FIFO/LRU reference used to cross-check the expected results.

Standard library only, and deliberately imports nothing from src/, so a bug in
the simulator cannot leak into the expected values.

    python expected_results/reference_paging.py          check memory.json and memory_sweep.json
    python expected_results/reference_paging.py --write  regenerate memory_sweep.json
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
SWEEP_FRAMES = (2, 3, 4, 5, 8)
SWEEP_TRACES = ("trace.txt", "trace_stress.txt")
SWEEP_PAGE_SIZE = 4096
SWEEP_LATENCY = 2


def read_trace(path):
    addresses = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            addresses.append(int(line, 0))
    return addresses


def simulate(pages, policy, frames):
    """Return one record per reference: page, H or F, evicted page, frames after."""
    slots = [None] * frames
    order = []  # Eviction order, next victim first.
    steps = []
    for page in pages:
        evicted = None
        if page in slots:
            result = "H"
            if policy == "LRU":
                order.remove(page)
                order.append(page)
        else:
            result = "F"
            if None in slots:
                slot = slots.index(None)
            else:
                evicted = order.pop(0)
                slot = slots.index(evicted)
            slots[slot] = page
            order.append(page)
        steps.append({"page": page, "result": result, "evicted": evicted, "frames": list(slots)})
    return steps


def summarize(steps, latency=0):
    references = len(steps)
    faults = sum(step["result"] == "F" for step in steps)
    hits = references - faults
    total_cost = hits + faults * (1 + latency)
    return {
        "references": references,
        "hits": hits,
        "faults": faults,
        "evictions": sum(step["evicted"] is not None for step in steps),
        "fault_rate_percent": round(100 * faults / references, 4),
        "hit_rate_percent": round(100 * hits / references, 4),
        "avg_access_time_ms": round(total_cost / references, 4),
    }


def case_pages(case):
    if "trace_file" in case:
        addresses = read_trace(HERE.parent / case["trace_file"])
    else:
        addresses = [int(str(address), 0) for address in case["addresses"]]
    return [address // case["page_size"] for address in addresses]


def check_hand_values():
    problems = []
    cases = json.loads((HERE / "memory.json").read_text())["cases"]
    for case in cases:
        pages = case_pages(case)
        for policy, expected in case["policies"].items():
            steps = simulate(pages, policy, case["frames"])
            actual = summarize(steps, case.get("fault_latency", 0))
            for key, value in expected["summary"].items():
                if actual[key] != value:
                    problems.append(f"{case['name']} {policy} {key}: hand {value}, reference {actual[key]}")
            if "steps" in expected and expected["steps"] != steps:
                problems.append(f"{case['name']} {policy}: step table differs from reference")
    return len(cases), problems


def sweep():
    rows = []
    for name in SWEEP_TRACES:
        pages = [address // SWEEP_PAGE_SIZE for address in read_trace(DATA / name)]
        for frames in SWEEP_FRAMES:
            for policy in ("FIFO", "LRU"):
                summary = summarize(simulate(pages, policy, frames), SWEEP_LATENCY)
                rows.append({"trace": name, "policy": policy, "frames": frames, **summary})
    return {
        "method": "script-checked by expected_results/reference_paging.py, not hand-worked",
        "page_size": SWEEP_PAGE_SIZE,
        "fault_latency": SWEEP_LATENCY,
        "rows": rows,
    }


def main():
    sweep_path = HERE / "memory_sweep.json"
    if "--write" in sys.argv:
        sweep_path.write_text(json.dumps(sweep(), indent=2) + "\n")
    case_count, problems = check_hand_values()
    if json.loads(sweep_path.read_text()) != sweep():
        problems.append("memory_sweep.json is out of date; rerun with --write")
    for problem in problems:
        print(problem)
    print(f"{case_count} hand-worked cases checked, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
