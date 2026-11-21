"""Network topology imagery (spec 5.1): nodes, links, link status/cost, the
selected route, and link utilization.

Utilization comes from the delivered-packet events, whose message names the
route and packet size ("delivered via NodeA -> NodeB -> NodeC (delay: 3.0 ms, size: 128B)").
"""

import re
from typing import Any, Dict, List

import altair as alt
import pandas as pd

DELIVERED = re.compile(r"via (.+?) \(.*size: (\d+)B\)")


def route_edges(route: List[str]) -> set:
    """The links a route uses, in both directions so A-B and B-A both match."""
    pairs = set(zip(route, route[1:]))
    return pairs | {(b, a) for a, b in pairs}


def topology_dot(nodes: List[str], links: List[Dict[str, Any]], route: List[str]) -> str:
    """Graphviz DOT text: route links are thick, down links are dashed and labeled DOWN."""
    used = route_edges(route)
    lines = ["graph network {", "  rankdir=LR;", '  node [shape=circle, style=filled, fillcolor="#e8f0fb"];']
    for node in nodes:
        fill = "#2a78d6" if node in route else "#e8f0fb"
        font = "white" if node in route else "black"
        lines.append(f'  "{node}" [fillcolor="{fill}", fontcolor="{font}"];')
    for link in links:
        label = f"{link['latency']:g} ms · {link['bandwidth']:g} B/ms"
        style = 'style=dashed, color="#d03b3b"' if link["status"] != "UP" else 'color="#555555"'
        if link["status"] != "UP":
            label += " · DOWN"
        if (link["src"], link["dst"]) in used:
            style = 'color="#2a78d6", penwidth=4'
            label += " · route"
        lines.append(f'  "{link["src"]}" -- "{link["dst"]}" [label="{label}", {style}];')
    lines.append("}")
    return "\n".join(lines)


def link_usage(events: list, links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Bytes and packets carried by each link, from the delivered-packet events."""
    usage = {link["edge"]: {"link": link["edge"], "packets": 0, "bytes": 0} for link in links}
    for event in events:
        if event.manager != "Network" or event.event_type != "PACKET_DELIVERED":
            continue
        match = DELIVERED.search(event.explanatory_message or "")
        if not match:
            continue
        route, size = [n.strip() for n in match.group(1).split("->")], int(match.group(2))
        used = route_edges(route)
        for link in links:
            if (link["src"], link["dst"]) in used:
                usage[link["edge"]]["packets"] += 1
                usage[link["edge"]]["bytes"] += size
    return list(usage.values())


def usage_chart(usage: List[Dict[str, Any]]) -> alt.Chart:
    return alt.Chart(pd.DataFrame(usage)).mark_bar(color="#2a78d6").encode(
        x=alt.X("bytes:Q", title="Data carried (bytes)"),
        y=alt.Y("link:N", title="Link", sort="-x"),
        tooltip=["link", "packets", "bytes"],
    ).properties(title="Link utilization: bytes carried by each link", height=40 + 28 * len(usage))
