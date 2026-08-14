from app.audit.engine import SEOIssue


def test_audit_issue_preserves_every_affected_url():
    urls = [f"https://example.test/page-{index}" for index in range(37)]
    issue = SEOIssue(
        severity="warning",
        category="content",
        title="Complete evidence",
        description="All affected URLs remain in the persisted report.",
        affected_urls=urls,
    )

    assert issue.to_dict()["affected_urls"] == urls
