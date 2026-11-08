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
- **Libraries Used**: `streamlit` for the dashboard, `jsonschema` for event validation, `pytest` for testing, `dataclasses` (Python standard library) for data modeling.
- **AI Assistance**: Consulted GenAI for architecture design advice, class diagram layouts, and base template code structure in compliance with course rules.
- **Sourced Tools — GenAI Entry (Milestone 3 dashboard):** Tool/model: Claude Opus 5.5 (Anthropic) via Claude Code. Access date: 2026-11-06. Instructor-authorized purpose: Brainstorming dashboard layout, pseudocode, and unit tests. Use: drafted the Memory tab's frame-occupancy, hit/fault and eviction views (`src/dashboard/memory_history.py`, `src/dashboard/views/memory.py`), the File tab's controls, metadata, storage and operation-log views (`src/dashboard/views/file_system.py`, `src/dashboard/run_controls.py`), CSV export and test controls (`src/dashboard/manager_view.py`, `src/dashboard/test_runner.py`), the FIFO vs LRU comparison (`src/dashboard/views/comparison.py`) and their tests. Student modification: Variables, methods. Verification: `pytest`; FIFO vs LRU checked against a hand-worked trace (pages 1 2 3 1 4 1, 3 frames: FIFO 5 faults/1 hit, LRU 4 faults/2 hits); Affected files: listed above.
