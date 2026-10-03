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
