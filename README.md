# Discrete-Event OS Simulator

An interactive, multi-layered Operating System simulator built for OS class.

## Live Demo

- View the latest, live version of our simulator dashboard here: https://csc-301-os-simulator.streamlit.app
- Deployed using [Streamlit Community Cloud](https://streamlit.io/cloud)

## Project Structure

- `src/core/`: Shared data model, event schema, base manager, and simulation controller
- `src/managers/`: Subsystem managers (process, memory, file system, device, network, security)
- `src/dashboard/`: Streamlit dashboard, run configuration sidebar, and per-manager views
- `streamlit_app.py`: Dashboard entry point (used locally and by Streamlit Community Cloud)
- `docs/`: Data model and event schema documentation
- `tests/`: Automated unit and integration tests
- `data/`: Baseline input CSV and JSON scenario files

## Setup Instructions

1. Clone repository: `git clone https://github.com/OS-Simulator-Organization/os-simulator-project.git`
2. Create virtual environment: `python3 -m venv .venv`
3. Activate virtual environment:
   - Mac/Linux: `source .venv/bin/activate`
   - Windows: `.venv\Scripts\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run unit tests: `pytest`
6. Run the dashboard locally: `streamlit run streamlit_app.py`

## Sourced Tools & GenAI Statement

- **Major Libraries Used**: `streamlit` for the dashboard, `jsonschema` for event validation, `pytest` for testing, `dataclasses` (Python standard library) for data modeling.
- **Minor Libraries Used**: `abc`, `pathlib`, `pandas`, `heapq`, `typing`, `enum`, `os`, `uuid`
- **AI Assistance**: Consulted GenAI for architecture design advice, class diagram layouts, and base template code structure in compliance with course rules.
- **Sourced Tools — GenAI Entry (Milestone 3 dashboard):** Tool/model: Claude Opus 5.5 (Anthropic) via Claude Code. Access date: 2026-11-06. Instructor-authorized purpose: Brainstorming dashboard layout, pseudocode, and unit tests. Use: drafted the Memory tab's frame-occupancy, hit/fault and eviction views (`src/dashboard/memory_history.py`, `src/dashboard/views/memory.py`), the File tab's controls, metadata, storage and operation-log views (`src/dashboard/views/file_system.py`, `src/dashboard/run_controls.py`), CSV export and test controls (`src/dashboard/manager_view.py`, `src/dashboard/test_runner.py`), the FIFO vs LRU comparison (`src/dashboard/views/comparison.py`) and their tests. Student modification: Variables, methods. Verification: `pytest`; FIFO vs LRU checked against a hand-worked trace (pages 1 2 3 1 4 1, 3 frames: FIFO 5 faults/1 hit, LRU 4 faults/2 hits); Affected files: listed above.
- **Sourced Tools — GenAI Entry (Section 5 dashboard completion):** Tool/model: Claude Opus 5.5 (Anthropic) via Claude Code. Access date: 2026-11-20. Instructor-authorized purpose: generating dashboard code, approved by the instructor on the condition that the code is at a college level. Use: drafted the Overview status cards (`src/dashboard/overview.py`), the Event Explorer (`src/dashboard/event_explorer.py`), the Testing Center (`src/dashboard/testing_center.py`, `src/dashboard/test_runner.py`), the Export tab (`src/dashboard/export.py`), shared run controls with speed and stop-at-tick (`src/dashboard/run_controls.py`, used by the Process, Memory, File, Device and Network tabs), the process state timeline (`src/dashboard/process_timeline.py`, `src/dashboard/views/process.py`), the Security tab (`src/dashboard/views/security.py`), the network topology and link utilization views (`src/dashboard/network_topology.py`, `src/dashboard/views/network.py`), the scheduling batch comparison and FIFO/LRU table export (`src/dashboard/views/comparison.py`), the extra Scenario Builder inputs including a 16-command file script with intentional errors (`src/dashboard/scenario_inputs.py`, `src/dashboard/views/scenario_builder.py`, `src/dashboard/config_sidebar.py`) and their tests. Student modification: [fill in]. Verification: `pytest` (174 passed); FIFO vs LRU locality example checked against a hand-worked trace; link utilization checked by hand against the baseline packets (NodeB-NodeC: 2 packets, 128 + 256 = 384 bytes); end-to-end run of the dashboard. Affected files: listed above.
