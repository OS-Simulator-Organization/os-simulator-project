from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.core.controller_api import NetworkConfig, NetworkPolicy, RunConfig
from src.dashboard.config_sidebar import describe_network_config

ENTRYPOINT = Path(__file__).parent.parent / "streamlit_app.py"


def test_describe_network_config_formats_policy_and_buffer():
    cfg = RunConfig(network=NetworkConfig(queue_policy=NetworkPolicy.PRIORITY, buffer_capacity=16))
    desc = describe_network_config(cfg)
    assert "PRIORITY" in desc
    assert "16" in desc


def loaded_app() -> AppTest:
    app = AppTest.from_file(str(ENTRYPOINT), default_timeout=30).run()
    return app.sidebar.button[0].click().run()


def test_network_tab_controls_step_and_reset():
    app = loaded_app()
    app.button(key="network-step").click().run()
    assert app.session_state.controller.snapshot().tick == 1
    assert any(e.manager == "Network" for e in app.session_state.events)

    app.button(key="network-reset").click().run()
    assert app.session_state.controller.snapshot().tick == 0
    assert app.session_state.events == []


def test_network_tab_renders_without_exceptions():
    app = loaded_app()
    assert not app.exception
    assert "Network" in app.session_state.controller.engine.managers