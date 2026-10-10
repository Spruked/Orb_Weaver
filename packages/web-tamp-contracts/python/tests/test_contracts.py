import json
from datetime import datetime
from pathlib import Path

import pytest

from web_tamp_contracts import Authorization, ExecutionReceipt, Proposal, Task, WorldEdge, WorldModel, WorldNode


ROOT = Path(__file__).resolve().parents[2]


def test_website_task_fixture_is_python_validated():
    fixture = json.loads((ROOT / "fixtures" / "website-crawl-task.json").read_text())
    task = Task.model_validate(fixture)
    assert task.domain == "website"
    normalized = dict(fixture)
    normalized.pop("parent_task_id", None)
    normalized["success_criteria"] = [{**normalized["success_criteria"][0], "evidence_ids": []}]
    assert task.model_dump(mode="json", exclude_none=True) == normalized


def test_proposal_and_authorization_are_distinct_contracts():
    proposal = Proposal(
        proposal_id="proposal:1", task_id="task:1", primitive_id="primitive:1", sequence=0,
        rationale="coverage", planner_version="planner/v1", world_model_version="world/v1",
        proposed_at=datetime.fromisoformat("2026-10-10T12:00:00+00:00"),
    )
    authorization = Authorization(
        authorization_id="authorization:1", proposal_id=proposal.proposal_id, approval_id="approval:1",
        scopes=["website.read_public"], issued_by="stage-governor",
        issued_at=datetime.fromisoformat("2026-10-10T12:00:01+00:00"),
        expires_at=datetime.fromisoformat("2026-10-10T12:05:01+00:00"), policy_decision="allowed",
    )
    assert "approval_id" not in proposal.model_dump()
    assert authorization.policy_decision == "allowed"


def test_world_model_rejects_edges_to_unknown_nodes():
    node = WorldNode(node_id="route:/", node_type="route", layers=["structural"], created_at=datetime.now(), updated_at=datetime.now())
    edge = WorldEdge(edge_id="edge:1", relation="contains", from_node_id=node.node_id, to_node_id="missing", layers=["structural"])
    with pytest.raises(ValueError, match="reference nodes"):
        WorldModel(world_model_id="world:1", version="v1", domain="website", nodes=[node], edges=[edge], updated_at=datetime.now())


def test_execution_receipt_serializes_failure_and_trace():
    receipt = ExecutionReceipt(
        receipt_id="receipt:1", task_id="task:1", primitive_id="primitive:1", proposal_id="proposal:1",
        started_at=datetime.now(), completed_at=datetime.now(), outcome="failed", trace_id="trace:1",
        failure={"code": "target_lost", "message": "Target was not found", "retryable": True},
    )
    payload = receipt.model_dump(mode="json")
    assert payload["schema"] == "web_tamp.execution_receipt.v1"
    assert payload["failure"]["retryable"] is True
