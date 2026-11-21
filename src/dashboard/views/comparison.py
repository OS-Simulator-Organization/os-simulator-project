"""Comparison tab (spec 4.2 and 5): run policies on identical input and compare
them side by side.

- Page replacement: FIFO vs LRU on the same trace and frames.
- CPU scheduling: a batch run of every scheduling policy on the same workload.

Each policy runs on a fresh controller with the identical config; only the
policy differs, so the results are directly comparable and reproducible.
"""

from dataclasses import replace
from typing import Any, Callable, Dict, List, Optional

import altair as alt
import pandas as pd
import streamlit as st

from src.core.controller import RealController
from src.core.controller_api import (MemoryConfig, ProcessConfig, ReplacementAlgorithm, RunConfig,
                                     SchedulingPolicy)
from src.dashboard.config_sidebar import read_config

RESULTS = "memory-comparison"
SCHEDULING_RESULTS = "scheduling-comparison"
USE_LOCALITY = "comparison-use-locality"
MAX_TICKS = 10_000
BASELINE_TRACE = ["0x0040", "0x10A0", "0x0044", "0x20B0"]
POLICY_COLORS = {"FIFO": "#2a78d6", "LRU": "#eb6834"}

# Reproducible trace where FIFO and LRU differ. Pages 1 2 3 1 4 1 (256-byte pages, 3 frames), by hand:
#   FIFO: F F F H F(evicts 1) F(evicts 2) -> 5 faults, 1 hit, 2 evictions
#   LRU:  F F F H F(evicts 2) H           -> 4 faults, 2 hits, 1 eviction
LOCALITY_EXAMPLE = RunConfig(
    scenario_id="custom",
    process=ProcessConfig(custom_workload=[{"pid": "P1", "arrival_time": 0, "burst_time": 20, "priority": 1}]),
    memory=MemoryConfig(page_size=256, total_frames=3, fault_latency=0, trace=[256, 512, 768, 256, 1024, 256]),
)

SCHEDULING_METRICS = [
    ("avg_waiting_time", "Average waiting time (ms)"),
    ("avg_turnaround_time", "Average turnaround time (ms)"),
    ("avg_response_time", "Average response time (ms)"),
    ("utilization", "CPU utilization (%)"),
    ("throughput", "Throughput (processes/s)"),
    ("context_switches", "Context switches (count)"),
    ("makespan", "Makespan (ms)"),
]
COMPARED_METRICS = [
    ("total_memory_references", "References"),
    ("page_hits", "Hits"),
    ("page_faults", "Faults"),
    ("eviction_count", "Evictions"),
    ("page_fault_rate", "Fault rate (%)"),
    ("page_hit_rate", "Hit rate (%)"),
    ("avg_access_time", "Average access time (ms)"),
]


def compare_replacement_policies(config: RunConfig) -> List[Dict[str, Any]]:
    """Runs FIFO and LRU to completion on the same config and returns one row of memory metrics per policy."""
    trace = config.memory.trace or BASELINE_TRACE
    rows = []
    
    for algorithm in ReplacementAlgorithm:
        controller = RealController()
        controller.load(replace(config, memory=replace(config.memory, algorithm=algorithm, trace=trace)))
        metrics = controller.run(until_tick=MAX_TICKS).snapshot.metrics.get("Memory", {})
        rows.append({"policy": algorithm.value, **{label: metrics[key].value for key, label in COMPARED_METRICS}})
    return rows


