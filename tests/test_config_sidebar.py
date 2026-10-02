from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.core.controller_api import ProcessConfig, RunConfig, RunStatus, SchedulingPolicy
from src.dashboard.config_sidebar import CONTEXT_SWITCH, POLICY, POLICY_LABELS, QUANTUM, SEED, config_errors
from src.dashboard.mock_controller import MockController

ENTRYPOINT = Path(__file__).parent.parent / "streamlit_app.py"
WARNING = "Settings changed. Press Load and reset to apply them."


def run_app() -> AppTest:
    return AppTest.from_file(str(ENTRYPOINT), default_timeout=10).run()


def load(app: AppTest) -> AppTest:
    return app.sidebar.button[0].click().run()


def pick_policy(app: AppTest, policy: SchedulingPolicy) -> AppTest:
    return app.selectbox(key=POLICY).set_value(POLICY_LABELS[policy]).run()


def snapshot(app: AppTest):
    return app.session_state.controller.snapshot()


def messages(elements) -> list:
    return [element.value for element in elements]


def test_starts_unloaded_with_load_enabled():
    app = run_app()
    assert snapshot(app).status is RunStatus.NOT_LOADED
    assert "No run loaded. Press Load and reset to start." in messages(app.sidebar.info)
    assert not app.sidebar.button[0].disabled


def test_load_starts_a_run_with_the_sidebar_config():
    app = load(run_app())
    assert snapshot(app).status is RunStatus.READY
    assert snapshot(app).config == RunConfig()
    assert not app.sidebar.info
    assert not app.sidebar.warning


def test_changing_a_setting_after_load_warns():
    app = load(run_app())
    app.number_input(key=SEED).set_value(5).run()
    assert messages(app.sidebar.warning) == [WARNING]


def test_changing_a_setting_back_clears_the_warning():
    app = load(run_app())
    app.number_input(key=SEED).set_value(5).run()
    app.number_input(key=SEED).set_value(0).run()
    assert not app.sidebar.warning


def test_reloading_applies_changes_and_clears_the_warning():
    app = load(run_app())
    first_run = snapshot(app).run_id
    app.number_input(key=SEED).set_value(5).run()
    load(app)
    assert snapshot(app).config.seed == 5
    assert snapshot(app).run_id != first_run
    assert not app.sidebar.warning


def test_load_clears_the_event_log():
    app = load(run_app())
    app.session_state.events = app.session_state.controller.step().events
    load(app)
    assert app.session_state.events == []


def test_round_robin_shows_quantum_and_context_switch():
    app = pick_policy(run_app(), SchedulingPolicy.ROUND_ROBIN)
    labels = [number_input.label for number_input in app.sidebar.number_input]
    assert "Time quantum (ms)" in labels
    assert "Context switch cost (ms)" in labels


def test_other_policies_hide_quantum_and_context_switch():
    app = pick_policy(pick_policy(run_app(), SchedulingPolicy.ROUND_ROBIN), SchedulingPolicy.FCFS)
    labels = [number_input.label for number_input in app.sidebar.number_input]
    assert labels == ["Seed"]


def test_unsupported_policy_blocks_load():
    app = pick_policy(run_app(), SchedulingPolicy.ROUND_ROBIN)
    assert messages(app.sidebar.error) == ["Round Robin is not supported yet."]
    assert app.sidebar.button[0].disabled


def test_switching_back_to_a_supported_policy_unblocks_load():
    app = pick_policy(pick_policy(run_app(), SchedulingPolicy.SJF), SchedulingPolicy.FCFS)
    assert not app.sidebar.error
    assert not app.sidebar.button[0].disabled


def store_read_config():
    import streamlit as st

    from src.dashboard.config_sidebar import read_config

    st.session_state.result = read_config()


def read_config_with(state: dict) -> RunConfig:
    app = AppTest.from_function(store_read_config, default_timeout=10)
    for key, value in state.items():
        app.session_state[key] = value
    return app.run().session_state.result


def test_round_robin_values_reach_the_config():
    config = read_config_with({SEED: 3, POLICY: "Round Robin", QUANTUM: 6, CONTEXT_SWITCH: 2})
    assert config == RunConfig(seed=3, process=ProcessConfig(SchedulingPolicy.ROUND_ROBIN, quantum_ms=6, context_switch_ms=2))


def test_leftover_round_robin_values_are_ignored_by_other_policies():
    config = read_config_with({POLICY: "First come, first served", QUANTUM: 6, CONTEXT_SWITCH: 2})
    assert config == RunConfig()


def test_process_tab_header_shows_the_loaded_config():
    app = load(run_app())
    assert "Policy: FCFS · Quantum: – · Context switch: 0 ms" in messages(app.caption)


def test_config_errors_combine_validation_and_support():
    controller = MockController()
    bad_round_robin = RunConfig(process=ProcessConfig(SchedulingPolicy.ROUND_ROBIN, quantum_ms=0))
    errors = config_errors(bad_round_robin, controller)
    assert "Round Robin needs a time quantum of at least 1 ms." in errors
    assert "Round Robin is not supported yet." in errors
    assert config_errors(RunConfig(), controller) == []
