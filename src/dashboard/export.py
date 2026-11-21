"""Export tab (spec 5): save the configuration, event log, per-manager CSV,
charts and a summary report.

Everything exported comes from the simulation (config, snapshot, events), so no
host paths, user names or other machine details end up in the files.
"""

import json
from dataclasses import asdict
from enum import Enum
from typing import Any

import pandas as pd
import streamlit as st

from src.core.controller_api import RunConfig, RunStatus, Snapshot
from src.dashboard.process_timeline import state_intervals, timeline_chart
from src.dashboard.views.comparison import RESULTS as MEMORY_RESULTS, comparison_chart


def config_json(config: RunConfig) -> str:
    def plain(value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, dict):
            return {k: plain(v) for k, v in value.items()}
        if isinstance(value, list):
            return [plain(v) for v in value]
        return value

    return json.dumps(plain(asdict(config)), indent=2)


def events_csv(events: list) -> str:
    return pd.DataFrame([e.to_dict() for e in events]).to_csv(index=False)


def all_metrics_csv(snapshot: Snapshot) -> str:
    rows = [{"manager": manager, "metric": key, "value": metric.value, "unit": metric.unit}
            for manager, metrics in snapshot.metrics.items() for key, metric in metrics.items()]
    return pd.DataFrame(rows, columns=["manager", "metric", "value", "unit"]).to_csv(index=False)


def summary_report(snapshot: Snapshot, events: list) -> str:
    config = snapshot.config
    lines = [
        "# OS Simulator run summary",
        "",
        f"- Run ID: {snapshot.run_id}",
        f"- Scenario: {config.scenario_id}",
        f"- Seed: {config.seed}",
        f"- Status: {snapshot.status.value}",
        f"- Simulation time: {snapshot.tick} ms",
        f"- Scheduling policy: {config.process.policy.value}",
        f"- Page replacement: {config.memory.algorithm.value}, {config.memory.total_frames} frames, "
        f"{config.memory.page_size}-byte pages",
        f"- Events recorded: {len(events)}",
        "",
    ]
    for manager, metrics in snapshot.metrics.items():
        lines += [f"## {manager}", "", "| Metric | Value | Unit |", "|---|---|---|"]
        lines += [f"| {key} | {metric.value:g} | {metric.unit} |" for key, metric in metrics.items()]
        lines.append("")
    return "\n".join(lines)


def render_export(snapshot: Snapshot, events: list) -> None:
    st.subheader("Export")
    if snapshot.status is RunStatus.NOT_LOADED:
        st.caption("Load a run to export its results.")
        return
    st.caption("Files contain simulated data only: configuration, events, metrics and charts.")
    prefix = snapshot.run_id

    st.markdown("**Run**")
    config_col, report_col = st.columns(2)
    config_col.download_button("Configuration (JSON)", config_json(snapshot.config), f"{prefix}-config.json",
                               "application/json", key="export-config")
    report_col.download_button("Summary report (Markdown)", summary_report(snapshot, events), f"{prefix}-summary.md",
                               "text/markdown", key="export-report")

    st.markdown("**Logs and per-manager data**")
    events_col, metrics_col = st.columns(2)
    events_col.download_button("Full event log (CSV)", events_csv(events), f"{prefix}-events.csv", "text/csv",
                               key="export-events", disabled=not events)
    metrics_col.download_button("All manager metrics (CSV)", all_metrics_csv(snapshot), f"{prefix}-metrics.csv",
                                "text/csv", key="export-metrics")
    st.caption("Each manager tab also has its own event log and metrics CSV in its Event log section.")

    st.markdown("**Charts**")
    st.caption("Charts download as interactive HTML pages that open in any browser.")
    timeline_col, memory_col = st.columns(2)
    intervals = state_intervals(events, now=snapshot.tick)
    timeline_col.download_button("Process state timeline (HTML)",
                                 timeline_chart(intervals).to_html() if intervals else "",
                                 f"{prefix}-process-timeline.html", "text/html", key="export-timeline",
                                 disabled=not intervals)
    memory_rows = st.session_state.get(MEMORY_RESULTS)
    memory_col.download_button("FIFO vs LRU chart (HTML)",
                               comparison_chart(memory_rows).to_html() if memory_rows else "",
                               "fifo-vs-lru.html", "text/html", key="export-memory-chart",
                               disabled=not memory_rows, help=None if memory_rows else "Run FIFO vs LRU in the Comparison tab first.")
