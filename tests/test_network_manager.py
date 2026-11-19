from src.core.models import Packet, PacketStatus
from src.managers.NetworkManager import NetworkManager


def make_pkt(
    pid: str,
    src: str = "NodeA",
    dst: str = "NodeC",
    priority: int = 1,
    ttl: int = 5,
    creation_time: float = 0.0,
    size: int = 64,
) -> Packet:
    return Packet(
        packet_id=pid,
        source_node=src,
        dest_node=dst,
        source_process_id="P1",
        payload_size=size,
        hop_limit=ttl,
        priority=priority,
        creation_time=creation_time,
        status=PacketStatus.QUEUED,
    )


def test_topology_initialization_and_validation():
    nm = NetworkManager()
    nm.configure({"queue_policy": "FIFO", "buffer_capacity": 10})
    assert nm.is_configured is True
    assert len(nm.nodes) >= 3
    assert nm.validate() == []


def test_fifo_packet_scheduling_order():
    nm = NetworkManager()
    nm.configure({"queue_policy": "FIFO"})
    nm.load([
        make_pkt("PKT-1", priority=2, creation_time=0.0),
        make_pkt("PKT-2", priority=0, creation_time=0.0),
        make_pkt("PKT-3", priority=1, creation_time=0.0),
    ])

    nm.step(0)
    nm.step(1)
    nm.step(2)

    assert [p.packet_id for p in nm.delivered_packets] == ["PKT-1", "PKT-2", "PKT-3"]


def test_priority_packet_scheduling_order():
    nm = NetworkManager()
    nm.configure({"queue_policy": "PRIORITY"})
    nm.load([
        make_pkt("PKT-1", priority=1, creation_time=0.0),
        make_pkt("PKT-2", priority=0, creation_time=0.0),
        make_pkt("PKT-3", priority=2, creation_time=0.0),
    ])

    nm.step(0)
    nm.step(1)
    nm.step(2)

    assert [p.packet_id for p in nm.delivered_packets] == ["PKT-2", "PKT-1", "PKT-3"]


def test_dijkstra_routing_and_reroute_on_link_failure():
    nm = NetworkManager()
    nm.configure({"queue_policy": "FIFO"})

    route_before, _ = nm.find_route("NodeA", "NodeC")
    assert route_before == ["NodeA", "NodeB", "NodeC"]

    nm.fail_link("NodeA-NodeB")
    route_after, _ = nm.find_route("NodeA", "NodeC")
    assert route_after == ["NodeA", "NodeD", "NodeC"]

    nm.load([make_pkt("PKT-REROUTE", src="NodeA", dst="NodeC", ttl=5)])
    events = nm.step(0)
    assert len(nm.delivered_packets) == 1
    assert nm.delivered_packets[0].status == PacketStatus.DELIVERED
    assert "NodeA -> NodeD -> NodeC" in events[0].explanatory_message

    nm.recover_link("NodeA-NodeB")
    assert nm.links["NodeA-NodeB"]["status"] == "UP"


def test_unreachable_packet_dropped_when_no_active_path():
    nm = NetworkManager()
    nm.fail_link("NodeA-NodeB")
    nm.fail_link("NodeA-NodeD")
    nm.load([make_pkt("PKT-UNREACHABLE", src="NodeA", dst="NodeC", ttl=5)])

    events = nm.step(0)
    assert len(nm.dropped_packets) == 1
    assert nm.dropped_packets[0].status == PacketStatus.DROPPED
    assert events[0].event_type == "PACKET_DROPPED"


def test_ttl_expiration_drops_packet():
    nm = NetworkManager()
    nm.load([make_pkt("PKT-TTL", src="NodeA", dst="NodeC", ttl=0)])

    events = nm.step(0)
    assert len(nm.dropped_packets) == 1
    assert nm.dropped_packets[0].status == PacketStatus.EXPIRED
    assert events[0].event_type == "PACKET_EXPIRED"


def test_buffer_capacity_overflow_and_reset():
    nm = NetworkManager()
    nm.configure({"queue_policy": "FIFO", "buffer_capacity": 2})
    nm.load([
        make_pkt("PKT-1"),
        make_pkt("PKT-2"),
        make_pkt("PKT-3"),
    ])

    assert len(nm.packet_buffer) == 2
    assert len(nm.dropped_packets) == 1
    assert nm.dropped_packets[0].packet_id == "PKT-3"

    metrics = nm.metrics()
    assert metrics["queued_packets"] == 2.0
    assert metrics["dropped_packets"] == 1.0

    nm.reset()
    assert len(nm.packet_buffer) == 0
    assert len(nm.delivered_packets) == 0
    assert len(nm.dropped_packets) == 0