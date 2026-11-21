# Expected Results

Expected values for the automated tests, worked out by hand, taken from published results, or checked with `reference_paging.py`. None come from the simulator.

| File | Contents |
|---|---|
| `process_baseline.json` | Round Robin on P1–P4, q = 4 (hand-worked) |
| `memory.json` | FIFO and LRU cases (hand-worked or published) |
| `memory_sweep.json` | `trace.txt` and `trace_stress.txt` at 2, 3, 4, 5 and 8 frames (script-checked) |
| `file_system.json` | Every command in `data/fs_script.txt` (hand-worked) |

Assumptions: 1 tick = 1 ms. A fault fills the lowest free frame, or the evicted page's frame. A hit costs 1 ms and a fault costs 1 ms + `fault_latency`.

Cross-check the memory values with `python expected_results/reference_paging.py`.
