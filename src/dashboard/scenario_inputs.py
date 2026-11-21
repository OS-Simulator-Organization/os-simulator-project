"""Field definitions, defaults and validation for the Scenario Builder's extra
inputs: file scripts, users/policies, device requests, network links, packets
and failure events (spec section 5).

Column names match what each manager's load() reads, so a validated table can
be handed straight to the manager.
"""

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

PID_FORMAT = re.compile(r"^P\d+$")
FILE_OPS = ("CREATE", "READ", "WRITE", "DELETE")
PERMISSIONS = ("r", "w", "x", "admin", "network")


@dataclass(frozen=True)
class Field:
    name: str
    kind: str = "text"        # text, int, pid, path, choice, bool, permissions
    minimum: int = 0
    unique: bool = False
    required: bool = True
    choices: Tuple[str, ...] = ()


@dataclass(frozen=True)
class InputKind:
    key: str
    title: str
    fields: Tuple[Field, ...]
    defaults: Tuple[Dict[str, Any], ...] = ()
    note: str = ""


def _file_step(time, op, path, pid="P1", content=None, is_dir=False):
    return {"arrival_time": time, "pid": pid, "op": op, "path": path, "content": content, "is_dir": is_dir}


# 16 commands covering create (file and directory), write, read and delete, including six
# intentional errors: duplicate name, missing file, reading a directory, deleted file, missing parent (x2).
DEFAULT_FILE_SCRIPT = (
    _file_step(1, "CREATE", "/docs", is_dir=True),
    _file_step(2, "CREATE", "/docs/notes.txt"),
    _file_step(3, "WRITE", "/docs/notes.txt", content="hello"),
    _file_step(4, "READ", "/docs/notes.txt"),
    _file_step(5, "CREATE", "/docs/notes.txt", pid="P2"),          # error: already exists
    _file_step(6, "READ", "/missing.txt", pid="P2"),               # error: file not found
    _file_step(7, "CREATE", "/logs", pid="P3", is_dir=True),
    _file_step(8, "CREATE", "/logs/app.log", pid="P3"),
    _file_step(9, "WRITE", "/logs/app.log", pid="P3", content="started"),
    _file_step(10, "READ", "/logs", pid="P3"),                     # error: is a directory
    _file_step(11, "DELETE", "/logs/app.log", pid="P4"),
    _file_step(12, "READ", "/logs/app.log", pid="P4"),             # error: deleted file
    _file_step(13, "DELETE", "/nowhere/file.txt", pid="P4"),       # error: missing parent
    _file_step(14, "CREATE", "/tmp/x.txt", pid="P1"),              # error: missing parent
    # A failed file request blocks its process until a later request succeeds, so P1 and P4 end on a success.
    _file_step(15, "CREATE", "/logs/done.txt", pid="P4"),
    _file_step(16, "READ", "/docs/notes.txt", pid="P1"),
)