def side_by_side(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One row per metric, one column per policy."""
    return [{"metric": label, **{row["policy"]: row[label] for row in rows}} for _, label in COMPARED_METRICS]


def comparison_chart(rows: List[Dict[str, Any]]) -> alt.Chart:
    counts = pd.DataFrame([
        {"policy": row["policy"], "measure": measure, "count": row[measure]}
        for row in rows for measure in ("Hits", "Faults", "Evictions")
    ])
    return alt.Chart(counts).mark_bar().encode(
        x=alt.X("measure:N", title="Measure", sort=["Hits", "Faults", "Evictions"], axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("policy:N", sort=["FIFO", "LRU"]),
        y=alt.Y("count:Q", title="Count (memory references)"),
        color=alt.Color("policy:N", title="Policy",
                        scale=alt.Scale(domain=list(POLICY_COLORS), range=list(POLICY_COLORS.values()))),
        tooltip=["policy", "measure", "count"],
    ).properties(title="FIFO vs LRU on the same trace", height=280)


def compare_scheduling_policies(config: RunConfig,
                                on_progress: Optional[Callable[[int, int, str], None]] = None) -> List[Dict[str, Any]]:
    """Batch experiment: runs every scheduling policy on the same workload and returns one row of process metrics each."""
    rows = []
    policies = list(SchedulingPolicy)
    for index, policy in enumerate(policies):
        if on_progress:
            on_progress(index, len(policies), policy.value)
        quantum = (config.process.quantum_ms or 4) if policy is SchedulingPolicy.ROUND_ROBIN else None
        process = replace(config.process, policy=policy, quantum_ms=quantum)
        controller = RealController()
        controller.load(replace(config, process=process))
        metrics = controller.run(until_tick=MAX_TICKS).snapshot.metrics.get("Process", {})
        rows.append({"policy": policy.value, **{label: metrics[key].value for key, label in SCHEDULING_METRICS
                                                if key in metrics}})
    return rows


def scheduling_table(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One row per metric, one column per scheduling policy."""
    return [{"metric": label, **{row["policy"]: row.get(label) for row in rows}} for _, label in SCHEDULING_METRICS]


def scheduling_chart(rows: List[Dict[str, Any]], metric: str) -> alt.Chart:
    data = pd.DataFrame([{"policy": row["policy"], "value": row.get(metric, 0)} for row in rows])
    return alt.Chart(data).mark_bar(color="#2a78d6").encode(
        x=alt.X("policy:N", title="Scheduling policy", sort=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("value:Q", title=metric),
        tooltip=["policy", alt.Tooltip("value:Q", title=metric, format=".2f")],
    ).properties(title=f"{metric} by scheduling policy", height=260)


def csv_of(table: List[Dict[str, Any]]) -> str:
    return pd.DataFrame(table).to_csv(index=False)


def render_comparison() -> None:
    st.subheader("Comparison")
    render_memory_comparison()
    st.divider()
    render_scheduling_comparison()


def render_memory_comparison() -> None:
    st.markdown("**Page replacement: FIFO vs LRU**")
    config = read_config()
    use_example = st.checkbox("Use the reproducible locality example (pages 1 2 3 1 4 1, 3 frames, 256-byte pages)",
                              key=USE_LOCALITY)
    if use_example:
        config = LOCALITY_EXAMPLE
        st.caption("Hand-worked result: FIFO 5 faults / 1 hit / 2 evictions, LRU 4 faults / 2 hits / 1 eviction.")
    else:
        memory = config.memory
        source = "custom trace from the Scenario Builder" if memory.trace else "the baseline trace (0x0040, 0x10A0, 0x0044, 0x20B0)"
        st.caption(f"Both policies run on {source} with {memory.total_frames} frames, {memory.page_size}-byte pages "
                   f"and {memory.fault_latency}-tick fault latency, taken from the sidebar.")

    if st.button("Run FIFO vs LRU", type="primary", key="run-memory-comparison"):
        with st.spinner("Running both policies..."):
            st.session_state[RESULTS] = compare_replacement_policies(config)

    rows = st.session_state.get(RESULTS)
    if not rows:
        st.caption("No comparison yet.")
        return
    table = side_by_side(rows)
    st.dataframe(table, hide_index=True)
    st.download_button("Download FIFO vs LRU table (CSV)", csv_of(table), "fifo_vs_lru.csv", "text/csv",
                       key="memory-comparison-csv")
    st.altair_chart(comparison_chart(rows), width="stretch")
    st.caption("If no page is ever evicted, both policies give the same result. To see them differ, use the "
               "locality example or a trace in the Scenario Builder that uses more pages than there are frames.")


def render_scheduling_comparison() -> None:
    st.markdown("**CPU scheduling: batch experiment over every policy**")
    config = read_config()
    quantum = config.process.quantum_ms or 4
    st.caption(f"Runs FCFS, SJF, SRTF, Round Robin (q = {quantum} ms) and Priority on the same workload "
               f"(scenario '{config.scenario_id}', seed {config.seed}, context switch {config.process.context_switch_ms} ms).")

    if st.button("Run scheduling batch", type="primary", key="run-scheduling-comparison"):
        progress = st.progress(0.0, text="Starting batch...")

        def show(index: int, total: int, name: str) -> None:
            progress.progress(index / total, text=f"Running {name} ({index + 1} of {total})...")

        st.session_state[SCHEDULING_RESULTS] = compare_scheduling_policies(config, on_progress=show)
        progress.empty()

    rows = st.session_state.get(SCHEDULING_RESULTS)
    if not rows:
        st.caption("No batch run yet.")
        return
    table = scheduling_table(rows)
    st.dataframe(table, hide_index=True)
    st.download_button("Download scheduling table (CSV)", csv_of(table), "scheduling_comparison.csv", "text/csv",
                       key="scheduling-comparison-csv")
    metric = st.selectbox("Chart metric", [label for _, label in SCHEDULING_METRICS], key="scheduling-chart-metric")
    st.altair_chart(scheduling_chart(rows, metric), width="stretch")
