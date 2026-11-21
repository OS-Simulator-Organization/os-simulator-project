"""Per-tick memory history for the Memory tab's over-time charts.

The Memory manager's snapshot only holds the current state, and Run can jump
many ticks at once, so the history is rebuilt by replaying the loaded run on a
fresh controller. Runs are deterministic (same config and seed give the same
result), so the replay matches the live run tick for tick.
"""

from typing import Any, Dict, List

from src.core.controller import RealController
from src.core.controller_api import RunConfig, RunStatus


def memory_history(config: RunConfig, upto_tick: int) -> Dict[str, List[Dict[str, Any]]]:
    """Returns "frames" (one row per frame per tick), "accesses" (one row per hit or fault)
    and "evictions" (one row each time a frame's page is replaced by another page)."""
    controller = RealController()
    controller.load(config)
    memory = controller.engine.get_manager("Memory")
    frames: List[Dict[str, Any]] = []
    accesses: List[Dict[str, Any]] = []
    evictions: List[Dict[str, Any]] = []
    previous: Dict[int, str] = {}
    hits = faults = 0

    for tick in range(upto_tick):
        if controller.snapshot().status not in (RunStatus.READY, RunStatus.PAUSED):
            break
        controller.step()
        state = memory.snapshot()
        for frame in state["frames"]:
            page = frame["page_number"]
            contents = f"page {page}" if page is not None else "free"
            frames.append({
                "tick": tick,
                "frame": frame["frame_id"],
                "page": page,
                "contents": contents,
            })
            # A full frame that now holds a different page had its old page evicted.
            old = previous.get(frame["frame_id"], "free")
            if old != "free" and contents not in ("free", old):
                evictions.append({"tick": tick, "frame": frame["frame_id"], "evicted": old, "loaded": contents})
            previous[frame["frame_id"]] = contents
        # The manager keeps running totals, so this tick's hits and faults are the increase.
        for result, total, before in (("Hit", state["hit_count"], hits), ("Fault", state["page_fault_count"], faults)):
            if total > before:
                accesses.append({"tick": tick, "result": result, "count": total - before})
        hits, faults = state["hit_count"], state["page_fault_count"]

    return {"frames": frames, "accesses": accesses, "evictions": evictions}
