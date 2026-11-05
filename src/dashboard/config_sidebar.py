"""Run configuration sidebar (#14).

Sidebar widgets store their values in session state under the keys below;
read_config() turns them into a RunConfig, which the Load panel compares with
the loaded run's config.
"""

from typing import List

import streamlit as st

from src.core.controller_api import(
    ControllerAPI,
    ProcessConfig,
    MemoryConfig,
    RunConfig,
    RunStatus,
    SchedulingPolicy,
    ReplacementAlgorithm
)

SEED = "seed"
SCENARIO = "scenario"

SCENARIOS = ["baseline", "none"]

# Process Config Keys
POLICY = "process_policy"
QUANTUM = "process_quantum_ms"
CONTEXT_SWITCH = "process_context_switch_ms"
AGING_INTERVAL = "process_aging_interval"

POLICY_LABELS = {
    SchedulingPolicy.FCFS: "First come, first served",
    SchedulingPolicy.SJF: "Shortest job first",
    SchedulingPolicy.SRTF: "Shortest remaining time first",
    SchedulingPolicy.ROUND_ROBIN: "Round Robin",
    SchedulingPolicy.PRIORITY: "Priority with aging",
}
POLICIES_BY_LABEL = {label: policy for policy, label in POLICY_LABELS.items()}

# Memory Config Keys
MEM_ALGORITHM = "memory_algorithm"
PAGE_SIZE = "page_size"
TOTAL_FRAMES = "total_frames"
FAULT_LATENCY = "fault_latency"

REPLACEMENT_ALGORITHMS = ["FIFO", "LRU"]
PAGE_SIZE_OPTIONS = [256, 512, 1024, 2048, 4096, 8192]




def render_global_settings() -> None:
    st.number_input("Seed", min_value=0, value=0, step=1, key=SEED)
    st.selectbox("Scenario", SCENARIOS, key=SCENARIO)


def render_process_settings() -> None:
    label = st.selectbox("Scheduling policy", list(POLICIES_BY_LABEL), key=POLICY)
    if POLICIES_BY_LABEL[label] is SchedulingPolicy.ROUND_ROBIN:
        st.number_input("Time quantum (ms)", min_value=1, value=4, step=1, key=QUANTUM)
    elif POLICIES_BY_LABEL[label] is SchedulingPolicy.PRIORITY:
        st.number_input("Aging interval (ms)", min_value=0, value=10, step=1, key=AGING_INTERVAL)

    if POLICIES_BY_LABEL[label] in (SchedulingPolicy.ROUND_ROBIN, SchedulingPolicy.SRTF):
        st.number_input("Context switch cost (ms)", min_value=0, value=0, step=1, key=CONTEXT_SWITCH)

def render_memory_settings() -> None:
    """Renders memory manager configuration widgets in the sidebar."""
    st.selectbox("Replacement algorithm", REPLACEMENT_ALGORITHMS, key=MEM_ALGORITHM)
    st.selectbox("Page size (bytes)", PAGE_SIZE_OPTIONS, index=4, key=PAGE_SIZE)
    st.number_input("Total frames", min_value=1, value=4, step=1, key=TOTAL_FRAMES)
    st.number_input("Fault latency (ticks)", min_value=0, value=2, step=1, key=FAULT_LATENCY)

def read_config() -> RunConfig:
    state = st.session_state

    policy = POLICIES_BY_LABEL[state.get(POLICY, POLICY_LABELS[SchedulingPolicy.FCFS])]
    round_robin = policy is SchedulingPolicy.ROUND_ROBIN
    srtf = policy is SchedulingPolicy.SRTF

    alg_str = state.get(MEM_ALGORITHM, ReplacementAlgorithm.FIFO.value)
    replacement_alg = ReplacementAlgorithm(alg_str)

    return RunConfig(
        seed=state.get(SEED, 0),
        scenario_id=state.get(SCENARIO, SCENARIOS[0]),
        process=ProcessConfig(
            policy=policy,
            quantum_ms=state.get(QUANTUM, 4) if round_robin else None,
            context_switch_ms=state.get(CONTEXT_SWITCH, 0) if round_robin or srtf else 0 ,
            aging_interval=state.get(AGING_INTERVAL, 0),
            custom_workload=state.get("custom_workload", []),
        ),
        memory=MemoryConfig(
            algorithm=replacement_alg,
            page_size=state.get(PAGE_SIZE, 4096),
            total_frames=state.get(TOTAL_FRAMES, 4),
            fault_latency=state.get(FAULT_LATENCY, 2),
            traces=state.get("custom_traces", {}),
        )
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
