from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.core.events import EventRecord
from src.dashboard.views.file_system import flatten_tree, operation_counts, operation_log

ENTRYPOINT = Path(__file__).parent.parent / "streamlit_app.py"

TREE = {
    "path": "/", "name": "/", "is_dir": True, "owner_id": "root", "permissions": "rwx", "size": 0,
    "children": {
        "docs": {
            "path": "/docs", "name": "docs", "is_dir": True, "owner_id": "root", "permissions": "rwx", "size": 0,
            "children": {
                "notes.txt": {"path": "/docs/notes.txt", "name": "notes.txt", "is_dir": False, "owner_id": "u1",
                              "permissions": "rw-", "size": 11, "children": {}},
            },
        },
    },
}


def file_event(time, action, outcome, pid="P1"):
    return EventRecord(timestamp=time, manager="File", event_type=f"FILE_{action}", entity_id=pid, action=action,
                       previous_state="PENDING", new_state="COMPLETED", outcome=outcome)


def test_flatten_tree_lists_every_path_with_metadata():
    rows = flatten_tree(TREE)
    assert [r["path"] for r in rows] == ["/", "/docs", "/docs/notes.txt"]
    assert rows[2] == {"path": "/docs/notes.txt", "type": "file", "owner": "u1", "permissions": "rw-", "size (bytes)": 11}


def test_flatten_empty_tree():
    assert flatten_tree({}) == []


def test_operation_log_keeps_order_and_only_file_events():
    other = EventRecord(timestamp=0, manager="Process", event_type="X", entity_id="P1", action="DISPATCH",
                        previous_state="READY", new_state="RUNNING", outcome="SUCCESS")
    log = operation_log([file_event(1, "READ", "SUCCESS"), other, file_event(3, "WRITE", "ERROR")])
    assert [(r["time (ms)"], r["command"], r["outcome"]) for r in log] == [(1, "READ", "SUCCESS"), (3, "WRITE", "ERROR")]


def test_operation_counts_split_success_and_failure_by_command():
    log = operation_log([file_event(1, "READ", "SUCCESS"), file_event(2, "READ", "ERROR"), file_event(3, "WRITE", "SUCCESS")])
    assert operation_counts(log) == [
        {"command": "READ", "succeeded": 1, "failed": 1},
        {"command": "WRITE", "succeeded": 1, "failed": 0},
    ]


def loaded_app() -> AppTest:
    app = AppTest.from_file(str(ENTRYPOINT), default_timeout=30).run()
    return app.sidebar.button[0].click().run()


def test_file_tab_controls_step_and_reset():
    app = loaded_app()
    for _ in range(4):
        app.button(key="file-step").click().run()
    assert app.session_state.controller.snapshot().tick == 4
    assert any(e.manager == "File" for e in app.session_state.events)
    app.button(key="file-reset").click().run()
    assert app.session_state.controller.snapshot().tick == 0
    assert app.session_state.events == []


def test_file_tab_shows_metadata_storage_and_operation_log():
    app = loaded_app()
    app.button(key="file-run-to-end").click().run()
    assert not app.exception
    assert app.selectbox(key="file-node").options[:2] == ["/", "/system.log"]
    markdown = [m.value for m in app.markdown]
    for region in ("**Node metadata**", "**Storage composition**", "**Operation log**"):
        assert region in markdown
    assert "No file operations yet. Press Step or Run." not in [c.value for c in app.caption]
