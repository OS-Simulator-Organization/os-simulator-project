from collections import deque
import heapq
from typing import Any, Dict, List, Optional, Tuple
from src.core.base_manager import BaseManager
from src.core.events import EventRecord
from src.core.models import Packet, PacketStatus


class NetworkManager(BaseManager):
    """
    Simulates node-to-node topology, link capacities, buffer limits,
    FIFO/PRIORITY packet scheduling, shortest-path routing with rerouting,
    TTL expiration, link failures/recovery, and network metrics.
    """

    def __init__(self):
        super().__init__("Network")
        self.nodes: List[str] = ["NodeA", "NodeB", "NodeC", "NodeD"]
        self.links: Dict[str, Dict[str, Any]] = {
            "NodeA-NodeB": {"src": "NodeA", "dst": "NodeB", "bandwidth": 100, "latency": 1.0, "status": "UP"},
            "NodeB-NodeC": {"src": "NodeB", "dst": "NodeC", "bandwidth": 50, "latency": 2.0, "status": "UP"},
            "NodeA-NodeD": {"src": "NodeA", "dst": "NodeD", "bandwidth": 80, "latency": 2.0, "status": "UP"},
            "NodeD-NodeC": {"src": "NodeD", "dst": "NodeC", "bandwidth": 80, "latency": 1.5, "status": "UP"},
        }
        self.buffer_capacity: int = 16
        self.packet_buffer: List[Packet] = []
        self.delivered_packets: List[Packet] = []
        self.dropped_packets: List[Packet] = []
        self.queue_policy: str = "FIFO"  # "FIFO" or "PRIORITY"
        self.routing_method: str = "DIJKSTRA"  # Shortest path by link latency/cost across UP links
        self.total_delay: float = 0.0
        self.current_time: float = 0.0

    def configure(self, config: Dict[str, Any]) -> None:
        self.queue_policy = str(config.get("queue_policy", "FIFO")).upper()
        if self.queue_policy not in ("FIFO", "PRIORITY"):
            self.queue_policy = "FIFO"
        self.buffer_capacity = int(config.get("buffer_capacity", 16))
        if config.get("nodes"):
            self.nodes = list(config["nodes"])
        if config.get("links"):
            self._load_links(config["links"])
        self.is_configured = True

    def _load_links(self, raw_links: Any) -> None:
        self.links.clear()
        if isinstance(raw_links, dict):
            for edge_key, info in raw_links.items():
                parts = edge_key.split("-")
                src = info.get("src", parts[0] if len(parts) > 0 else "")
                dst = info.get("dst", parts[1] if len(parts) > 1 else "")
                self.links[edge_key] = {
                    "src": src,
                    "dst": dst,
                    "bandwidth": float(info.get("bandwidth", 100)),
                    "latency": float(info.get("latency", 1.0)),
                    "status": str(info.get("status", "UP")).upper(),
                }
        elif isinstance(raw_links, list):
            for info in raw_links:
                src = info.get("src", "")
                dst = info.get("dst", "")
                edge_key = info.get("edge", f"{src}-{dst}")
                self.links[edge_key] = {
                    "src": src,
                    "dst": dst,
                    "bandwidth": float(info.get("bandwidth", 100)),
                    "latency": float(info.get("latency", 1.0)),
                    "status": str(info.get("status", "UP")).upper(),
                }

    def load(self, input_data: Any) -> None:
        packets_raw: List[Any] = []
        if isinstance(input_data, dict):
            if input_data.get("nodes"):
                self.nodes = list(input_data["nodes"])
            if input_data.get("links"):
                self._load_links(input_data["links"])
            if "buffer_capacity" in input_data:
                self.buffer_capacity = int(input_data["buffer_capacity"])
            packets_raw = input_data.get("packets", [])
        elif isinstance(input_data, list):
            packets_raw = input_data

        for idx, item in enumerate(packets_raw):
            if isinstance(item, Packet):
                pkt = item
            elif isinstance(item, dict):
                ttl_val = item.get("ttl", item.get("hop_limit", 64))
                pkt = Packet(
                    packet_id=str(item.get("packet_id", f"PKT-{len(self.packet_buffer) + len(self.delivered_packets) + len(self.dropped_packets) + idx + 1}")),
                    source_node=str(item.get("source_node", item.get("source", self.nodes[0] if self.nodes else "NodeA"))),
                    dest_node=str(item.get("dest_node", item.get("destination", self.nodes[-1] if self.nodes else "NodeC"))),
                    source_process_id=str(item.get("source_process_id", item.get("pid", "P1"))),
                    payload_size=int(item.get("payload_size", item.get("size", 64))),
                    hop_limit=int(ttl_val),
                    priority=int(item.get("priority", 0)),
                    creation_time=float(item.get("creation_time", 0.0)),
                    status=PacketStatus.QUEUED,
                )
            else:
                continue

            if len(self.packet_buffer) >= self.buffer_capacity:
                pkt.status = PacketStatus.DROPPED
                self.dropped_packets.append(pkt)
            else:
                pkt.status = PacketStatus.QUEUED
                self.packet_buffer.append(pkt)

    def reset(self) -> None:
        self.packet_buffer.clear()
        self.delivered_packets.clear()
        self.dropped_packets.clear()
        self.total_delay = 0.0
        self.current_time = 0.0
        for data in self.links.values():
            data["status"] = "UP"

    def fail_link(self, link_id: str) -> None:
        if link_id in self.links:
            self.links[link_id]["status"] = "DOWN"

    def recover_link(self, link_id: str) -> None:
        if link_id in self.links:
            self.links[link_id]["status"] = "UP"

    def find_route(self, source: str, destination: str) -> Tuple[List[str], float]:
        """
        Computes shortest path using Dijkstra's algorithm over active (UP) links,
        weighted by link propagation latency (with bandwidth tie-breaker).
        """
        if source == destination:
            return [source], 0.0

        adjacency: Dict[str, List[Tuple[str, float, float]]] = {n: [] for n in self.nodes}
        for data in self.links.values():
            if data.get("status", "UP") != "UP":
                continue
            u, v = data.get("src"), data.get("dst")
            latency = float(data.get("latency", 1.0))
            bw = max(1.0, float(data.get("bandwidth", 100.0)))
            cost = latency + (100.0 / bw) * 0.1
            if u in adjacency:
                adjacency[u].append((v, cost, latency))
            if v in adjacency:
                adjacency[v].append((u, cost, latency))

        pq: List[Tuple[float, str, List[str], float]] = [(0.0, source, [source], 0.0)]
        visited = set()

        while pq:
            cost_so_far, curr, path, lat_so_far = heapq.heappop(pq)
            if curr in visited:
                continue
            visited.add(curr)

            if curr == destination:
                return path, lat_so_far

            for nxt, edge_cost, edge_lat in adjacency.get(curr, []):
                if nxt not in visited:
                    heapq.heappush(pq, (cost_so_far + edge_cost, nxt, path + [nxt], lat_so_far + edge_lat))

        return [], float("inf")

    def is_idle(self) -> bool:
        return len(self.packet_buffer) == 0

    def step(self, current_time: float) -> List[EventRecord]:
        self.current_time = float(current_time)
        events: List[EventRecord] = []

        ready_indices = [i for i, p in enumerate(self.packet_buffer) if p.creation_time <= self.current_time]
        if not ready_indices:
            return events

        if self.queue_policy == "PRIORITY":
            # Lower priority number = higher priority; tie-break by creation_time and buffer order
            chosen_idx = min(ready_indices, key=lambda i: (self.packet_buffer[i].priority, self.packet_buffer[i].creation_time, i))
        else:
            chosen_idx = ready_indices[0]

        pkt = self.packet_buffer.pop(chosen_idx)

        # Check TTL / hop_limit expiration
        if pkt.hop_limit <= 0:
            pkt.status = PacketStatus.EXPIRED
            self.dropped_packets.append(pkt)
            events.append(
                EventRecord(
                    timestamp=self.current_time,
                    manager=self.name,
                    event_type="PACKET_EXPIRED",
                    entity_id=pkt.packet_id,
                    action="DROP_TTL",
                    previous_state="QUEUED",
                    new_state="EXPIRED",
                    outcome="FAILURE",
                    explanatory_message=f"Packet {pkt.packet_id} dropped: TTL/hop limit expired."
                )
            )
            return events

        route, route_latency = self.find_route(pkt.source_node, pkt.dest_node)
        if not route:
            pkt.status = PacketStatus.DROPPED
            self.dropped_packets.append(pkt)
            events.append(
                EventRecord(
                    timestamp=self.current_time,
                    manager=self.name,
                    event_type="PACKET_DROPPED",
                    entity_id=pkt.packet_id,
                    action="DROP_UNREACHABLE",
                    previous_state="QUEUED",
                    new_state="DROPPED",
                    outcome="FAILURE",
                    explanatory_message=f"Packet {pkt.packet_id} unreachable from {pkt.source_node} to {pkt.dest_node} (no active path)."
                )
            )
            return events

        hops_needed = max(0, len(route) - 1)
        if pkt.hop_limit < hops_needed:
            pkt.hop_limit = 0
            pkt.status = PacketStatus.EXPIRED
            self.dropped_packets.append(pkt)
            events.append(
                EventRecord(
                    timestamp=self.current_time,
                    manager=self.name,
                    event_type="PACKET_EXPIRED",
                    entity_id=pkt.packet_id,
                    action="DROP_TTL",
                    previous_state="QUEUED",
                    new_state="EXPIRED",
                    outcome="FAILURE",
                    explanatory_message=f"Packet {pkt.packet_id} expired: route {' -> '.join(route)} requires {hops_needed} hops."
                )
            )
            return events

        pkt.hop_limit -= hops_needed
        pkt.status = PacketStatus.DELIVERED
        self.delivered_packets.append(pkt)
        self.total_delay += route_latency

        events.append(
            EventRecord(
                timestamp=self.current_time,
                manager=self.name,
                event_type="PACKET_DELIVERED",
                entity_id=pkt.packet_id,
                action="TRANSMIT",
                previous_state="QUEUED",
                new_state="DELIVERED",
                duration_or_cost=route_latency,
                outcome="SUCCESS",
                explanatory_message=f"Packet {pkt.packet_id} delivered via {' -> '.join(route)} (delay: {route_latency} ms, size: {pkt.payload_size}B)."
            )
        )

        return events

    def run(self, stop_condition: Any = None) -> List[EventRecord]:
        all_events: List[EventRecord] = []
        tick = int(self.current_time)
        while self.packet_buffer:
            if stop_condition is not None and callable(stop_condition) and stop_condition(self):
                break
            all_events.extend(self.step(float(tick)))
            tick += 1
        return all_events

    def snapshot(self) -> Dict[str, Any]:
        return {
            "queue_policy": self.queue_policy,
            "buffer_capacity": self.buffer_capacity,
            "topology": {
                "nodes": list(self.nodes),
                "links": [
                    {
                        "edge": link_id,
                        "src": data.get("src", ""),
                        "dst": data.get("dst", ""),
                        "status": data.get("status", "UP"),
                        "bandwidth": data.get("bandwidth", 100),
                        "latency": data.get("latency", 1.0),
                    }
                    for link_id, data in self.links.items()
                ],
            },
            "queued_packets": [
                {
                    "packet_id": p.packet_id,
                    "source": p.source_node,
                    "destination": p.dest_node,
                    "size": p.payload_size,
                    "priority": p.priority,
                    "creation_time": p.creation_time,
                    "ttl": p.hop_limit,
                    "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                }
                for p in self.packet_buffer
            ],
            "delivered_packets": [
                {
                    "packet_id": p.packet_id,
                    "source": p.source_node,
                    "destination": p.dest_node,
                    "size": p.payload_size,
                    "priority": p.priority,
                    "ttl": p.hop_limit,
                    "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                }
                for p in self.delivered_packets
            ],
            "dropped_packets": [
                {
                    "packet_id": p.packet_id,
                    "source": p.source_node,
                    "destination": p.dest_node,
                    "size": p.payload_size,
                    "priority": p.priority,
                    "ttl": p.hop_limit,
                    "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                }
                for p in self.dropped_packets
            ],
            "delivered_count": len(self.delivered_packets),
            "dropped_count": len(self.dropped_packets),
        }

    def metrics(self) -> Dict[str, Any]:
        total = len(self.delivered_packets) + len(self.dropped_packets) + len(self.packet_buffer)
        delivered_count = len(self.delivered_packets)
        avg_latency = (self.total_delay / delivered_count) if delivered_count > 0 else 0.0
        return {
            "delivered_packets": float(delivered_count),
            "dropped_packets": float(len(self.dropped_packets)),
            "queued_packets": float(len(self.packet_buffer)),
            "drop_rate": float((len(self.dropped_packets) / total) * 100.0) if total > 0 else 0.0,
            "delivery_rate": float((delivered_count / total) * 100.0) if total > 0 else 0.0,
            "avg_network_latency": float(avg_latency),
        }

    def validate(self) -> List[str]:
        errors = []
        if len(self.nodes) < 3:
            errors.append("Network topology requires at least 3 nodes.")
        if self.buffer_capacity <= 0:
            errors.append("Buffer capacity must be greater than 0.")
        if self.queue_policy not in ("FIFO", "PRIORITY"):
            errors.append(f"Unsupported queue policy: {self.queue_policy}")
        return errors

    def export(self, export_format: str = "json") -> Any:
        return {
            "metrics": self.metrics(),
            "delivered": [
                {**p.__dict__, "status": p.status.value if hasattr(p.status, "value") else str(p.status)}
                for p in self.delivered_packets
            ],
            "dropped": [
                {**p.__dict__, "status": p.status.value if hasattr(p.status, "value") else str(p.status)}
                for p in self.dropped_packets
            ],
        }