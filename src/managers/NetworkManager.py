from typing import Dict, List, Any, Optional
from src.core.base_manager import BaseManager
from src.core.events import EventRecord
from src.core.models import Packet


class NetworkManager(BaseManager):
    """
    Simulates node-to-node topology, link capacities, packet queueing/routing,
    TTL hop limits, and network transmission metrics.
    """

    def __init__(self):
        super().__init__("Network")
        self.nodes: List[str] = ["NodeA", "NodeB", "NodeC"]
        self.links: Dict[str, Dict[str, Any]] = {
            "NodeA-NodeB": {"bandwidth": 100, "latency": 1.0, "status": "UP"},
            "NodeB-NodeC": {"bandwidth": 50, "latency": 2.0, "status": "UP"},
        }
        self.packet_buffer: List[Packet] = []
        self.delivered_packets: List[Packet] = []
        self.dropped_packets: List[Packet] = []
        self.queue_policy: str = "FIFO"  # FIFO, PRIORITY

    def configure(self, config: Dict[str, Any]) -> None:
        self.queue_policy = config.get("queue_policy", "FIFO")
        self.is_configured = True

    def load(self, input_data: List[Packet]) -> None:
        self.packet_buffer.extend(input_data)

    def reset(self) -> None:
        self.packet_buffer.clear()
        self.delivered_packets.clear()
        self.dropped_packets.clear()

    def step(self, current_time: float) -> List[EventRecord]:
        events: List[EventRecord] = []

        if not self.packet_buffer:
            return events

        # Sort buffer if using priority policy
        if self.queue_policy == "PRIORITY":
            self.packet_buffer.sort(key=lambda p: p.hop_limit, reverse=True)

        pkt = self.packet_buffer.pop(0)

        # TTL Validation check
        if pkt.hop_limit <= 0:
            pkt.status = "DROPPED"
            self.dropped_packets.append(pkt)
            events.append(
                EventRecord(
                    timestamp=current_time,
                    manager=self.name,
                    event_type="PACKET_DROPPED",
                    entity_id=pkt.packet_id,
                    action="DROP",
                    previous_state="QUEUED",
                    new_state="DROPPED",
                    outcome="FAILURE",
                    explanatory_message=f"Packet {pkt.packet_id} dropped: TTL expired."
                )
            )
            return events

        # Transmission step
        pkt.hop_limit -= 1
        pkt.status = "DELIVERED"
        self.delivered_packets.append(pkt)

        events.append(
            EventRecord(
                timestamp=current_time,
                manager=self.name,
                event_type="PACKET_DELIVERED",
                entity_id=pkt.packet_id,
                action="TRANSMIT",
                previous_state="QUEUED",
                new_state="DELIVERED",
                outcome="SUCCESS",
                explanatory_message=f"Packet {pkt.packet_id} delivered from {pkt.source_node} to {pkt.dest_node}."
            )
        )

        return events

    def run(self, stop_condition: Any = None) -> List[EventRecord]:
        all_events = []
        while self.packet_buffer:
            all_events.extend(self.step(len(all_events)))
        return all_events

    def snapshot(self) -> Dict[str, Any]:
        """UI Snapshot format for network graph components and active links."""
        return {
            "topology": {
                "nodes": self.nodes,
                "links": [
                    {"edge": link_id, "status": data["status"], "bandwidth": data["bandwidth"]}
                    for link_id, data in self.links.items()
                ]
            },
            "queued_packets": [p.packet_id for p in self.packet_buffer],
            "delivered_count": len(self.delivered_packets),
            "dropped_count": len(self.dropped_packets)
        }

    def metrics(self) -> Dict[str, Any]:
        """UI metrics format for network latency and drop-rate charts."""
        total = len(self.delivered_packets) + len(self.dropped_packets) + len(self.packet_buffer)
        return {
            "delivered_packets": len(self.delivered_packets),
            "dropped_packets": len(self.dropped_packets),
            "queued_packets": len(self.packet_buffer),
            "drop_rate": len(self.dropped_packets) / max(1, total),
            "delivery_rate": len(self.delivered_packets) / max(1, total)
        }

    def validate(self) -> List[str]:
        return []

    def export(self, export_format: str = "json") -> Any:
        return {
            "metrics": self.metrics(),
            "delivered": [p.__dict__ for p in self.delivered_packets],
            "dropped": [p.__dict__ for p in self.dropped_packets]
        }