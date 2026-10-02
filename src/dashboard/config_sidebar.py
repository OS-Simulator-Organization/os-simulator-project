"""Run configuration sidebar (#14).

Sidebar widgets store their values in session state under the keys below;
read_config() turns them into a RunConfig, which the Load panel compares with
the loaded run's config.
"""

from typing import List

import streamlit as st

from src.core.controller_api import ControllerAPI, ProcessConfig, RunConfig, RunStatus, SchedulingPolicy

SEED = "seed"
SCENARIO = "scenario"
POLICY = "process_policy"
QUANTUM = "process_quantum_ms"
CONTEXT_SWITCH = "process_context_switch_ms"

SCENARIOS = ["baseline"]
POLICY_LABELS = {
    SchedulingPolicy.FCFS: "First come, first served",
    SchedulingPolicy.SJF: "Shortest job first",
    SchedulingPolicy.SRTF: "Shortest remaining time first",
    SchedulingPolicy.ROUND_ROBIN: "Round Robin",
    SchedulingPolicy.PRIORITY: "Priority with aging",
}
POLICIES_BY_LABEL = {label: policy for policy, label in POLICY_LABELS.items()}


def render_global_settings() -> None:
    st.number_input("Seed", min_value=0, value=0, step=1, key=SEED)
    st.selectbox("Scenario", SCENARIOS, key=SCENARIO)


def render_process_settings() -> None:
    label = st.selectbox("Scheduling policy", list(POLICIES_BY_LABEL), key=POLICY)
    if POLICIES_BY_LABEL[label] is SchedulingPolicy.ROUND_ROBIN:
        st.number_input("Time quantum (ms)", min_value=1, value=4, step=1, key=QUANTUM)
        st.number_input("Context switch cost (ms)", min_value=0, value=0, step=1, key=CONTEXT_SWITCH)


def read_config() -> RunConfig:
    state = st.session_state
    policy = POLICIES_BY_LABEL[state.get(POLICY, POLICY_LABELS[SchedulingPolicy.FCFS])]
    round_robin = policy is SchedulingPolicy.ROUND_ROBIN
    return RunConfig(
        seed=state.get(SEED, 0),
        scenario_id=state.get(SCENARIO, SCENARIOS[0]),
        process=ProcessConfig(
            policy=policy,
            quantum_ms=state.get(QUANTUM, 4) if round_robin else None,
            context_switch_ms=state.get(CONTEXT_SWITCH, 0) if round_robin else 0,
        ),
    )


def config_errors(config: RunConfig, controller: ControllerAPI) -> List[str]:
    errors = config.validate()
    if config.process.policy not in controller.supported_policies:
        errors.append(f"{POLICY_LABELS[config.process.policy]} is not supported yet.")
    return errors


def render_load_panel(controller: ControllerAPI) -> None:
    config = read_config()
    errors = config_errors(config, controller)
    for error in errors:
        st.error(error)

    snapshot = controller.snapshot()
    if snapshot.status is RunStatus.NOT_LOADED:
        st.info("No run loaded. Press Load and reset to start.")
    elif config != snapshot.config:
        st.warning("Settings changed. Press Load and reset to apply them.")

    if st.button("Load and reset", type="primary", disabled=bool(errors), width="stretch"):
        controller.load(config)
        st.session_state.events = []
        st.rerun()
