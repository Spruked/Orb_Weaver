from app.analytics.search_console import _summarize_rows


def test_search_console_summary_preserves_verified_metrics_and_opportunities():
    rows = [
        {
            'keys': ['roof inspection kansas city', 'https://example.com/inspection', 'DESKTOP', 'usa'],
            'clicks': 1,
            'impressions': 100,
            'ctr': 0.01,
            'position': 8.0,
        },
        {
            'keys': ['roof inspection kansas city', 'https://example.com/inspection', 'MOBILE', 'usa'],
            'clicks': 2,
            'impressions': 100,
            'ctr': 0.02,
            'position': 10.0,
        },
    ]
    result = _summarize_rows(rows)
    assert result['totals']['clicks'] == 3.0
    assert result['totals']['impressions'] == 200.0
    assert result['totals']['ctr'] == 0.015
    assert result['totals']['average_position'] == 9.0
    assert result['ranking_opportunities']
    assert result['low_ctr_opportunities']
