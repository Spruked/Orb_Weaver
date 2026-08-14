from bs4 import BeautifulSoup

from app.orb.pointer_plot import extract_pointer_plot_records


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
