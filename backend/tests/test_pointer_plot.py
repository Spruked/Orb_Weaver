from bs4 import BeautifulSoup

from app.orb.pointer_plot import extract_pointer_plot_records, mark_route_locator_conflicts, pointer_map_diagnostics


def test_extracts_same_route_cta_links_outside_navigation():
    soup = BeautifulSoup(
        """
        <main>
          <h1>Build with Orb Weaver</h1>
          <a class="cta-primary" href="/founding-beta">Join the Founding Beta</a>
        </main>
        """,
        "lxml",
    )
    records = extract_pointer_plot_records("https://example.test/", soup)
    cta = next(record for record in records if record["meaning"] == "button: Join the Founding Beta")
    assert cta["semantic_locator"] == 'a[href="/founding-beta"]'
    assert cta["allowed_actions"] == ["point", "point_and_confirm_navigate"]
    assert cta["runtime_policy"]["may_point"] is False
    assert cta["pointer_class"] == "live_guidance"


def test_navigation_anchor_is_not_duplicated_as_a_cta():
    soup = BeautifulSoup('<nav><a href="/beta">Beta</a></nav>', "lxml")
    records = extract_pointer_plot_records("https://example.test/", soup)
    matching = [record for record in records if record["meaning"].endswith("Beta")]
    assert len(matching) == 1
    assert matching[0]["target_type"] == "nav"


def test_default_extraction_does_not_truncate_component_rich_pages_at_eighty_targets():
    soup = BeautifulSoup(
        "<main>" + "".join(
            f'<button id="control-{index}">Run component action {index}</button>'
            for index in range(120)
        ) + "</main>",
        "lxml",
    )

    records = extract_pointer_plot_records("https://example.test/components", soup)

    assert len(records) == 120


def test_reference_content_is_not_live_guidance():
    soup = BeautifulSoup(
        """
        <main>
          <h1>What Web Weaver Does</h1>
          <p>Web Weaver builds a complete intelligent website from the beginning with native visitor guidance.</p>
        </main>
        """,
        "lxml",
    )
    records = extract_pointer_plot_records("https://example.test/web-weave", soup)
    assert records
    assert {record["pointer_class"] for record in records} == {"semantic_reference"}
    assert all(record["runtime_policy"]["may_point"] is False for record in records)


def test_duplicate_route_locator_conflicts_are_target_specific():
    records = [
        {
            "target_id": "one",
            "page_route": "/",
            "target_type": "button",
            "pointer_class": "live_guidance",
            "semantic_locator": "#duplicate",
            "confidence_class": "STABLE",
            "runtime_policy": {"may_point": True},
        },
        {
            "target_id": "two",
            "page_route": "/",
            "target_type": "button",
            "pointer_class": "live_guidance",
            "semantic_locator": "#duplicate",
            "confidence_class": "STABLE",
            "runtime_policy": {"may_point": True},
        },
    ]
    mark_route_locator_conflicts(records)
    diagnostics = pointer_map_diagnostics(records)
    assert diagnostics["route_locator_conflict_count"] == 1
    assert all(record["finding_subreason"] == "duplicate_route_locator_conflict" for record in records)
    assert all(record["runtime_policy"]["may_point"] is False for record in records)
