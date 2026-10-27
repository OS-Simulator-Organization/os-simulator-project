import csv
from src.core.models import Process, ProcessState


class ValidationError(Exception):
    pass


def load_and_validate_processes(file_path):
    processes = []
    seen_pids = set()

    try:
        with open(file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None:
                raise ValidationError("CSV file is empty or missing a header row.")

            required_columns = ["pid", "arrival_time", "burst_time", "priority"]
            for col in required_columns:
                if col not in reader.fieldnames:
                    raise ValidationError(f"Missing required column: '{col}'")

            line_number = 1
            for row in reader:
                line_number += 1

                pid = row.get("pid", "").strip()
                if not pid:
                    raise ValidationError(f"Line {line_number}: Process ID (pid) cannot be empty.")
                if pid in seen_pids:
                    raise ValidationError(f"Line {line_number}: Duplicate process ID '{pid}' found.")
                seen_pids.add(pid)

                owner_id = row.get("owner_id", "").strip()
                if not owner_id:
                    owner_id = "default_user"

                try:
                    arrival_time = int(row.get("arrival_time", "").strip())
                except ValueError:
                    raise ValidationError(f"Line {line_number} (PID {pid}): arrival_time must be an integer.")

                if arrival_time < 0:
                    raise ValidationError(f"Line {line_number} (PID {pid}): arrival_time cannot be negative.")

                try:
                    burst_time = int(row.get("burst_time", "").strip())
                except ValueError:
                    raise ValidationError(f"Line {line_number} (PID {pid}): burst_time must be an integer.")

                if burst_time <= 0:
                    raise ValidationError(f"Line {line_number} (PID {pid}): burst_time must be greater than 0.")

                try:
                    priority = int(row.get("priority", "").strip())
                except ValueError:
                    raise ValidationError(f"Line {line_number} (PID {pid}): priority must be an integer.")

                new_process = Process(
                    pid=pid,
                    owner_id=owner_id,
                    arrival_time=arrival_time,
                    burst_time=burst_time,
                    priority=priority,
                    remaining_time=burst_time,
                    state=ProcessState.NEW
                )
                processes.append(new_process)

    except FileNotFoundError:
        raise ValidationError(f"Could not find file at: {file_path}")

    if len(processes) == 0:
        raise ValidationError("No process rows found in file.")

    return processes