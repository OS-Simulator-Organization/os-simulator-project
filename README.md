# Discrete-Event OS Simulator

An interactive, multi-layered Operating System simulator built for OS class.

## Live Demo

- View the latest, live version of our simulator dashboard here: https://csc-301-os-simulator.streamlit.app
- Deployed using [Streamlit Community Cloud](https://streamlit.io/cloud)

## Managers

| Manager | What it simulates |
|---|---|
| Process | FCFS, SJF, SRTF, Round Robin (quantum and context-switch cost), Priority with aging |
| Memory | Paging with FIFO and LRU replacement and page-fault latency |
| File System | Hierarchical in-memory file system with permissions |
| Security | Users, roles, rwx permissions, login sessions, alerts, append-only audit log |
| Device | Disk, printer and keyboard queues; FCFS, SSTF and SCAN disk scheduling; failure and recovery |
| Network | Nodes, links and packets; FIFO and Priority queues; shortest-path routing with rerouting; buffers and drops |
| Parallel | Planned for the final submission |

## Dashboard

Tabs: Overview, one workspace per manager, Scenario Builder, Testing Center, Comparison, Event Explorer and Export. Each manager tab has its own run, reset and test controls.

## Project Structure

- `src/core/`: Shared data model, event schema, base manager, and simulation controller
- `src/managers/`: Subsystem managers (process, memory, file system, device, network, security)
- `src/dashboard/`: Streamlit dashboard, run configuration sidebar, and per-manager views
- `streamlit_app.py`: Dashboard entry point (used locally and by Streamlit Community Cloud)
- `docs/`: Data model and event schema documentation
- `tests/`: Automated unit and integration tests
- `data/`: Baseline input CSV and JSON scenario files
- `expected_results/`: Hand-worked expected values for the tests

## Setup Instructions

1. Clone repository: `git clone https://github.com/OS-Simulator-Organization/os-simulator-project.git`
2. Create virtual environment: `python3 -m venv .venv`
3. Activate virtual environment:
   - Mac/Linux: `source .venv/bin/activate`
   - Windows: `.venv\Scripts\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run unit tests: `pytest`
6. Run the dashboard locally: `streamlit run streamlit_app.py`

## Testing

- The dashboard's Testing Center tab runs each manager's suite, the integration tests and the boundary cases, with pass/fail and expected vs. actual values.
- `expected_results/` holds hand-worked values the tests check against. See its README.

## Known Limitations

- The parallel-computing component is not implemented yet.
- The integrated acceptance scenario is not available yet.
- The file manager cannot run a command script and has no `ls` or `rmdir` command yet.
- Loading a workload from a file fails silently.
- The Scenario Builder cannot import memory traces separately.
- The Testing Center shows expected and actual values only for failed tests.

## Sourced Tools & GenAI Statement

- **Major Libraries Used**: `streamlit` for the dashboard, `jsonschema` for event validation, `pytest` for testing, `dataclasses` (Python standard library) for data modeling.
- **Minor Libraries Used**: `abc`, `pathlib`, `pandas`, `heapq`, `typing`, `enum`, `os`, `uuid`
- **AI Assistance**: Consulted GenAI for architecture design advice, class diagram layouts, and base template code structure in compliance with course rules.
- **Sourced Tools — GenAI Entry (Milestone 3 dashboard):** Tool/model: Claude Opus 5.5 (Anthropic) via Claude Code. Access date: 2026-11-06. Instructor-authorized purpose: Brainstorming dashboard layout, pseudocode, and unit tests. Use: drafted the Memory tab's frame-occupancy, hit/fault and eviction views (`src/dashboard/memory_history.py`, `src/dashboard/views/memory.py`), the File tab's controls, metadata, storage and operation-log views (`src/dashboard/views/file_system.py`, `src/dashboard/run_controls.py`), CSV export and test controls (`src/dashboard/manager_view.py`, `src/dashboard/test_runner.py`), the FIFO vs LRU comparison (`src/dashboard/views/comparison.py`) and their tests. Student modification: Variables, methods. Verification: `pytest`; FIFO vs LRU checked against a hand-worked trace (pages 1 2 3 1 4 1, 3 frames: FIFO 5 faults/1 hit, LRU 4 faults/2 hits); Affected files: listed above.
