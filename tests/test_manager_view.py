from streamlit.testing.v1 import AppTest

from src.core.controller_api import PROCESS_METRIC_UNITS, ProcessConfig, RunConfig, SchedulingPolicy
from src.dashboard.views import VIEWS
from src.dashboard.views.process import describe_config


def render_tab(load: bool, step: bool, view: str = "process"):
    import importlib

    from src.dashboard.manager_view import render_manager_tab
    from src.dashboard.mock_controller import MockController

    VIEW = importlib.import_module(f"src.dashboard.views.{view}").VIEW

    controller = MockController()
    events = []
    if load:
        controller.load(controller.snapshot().config)
    if step:
        events = controller.step().events
    render_manager_tab(VIEW, controller.snapshot(), events)


def render_sidebar_hook():
    import streamlit as st

    from src.dashboard.manager_view import ManagerView, render_sidebar_section

    render_sidebar_section(ManagerView(name="Memory", manager="Memory", render_sidebar=lambda: st.number_input("Frames", value=8)))


def run(function, **kwargs) -> AppTest:
    return AppTest.from_function(function, kwargs=kwargs, default_timeout=10).run()


def test_views_use_schema_manager_names():
    schema_names = {"Process", "Memory", "File", "Security", "Device", "Network", "Parallel"}
    assert {view.manager for view in VIEWS} == schema_names


def test_view_names_are_unique():
    names = [view.name for view in VIEWS]
    assert len(names) == len(set(names))


def test_unloaded_tab_renders_every_section():
    app = run(render_tab, load=False, step=False)
    assert not app.exception
    assert app.subheader[0].value == "Process"
    assert [e.label for e in app.expander] == ["Inputs", "Event log"]
    assert "No metrics yet. Load a run to see them." in [c.value for c in app.caption]


def test_regions_are_labeled():
    markdown = [m.value for m in run(render_tab, load=False, step=False).markdown]
    assert "**CPU Gantt chart**" in markdown
    assert "**Process table**" in markdown


def test_actions_are_disabled_until_wired_up():
    buttons = run(render_tab, load=False, step=False).button
    assert [b.label for b in buttons] == ["Run process tests"]
    assert buttons[0].disabled


def test_loaded_tab_shows_a_metric_per_key():
    app = run(render_tab, load=True, step=False)
    assert len(app.metric) == len(PROCESS_METRIC_UNITS)


def test_event_log_shows_this_managers_events():
    app = run(render_tab, load=True, step=True)
    assert len(app.dataframe) == 1
    assert len(app.dataframe[0].value) == 2


def test_event_log_hides_other_managers_events():
    app = run(render_tab, load=True, step=True, view="memory")
    assert not app.dataframe
    assert "No events yet." in [c.value for c in app.caption]


def test_sidebar_hook_renders_inside_the_managers_section():
    app = run(render_sidebar_hook)
    assert app.expander[0].label == "Memory"
    assert app.number_input[0].label == "Frames"


def test_process_config_summary():
    rr = RunConfig(process=ProcessConfig(SchedulingPolicy.ROUND_ROBIN, quantum_ms=4, context_switch_ms=1))
    assert describe_config(rr) == "Policy: ROUND_ROBIN · Quantum: 4 ms · Context switch: 1 ms"
    assert "Quantum: –" in describe_config(RunConfig())