KINDS = (
    InputKind("file_script", "File script", (
        Field("arrival_time", "int"),
        Field("pid", "pid"),
        Field("op", "choice", choices=FILE_OPS),
        Field("path", "path"),
        Field("content", required=False),
        Field("is_dir", "bool", required=False),
    ), DEFAULT_FILE_SCRIPT,
        "Runs in the File manager. CREATE with is_dir makes a directory; DELETE removes a file or directory."),
    InputKind("users", "Users and policies", (
        Field("user_id", unique=True),
        Field("username"),
        Field("role"),
        Field("permissions", "permissions"),
    ), ({"user_id": "u_alice", "username": "alice", "role": "USER", "permissions": "r, w"},),
        "Added to the Security tab's users. Permissions are a comma list of r, w, x, admin, network. "
        "New users log in with the demo credential demo_default_pass."),
    InputKind("device_requests", "Device requests", (
        Field("request_id", unique=True),
        Field("device_id"),
        Field("pid", "pid"),
        Field("arrival_time", "int"),
        Field("burst_time", "int", minimum=1),
        Field("operation_type"),
    ), (
        {"request_id": "REQ-1", "device_id": "DISK_1", "pid": "P1", "arrival_time": 1, "burst_time": 3, "operation_type": "READ:45"},
        {"request_id": "REQ-2", "device_id": "PRINTER_1", "pid": "P2", "arrival_time": 2, "burst_time": 4, "operation_type": "PRINT"},
    ), "Saved with the scenario. The controller only loads device requests for the baseline scenario so far."),
    InputKind("links", "Network links", (
        Field("src"),
        Field("dst"),
        Field("bandwidth", "int", minimum=1),
        Field("latency", "int"),
        Field("status", "choice", choices=("UP", "DOWN")),
    ), (
        {"src": "NodeA", "dst": "NodeB", "bandwidth": 100, "latency": 1, "status": "UP"},
        {"src": "NodeB", "dst": "NodeC", "bandwidth": 50, "latency": 2, "status": "UP"},
        {"src": "NodeA", "dst": "NodeD", "bandwidth": 80, "latency": 2, "status": "UP"},
    ), "Saved with the scenario. The controller doesn't load custom links yet."),
    InputKind("packets", "Packets", (
        Field("packet_id", unique=True),
        Field("source_node"),
        Field("dest_node"),
        Field("pid", "pid"),
        Field("payload_size", "int", minimum=1),
        Field("ttl", "int", minimum=1),
        Field("priority", "int"),
        Field("creation_time", "int"),
    ), (
        {"packet_id": "PKT-1", "source_node": "NodeA", "dest_node": "NodeC", "pid": "P1", "payload_size": 128,
         "ttl": 5, "priority": 1, "creation_time": 0},
    ), "Saved with the scenario. The controller only loads packets for the baseline scenario so far."),
    InputKind("failures", "Failure events", (
        Field("time", "int"),
        Field("target"),
        Field("event", "choice", choices=("fail", "recover")),
    ), ({"time": 5, "target": "NodeB-NodeC", "event": "fail"}, {"time": 9, "target": "NodeB-NodeC", "event": "recover"}),
        "Saved with the scenario. No manager reads failure events from a scenario yet."),
)
KINDS_BY_KEY = {kind.key: kind for kind in KINDS}


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value)) or str(value).strip() == ""


def validate_rows(kind: InputKind, rows: List[Dict[str, Any]]) -> List[str]:
    """Returns one specific message per problem, e.g. "File script row 3: arrival_time cannot be negative."."""
    errors = []
    seen: Dict[str, set] = {f.name: set() for f in kind.fields if f.unique}
    for number, row in enumerate(rows, start=1):
        where = f"{kind.title} row {number}"
        for field in kind.fields:
            value = row.get(field.name)
            if is_blank(value):
                if field.required:
                    errors.append(f"{where}: {field.name} is required.")
                continue
            text = str(value).strip()
            if field.kind == "int":
                try:
                    number_value = float(text)
                except ValueError:
                    errors.append(f"{where}: {field.name} must be a whole number.")
                    continue
                if not number_value.is_integer():
                    errors.append(f"{where}: {field.name} must be a whole number.")
                elif number_value < field.minimum:
                    word = "cannot be negative" if field.minimum == 0 else f"must be at least {field.minimum}"
                    errors.append(f"{where}: {field.name} {word}.")
            elif field.kind == "pid" and not PID_FORMAT.match(text):
                errors.append(f"{where}: {field.name} must follow the 'P#' format (e.g. P1).")
            elif field.kind == "path" and not text.startswith("/"):
                errors.append(f"{where}: path must start with '/'.")
            elif field.kind == "choice" and text not in field.choices:
                errors.append(f"{where}: {field.name} must be one of {', '.join(field.choices)}.")
            elif field.kind == "permissions":
                unknown = [p for p in split_permissions(text) if p not in PERMISSIONS]
                if unknown:
                    errors.append(f"{where}: unknown permission(s) {', '.join(unknown)}; use {', '.join(PERMISSIONS)}.")
            if field.unique:
                if text in seen[field.name]:
                    errors.append(f"{where}: duplicate {field.name} '{text}'.")
                seen[field.name].add(text)
        if kind.key == "links" and not is_blank(row.get("src")) and row.get("src") == row.get("dst"):
            errors.append(f"{where}: src and dst must be different nodes.")
    return errors


def split_permissions(text: str) -> List[str]:
    return [p.strip() for p in str(text).split(",") if p.strip()]


def clean_rows(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drops empty rows and turns table values into plain Python values (whole numbers become int)."""
    rows = []
    for record in records:
        row = {}
        for key, value in record.items():
            if is_blank(value):
                value = None
            elif hasattr(value, "item"):
                value = value.item()
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            row[key] = value
        if any(v is not None for v in row.values()):
            rows.append(row)
    return rows
