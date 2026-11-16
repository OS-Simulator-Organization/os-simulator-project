from pathlib import Path
from streamlit.testing.v1 import AppTest

ENTRYPOINT = Path(__file__).parent.parent / "streamlit_app.py"


def run_app() -> AppTest:
    return AppTest.from_file(str(ENTRYPOINT), default_timeout=10).run()


def test_device_tab_renders_unloaded_defaults():
    """Verifies the Device tab renders the 3 default devices and metrics before loading a run."""
    app = run_app()
    assert not app.exception

    # Verify Device tab exists in main tabs
    tab_labels = [t.label for t in app.tabs]
    assert "Device" in tab_labels

    # Verify top-level metric cards render cleanly with default 0 values
    metric_labels = [m.label for m in app.metric]
    assert "Completed Requests" in metric_labels
    assert "Pending Queue" in metric_labels
    assert "Total Seek Distance" in metric_labels
    assert "Device Failures" in metric_labels

    # Verify all 3 required device types are represented in the status metrics
    assert any("DISK_1 (Storage Disk)" in lbl for lbl in metric_labels)
    assert any("PRINTER_1 (Printer)" in lbl for lbl in metric_labels)
    assert any("KEYBOARD_1 (Keyboard)" in lbl for lbl in metric_labels)


def test_device_tab_renders_after_load_and_run():
    """Verifies the Device tab updates metrics, dataframes, and charts without type errors after running."""
    app = run_app()

    # Click 'Load and reset' in sidebar
    app.sidebar.button[0].click().run()
    assert not app.exception

    # Step simulation forward 8 ticks so baseline requests (DISK_1, PRINTER_1, KEYBOARD_1) complete
    controller = app.session_state.controller
    for _ in range(8):
        controller.step()
    app.run()

    assert not app.exception

    # Verify Device Registry Overview dataframe rendered properly
    assert len(app.dataframe) >= 1

    # Verify completed requests metric updated (> 0)
    completed_metrics = [m for m in app.metric if m.label == "Completed Requests"]
    assert completed_metrics
    assert int(completed_metrics[0].value) == 3