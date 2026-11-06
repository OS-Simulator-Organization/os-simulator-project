from typing import Dict, List, Any, Optional
from src.core.base_manager import BaseManager
from src.core.models import FileNode
from src.core.events import EventRecord


class FileManager(BaseManager):

    def __init__(self):
        """
        Initializes all object fields to defaults
        Might change later depening on what bahavior we want
        """
        super().__init__("File")
        self.config: Dict[str, Any] = {}
        self.current_time: float = 0.0
        self.root: Optional[FileNode] = None
        self.pending_io_operations: List[Dict[str, Any]] = []
        self.reads_count: int = 0
        self.writes_count: int = 0
        self.bytes_read: int = 0
        self.bytes_written: int = 0

    def configure(self, config: Dict[str, Any]) -> None:
        """Initialize disk geometry and allocation policies"""
        self.config = config

        # Create root directory node
        self.root = FileNode(
            path ="/",
            name="/",
            is_dir=True,
            owner_id="root",
            permissions="rwx",
            size=0,
            children={}
        )

    def load(self, initial_state: Dict[str, Any]) -> None:
        """Pre populate the file system structure or pending I/O work"""
        self.current_time = 0.0
        self.reads_count = 0
        self.writes_count = 0
        self.bytes_read = 0
        self.bytes_written = 0

        # Load initial directory structure or initial file allocations
        initial_files = initial_state.get("files", [])
        for file_info in initial_files:
            self._create_file_node(file_info)

        # Queue initial scheduled file requests/workload
        self.pending_io_operations = initial_state.get("io_requests", [])

    def reset(self) -> None:
        pass

    def step(self, current_time: float) -> List[EventRecord]:
        """Advance file system state by one tick, processing scheduled I/O requests"""
        self.current_time = current_time
        events: List[EventRecord] = []

        if not self.pending_io_operations:
            return events

        # Process active I/O requests for this tick
        remaining_requests = []
        for req in self.pending_io_operations:
            if req.get("arrival_time", 0.0) <= self.current_time:
                # Execute file system operation (e.g., CREATE, READ, WRITE, DELETE)
                op_events = self._execute_io_operation(req)
                events.extend(op_events)
            else:
                remaining_requests.append(req)

        self.pending_io_operations = remaining_requests
        return events

    def run(self, stop_condition: Optional[Any] = None) -> List[EventRecord]:
        """Continuously run file system steps until requests are fulfilled or stopped"""
        all_events: List[EventRecord] = []

        while True:
            if stop_condition is not None and self._should_stop(stop_condition):
                break

            step_events = self.step(self.current_time)
            all_events.extend(step_events)

            self.current_time += 1.0

            if self._is_finished():
                break

        return all_events

    def snapshot(self) -> Dict[str, Any]:
        """Capture current file system tree and block usage for dashboard rendering."""
        return {
            "current_time": self.current_time,
            "file_tree": self._serialize_tree(self.root) if self.root else {},
        }

    def metrics(self) -> Dict[str, Any]:
        """Return I/O and storage utilization performance metrics"""
        return {
            "reads_count": self.reads_count,
            "writes_count": self.writes_count,
            "bytes_read": self.bytes_read,
            "bytes_written": self.bytes_written
        }

    def validate(self) -> List[str]:
        pass
    
    def export(self, export_format: str = "json") -> Any:
        pass

    def _resolve_node(self, path: str) -> Optional[FileNode]:
            """Traverse the directory tree to find a node by path."""
            clean = path.strip("/")
            if not clean:
                return self.root
            current = self.root
            for part in clean.split("/"):
                if not current or not current.is_dir or part not in current.children:
                    return None
                current = current.children[part]
            return current

    def create_directory(self, path: str, owner_id: str = "root", permissions: str = "rwx") -> tuple[bool, str]:
        clean = path.strip("/")
        parts = clean.split("/")
        name = parts[-1]
        parent_path = "/" + "/".join(parts[:-1]) if len(parts) > 1 else "/"
        parent = self._resolve_node(parent_path)

        if not parent or not parent.is_dir:
            return False, f"Parent directory '{parent_path}' not found"
        if name in parent.children:
            return False, f"Directory or file '{name}' already exists"

        new_dir = FileNode(
            path="/" + clean,
            name=name,
            is_dir=True,
            owner_id=owner_id,
            permissions=permissions,
            size=0,
            content="",
            parent_path=parent.path,
            children={}
        )
        parent.children[name] = new_dir
        return True, "Directory created successfully"

    def create_file(self, path: str, owner_id: str = "root", permissions: str = "rw-", content: str = "") -> tuple[bool, str]:
        clean = path.strip("/")
        parts = clean.split("/")
        name = parts[-1]
        parent_path = "/" + "/".join(parts[:-1]) if len(parts) > 1 else "/"
        parent = self._resolve_node(parent_path)

        if not parent or not parent.is_dir:
            return False, f"Parent directory '{parent_path}' not found"
        if name in parent.children:
            return False, f"File or directory '{name}' already exists"

        new_file = FileNode(
            path="/" + clean,
            name=name,
            is_dir=False,
            owner_id=owner_id,
            permissions=permissions,
            size=len(content.encode("utf-8")),
            content=content,
            parent_path=parent.path,
            children={}
        )
        parent.children[name] = new_file
        return True, "File created successfully"

    def read_file(self, path: str, user_id: str = "root") -> tuple[bool, str]:
        node = self._resolve_node(path)
        if not node:
            return False, f"File '{path}' not found"
        if node.is_dir:
            return False, f"'{path}' is a directory, not a file"
        if "r" not in node.permissions and node.owner_id != user_id:
            return False, f"Read permission denied for user '{user_id}'"

        self.reads_count += 1
        self.bytes_read += node.size
        return True, node.content

    def write_file(self, path: str, content: str, user_id: str = "root", append: bool = False) -> tuple[bool, str]:
        node = self._resolve_node(path)
        if not node:
            return False, f"File '{path}' not found"
        if node.is_dir:
            return False, f"'{path}' is a directory, not a file"
        if "w" not in node.permissions and node.owner_id != user_id:
            return False, f"Write permission denied for user '{user_id}'"

        if append:
            node.content += content
        else:
            node.content = content

        node.size = len(node.content.encode("utf-8"))
        self.writes_count += 1
        self.bytes_written += len(content.encode("utf-8"))
        return True, "Write successful"

    def delete(self, path: str, user_id: str = "root") -> tuple[bool, str]:
        clean = path.strip("/")
        parts = clean.split("/")
        name = parts[-1]
        parent_path = "/" + "/".join(parts[:-1]) if len(parts) > 1 else "/"
        parent = self._resolve_node(parent_path)

        if not parent or name not in parent.children:
            return False, f"Item '{path}' not found"

        node = parent.children[name]
        if "w" not in parent.permissions and parent.owner_id != user_id:
            return False, f"Permission denied to remove '{name}'"

        del parent.children[name]
        return True, "Deleted successfully"

    def chmod(self, path: str, permissions: str) -> tuple[bool, str]:
        node = self._resolve_node(path)
        if not node:
            return False, f"Path '{path}' not found"
        node.permissions = permissions
        return True, "Permissions updated"

    # Internal helper methods
    def _create_file_node(self, file_info: Dict[str, Any]) -> None:
        path = file_info.get("path", "")
        owner_id = file_info.get("owner_id", "root")
        permissions = file_info.get("permissions", "rw-")
        content = file_info.get("content", "")
        self.create_file(path, owner_id=owner_id, permissions=permissions, content=content)

    def _execute_io_operation(self, req: Dict[str, Any]) -> List[EventRecord]:
        events = []
        operation_type = req.get("op", req.get("operation", "")).upper()
        path = req.get("path", "")
        pid = req.get("pid", "P0")

        if operation_type == "READ":
            success, result = self.read_file(path, user_id=pid)
            if success:
                events.append(EventRecord(
                    tick=int(self.current_time),
                    event_type="FILE_READ_SUCCESS",
                    entity_id=pid,
                    details={"path": path, "size": len(result)}
                ))
            else:
                events.append(EventRecord(
                    tick=int(self.current_time),
                    event_type="FILE_OP_ERROR",
                    entity_id=pid,
                    details={"path": path, "operation": operation_type, "error": result}
                ))

        elif operation_type == "WRITE":
            content = req.get("content", "")
            success, msg = self.write_file(path, content, user_id=pid)
            if success:
                events.append(EventRecord(
                    tick=int(self.current_time),
                    event_type="FILE_WRITE_SUCCESS",
                    entity_id=pid,
                    details={"path": path, "bytes": len(content)}
                ))
            else:
                events.append(EventRecord(
                    tick=int(self.current_time),
                    event_type="FILE_OP_ERROR",
                    entity_id=pid,
                    details={"path": path, "operation": operation_type, "error": msg}
                ))

        elif operation_type == "CREATE":
            is_dir = req.get("is_dir", False)
            if is_dir:
                success, msg = self.create_directory(path, owner_id=pid)
            else:
                success, msg = self.create_file(path, owner_id=pid)

            if success:
                events.append(EventRecord(
                    tick=int(self.current_time),
                    event_type="FILE_CREATE_SUCCESS",
                    entity_id=pid,
                    details={"path": path}
                ))
            else:
                events.append(EventRecord(
                    tick=int(self.current_time),
                    event_type="FILE_OP_ERROR",
                    entity_id=pid,
                    details={"path": path, "operation": operation_type, "error": msg}
                ))

        elif operation_type == "DELETE":
            success, msg = self.delete(path, user_id=pid)
            if success:
                events.append(EventRecord(
                    tick=int(self.current_time),
                    event_type="FILE_DELETE_SUCCESS",
                    entity_id=pid,
                    details={"path": path}
                ))
            else:
                events.append(EventRecord(
                    tick=int(self.current_time),
                    event_type="FILE_OP_ERROR",
                    entity_id=pid,
                    details={"path": path, "operation": operation_type, "error": msg}
                ))

        return events  

    def _serialize_tree(self, node: FileNode) -> Dict[str, Any]:
        return {
            "path": node.path,
            "name": node.name,
            "is_dir": node.is_dir,
            "owner_id": node.owner_id,
            "permissions": node.permissions,
            "size": node.size,
            "children": {k: self._serialize_tree(v) for k, v in node.children.items()}
        }

    def _should_stop(self, stop_condition: Any) -> bool:
        return False

    def _is_finished(self) -> bool:
        return len(self.pending_io_operations) == 0
