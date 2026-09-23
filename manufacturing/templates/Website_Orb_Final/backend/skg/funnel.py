"""Site-derived Nine-of-Clubs topic choices along approved goal paths.

Choices select discussion topics, never silently execute either destination.
No fixed question count, factory sales copy, guessed witnesses or fake path.
"""
from __future__ import annotations


def compile_funnels(graph: dict) -> dict:
    nodes, routes = graph["nodes"], graph["route_index"]
    outgoing = {}
    for edge in graph["edges"]:
        if edge["kind"] == "links_to":
            outgoing.setdefault(edge["source"], []).append(edge)
    funnels = {}
    for goal in graph["goals"]:
        for entry, context in routes.items():
            journey = context["journeys"][goal["goal_id"]]
            cuts, hops, current = [], [], entry
            while routes[current]["journeys"][goal["goal_id"]]["status"] == "reachable":
                next_route = routes[current]["journeys"][goal["goal_id"]]["next_route"]
                next_node = routes[next_route]["node_id"]
                edges = sorted(outgoing.get(routes[current]["node_id"], []), key=lambda e: e["id"])
                toward = next((edge for edge in edges if edge["target"] == next_node), None)
                alternative = next((edge for edge in edges if edge["target"] != next_node
                                    and nodes[edge["target"]]["label"] != nodes[next_node]["label"]), None)
                if toward and alternative:
                    cuts.append({"from_route": current, "next_route": next_route,
                                 "dimension": "linked_site_topics",
                                 "a": nodes[next_node]["label"], "b": nodes[alternative["target"]]["label"],
                                 "witness_a": toward["witness_id"], "witness_b": alternative["witness_id"],
                                 "elimination_rule": "Either topic choice retains the visitor's selected goal; navigation needs confirmation."})
                hops.append(next_route)
                current = next_route
                if len(hops) > len(routes):
                    raise ValueError("Cycle in precompiled goal path")
            funnels[goal["goal_id"] + ":" + entry] = {
                "goal_id": goal["goal_id"], "entry": entry, "destination": goal["route"],
                "status": journey["status"], "route_path": hops, "cuts": cuts, "steps": len(cuts)}
    return {"schema": "website_orb.elimination_graph.v1", "site_id": graph["site_id"],
            "domain": graph["domain"], "source_scan_id": graph["source_scan_id"],
            "source_fingerprint": graph["source_fingerprint"], "authority": "advisory_only",
            "status": "ready" if graph["goals"] else "awaiting_owner_goal", "funnels": funnels}


def present_step(funnel: dict, answers: list[str]) -> dict:
    if any(answer not in {"a", "b"} for answer in answers) or len(answers) > len(funnel["cuts"]):
        raise ValueError("Invalid topic-choice history")
    if funnel["status"] == "unreachable":
        return {"type": "unreachable", "navigation_authorized": False}
    if len(answers) == len(funnel["cuts"]):
        return {"type": "destination_proposal", "route": funnel["destination"],
                "requires_confirmation": True, "navigation_authorized": False}
    cut = funnel["cuts"][len(answers)]
    return {"type": "choice", "step": len(answers), "total": len(funnel["cuts"]),
            "question": f"Would you like to hear about {cut['a']} or {cut['b']} as we work toward your selected goal?",
            "options": [{"value": side, "label": cut[side], "witness_id": cut['witness_' + side]} for side in ("a", "b")],
            "navigation_authorized": False}
