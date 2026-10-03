# os-simulator-project
# Discrete-Event OS Simulator

An interactive, multi-layered Operating System simulator built for OS class.

## Live Demo
- View the latest, live version of our simulator dashboard here: https://csc-301-os-simulator.streamlit.app
- Deployed using [Streamlit Community Cloud](https://streamlit.io/cloud)

## Project Structure
- `src/`: Core Python modules (Shared Data Model, Event Schema, Managers, Dashboard)
- `docs/`: Architecture diagrams, data specs, and project documentation
- `tests/`: Automated unit and integration tests
- `data/`: Baseline input CSV and JSON scenario files

## Setup Instructions
1. Clone repository: `git clone <repo-url>`
2. Create virtual environment: `python3 -m venv .venv`
3. Activate virtual environment:
   - Mac/Linux: `source .venv/bin/activate`
   - Windows: `.venv\Scripts\activate`

4. Install dependencies: `pip install -r requirements.txt`
5. Run unit tests: `pytest`

## Sourced Tools & GenAI Statement
- **Libraries Used**: `pytest` for testing, `dataclasses` (Python standard library) for data modeling.
- **AI Assistance**: Consulted GenAI for architecture design advice, class diagram layouts, and base template code structure in compliance with course rules.
