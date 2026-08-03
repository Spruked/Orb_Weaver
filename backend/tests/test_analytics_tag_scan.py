from app.crawler.analytics_tags import analyze_analytics_tags, summarize_analytics_tags


def test_detects_google_analytics_identifiers_and_signals():
    html = """
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-ABC123XYZ"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('consent', 'default', {'analytics_storage': 'granted'});
      gtag('config', 'G-ABC123XYZ');
    </script>
    <script src="https://www.googletagmanager.com/gtm.js?id=GTM-ABCD123"></script>
    """

    result = analyze_analytics_tags(html, "/")

    assert result["ga4_measurement_ids"] == ["G-ABC123XYZ"]
    assert result["gtm_container_ids"] == ["GTM-ABCD123"]
    assert result["data_layer_detected"] is True
    assert result["gtag_config_detected"] is True
    assert result["consent_mode_detected"] is True


def test_summary_flags_route_gaps_and_conflicting_measurement_ids():
    first = analyze_analytics_tags("gtag('config', 'G-ABC123XYZ')", "/")
    second = analyze_analytics_tags("gtag('config', 'G-SECOND123')", "/pricing")
    third = analyze_analytics_tags("<html></html>", "/contact")

    summary = summarize_analytics_tags([first, second, third])
    codes = {issue["code"] for issue in summary["issues"]}

    assert summary["ga4_measurement_ids"] == ["G-ABC123XYZ", "G-SECOND123"]
    assert "multiple_ga4_measurement_ids" in codes
    assert "analytics_missing_on_routes" in codes
