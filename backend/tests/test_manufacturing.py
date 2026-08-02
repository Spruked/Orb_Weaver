from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.manufacturing import dock_station_builder
from app.manufacturing.dock_station_builder import build_customer_dock_station, validate_build_ids
from app.manufacturing.validator import package_tree_hash, validate_required_paths


REQUIRED_PATHS = [
    {"path": "dock-station/app/backend/app/main.py", "type": "file"},
    {"path": "dock-station/app/frontend/package.json", "type": "file"},
    {"path": "dock-station/app/orb/template/runtime", "type": "directory"},
]


def _write_template_manifest(template_root: Path, required_paths: list[dict[str, str]] | None = None) -> None:
    payload = {
        "schema": "orb_weaver.dock_station_master_template.v1",
        "template_id": "dock_station_master",
        "template_version": "test",
        "source": {
            "name": "Orb Dock Station v2.1",
            "repository": "https://github.com/Spruked/Orb_Dock_Station_v2.1.git",
            "commit": "810f0d29dedae2439c9ed247a8400507cfad6e40",
        },
        "required_paths": required_paths or REQUIRED_PATHS,
    }
    template_root.mkdir(parents=True, exist_ok=True)
    (template_root / "manifest.template.json").write_text(json.dumps(payload), encoding="utf-8")


def _make_template(tmp_path: Path, required_paths: list[dict[str, str]] | None = None) -> Path:
    template_root = tmp_path / "template"
    _write_template_manifest(template_root, required_paths)
    for requirement in required_paths or REQUIRED_PATHS:
        target = template_root / requirement["path"]
        if requirement["type"] == "directory":
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"{requirement['path']}\n", encoding="utf-8")
    return template_root


def _json_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _json_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _json_strings(child)


@pytest.mark.parametrize(
    ("customer_id", "deployment_id"),
    [
        ("../customer", "deployment"),
        ("customer/name", "deployment"),
        ("customer\\name", "deployment"),
        ("con", "deployment"),
        ("customer", "lpt1"),
        ("customer.", "deployment"),
        ("customer..name", "deployment"),
        ("Customer", "deployment"),
        ("cafe\u0301", "deployment"),
        ("café", "deployment"),
    ],
)
def test_rejects_unsafe_colliding_reserved_and_unicode_ids(customer_id: str, deployment_id: str) -> None:
    with pytest.raises(ValueError):
        validate_build_ids(customer_id, deployment_id)


def test_validate_required_paths_rejects_traversal_and_absolute_paths(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    result = validate_required_paths(
        root,
        [
            {"path": "../outside", "type": "file"},
            {"path": "/tmp/outside", "type": "file"},
        ],
    )
    assert result["passed"] is False
    assert "../outside" in result["unsafe_paths"]
    assert "/tmp/outside" in result["unsafe_paths"]


def test_validate_required_paths_rejects_symlink(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = tmp_path / "outside.txt"
    target.write_text("outside\n", encoding="utf-8")
    link = root / "link.txt"
    try:
        os.symlink(target, link)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    result = validate_required_paths(root, [{"path": "link.txt", "type": "file"}])
    assert result["passed"] is False
    assert "link.txt" in result["symlinks"]


def test_validate_required_paths_rejects_forbidden_development_folders(tmp_path: Path) -> None:
    root = tmp_path / "root"
    (root / "app" / "node_modules").mkdir(parents=True)
    result = validate_required_paths(root, [{"path": "app", "type": "directory"}])
    assert result["passed"] is False
    assert "app/node_modules" in result["forbidden_payloads"]


def test_customer_manifest_uses_package_relative_paths_and_no_stale_absolute_paths(tmp_path: Path) -> None:
    template_root = _make_template(tmp_path)
    builds_root = tmp_path / "builds"
    result = build_customer_dock_station(
        customer_id="test-customer",
        deployment_id="test-deployment",
        template_root=template_root,
        builds_root=builds_root,
    )
    manifest_path = Path(result["deployment_manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result["status"] == "created"
    assert manifest["paths"] == {
        "dock_station": ".",
        "dock_station_app": "app",
        "orb_template": "app/orb/template",
        "deployment_manifest": "deployment/manifest.json",
        "verification_report": "reports/verification-report.json",
    }
    assert "local_source_path" not in manifest["template"]["source"]
    assert manifest["template"]["source"]["commit"] == "810f0d29dedae2439c9ed247a8400507cfad6e40"
    assert manifest["template"]["tree_hash"] == result["template_tree_hash"]
    assert manifest["manifest_hash"] == result["manifest_hash"]
    assert manifest["manufacturing_pass"] == {
        "manufacturing_structure": True,
        "blank_template": True,
        "delivery_ready": False,
    }
    assert not any(text.startswith("/") or ":\\" in text for text in _json_strings(manifest))

    report = json.loads(Path(result["verification_report"]).read_text(encoding="utf-8"))
    assert report["template_file_hashes"]
    assert report["package_file_hashes"]


def test_package_tree_hash_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    (first / "b").mkdir(parents=True)
    (first / "a.txt").write_text("a\n", encoding="utf-8")
    (first / "b" / "c.txt").write_text("c\n", encoding="utf-8")
    (second / "b").mkdir(parents=True)
    (second / "b" / "c.txt").write_text("c\n", encoding="utf-8")
    (second / "a.txt").write_text("a\n", encoding="utf-8")

    first_hash = package_tree_hash(first)
    second_hash = package_tree_hash(second)

    assert first_hash["tree_hash"] == second_hash["tree_hash"]
    assert [entry["path"] for entry in first_hash["files"]] == ["a.txt", "b/c.txt"]


def test_destination_collision_is_rejected(tmp_path: Path) -> None:
    template_root = _make_template(tmp_path)
    builds_root = tmp_path / "builds"
    (builds_root / "test-customer" / "test-deployment").mkdir(parents=True)

    with pytest.raises(FileExistsError):
        build_customer_dock_station(
            customer_id="test-customer",
            deployment_id="test-deployment",
            template_root=template_root,
            builds_root=builds_root,
        )


def test_failed_partial_build_cleans_staging_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    template_root = _make_template(tmp_path)
    builds_root = tmp_path / "builds"

    def fail_write_json(path: Path, payload: dict) -> None:
        if path.name == "manifest.json":
            raise RuntimeError("forced manifest write failure")
        dock_station_builder.write_json(path, payload)

    monkeypatch.setattr(dock_station_builder, "write_json", fail_write_json)

    with pytest.raises(RuntimeError):
        build_customer_dock_station(
            customer_id="test-customer",
            deployment_id="test-deployment",
            template_root=template_root,
            builds_root=builds_root,
        )

    assert not (builds_root / "test-customer" / "test-deployment").exists()
    staging_root = builds_root / ".staging"
    assert not staging_root.exists() or not any(staging_root.iterdir())
