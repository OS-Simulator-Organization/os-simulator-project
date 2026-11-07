"""Comparison tab: FIFO vs LRU page replacement on the same trace (spec 4.2 and 5).

Each policy runs on a fresh controller with the identical sidebar config; only
the replacement algorithm differs. The baseline scenario ignores the chosen
algorithm unless traces are given, so the baseline trace is passed explicitly
when no custom traces have been applied.
"""

from dataclasses import replace
from typing import Any, Dict, List

import altair as alt
import pandas as pd
import streamlit as st

from src.core.controller import RealController
from src.core.controller_api import ReplacementAlgorithm, RunConfig
from src.dashboard.config_sidebar import read_config

RESULTS = "memory-comparison"
MAX_TICKS = 10_000
BASELINE_TRACES = {"P1": ["0x0040", "0x10A0", "0x0044", "0x20B0"]}
POLICY_COLORS = {"FIFO": "#2a78d6", "LRU": "#eb6834"}
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
    traces = config.memory.traces or BASELINE_TRACES
    rows = []
    for algorithm in ReplacementAlgorithm:
        controller = RealController()
        controller.load(replace(config, memory=replace(config.memory, algorithm=algorithm, traces=traces)))
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


def render_comparison() -> None:
    st.subheader("Comparison")
    st.markdown("**Page replacement: FIFO vs LRU**")
    config = read_config()
    memory = config.memory
    source = "custom traces from the Scenario Builder" if memory.traces else "the baseline trace (0x0040, 0x10A0, 0x0044, 0x20B0)"
    st.caption(f"Both policies run on {source} with {memory.total_frames} frames, {memory.page_size}-byte pages "
               f"and {memory.fault_latency}-tick fault latency, taken from the sidebar.")

    if st.button("Run FIFO vs LRU", type="primary", key="run-memory-comparison"):
        with st.spinner("Running both policies..."):
            st.session_state[RESULTS] = compare_replacement_policies(config)

    rows = st.session_state.get(RESULTS)
    if not rows:
        st.caption("No comparison yet.")
        return
    st.dataframe(side_by_side(rows), hide_index=True)
    st.altair_chart(comparison_chart(rows), width="stretch")
    st.caption("If no page is ever evicted, both policies give the same result. To see them differ, add a trace "
               "in the Scenario Builder that uses more pages than there are frames.")
