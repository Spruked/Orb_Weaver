from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Dimension,
    Metric,
    FilterExpression,
    Filter,
    FilterExpressionList
)
from google.oauth2 import service_account
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
from app.core.config import settings

class GA4Connector:
    def __init__(self, property_id: str = None, credentials_path: str = None):
        self.property_id = property_id or settings.GA4_PROPERTY_ID
        self.credentials_path = credentials_path or settings.GA4_CREDENTIALS_PATH
        self.client = None
        self._init_client()

    def _init_client(self):
        if self.credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=settings.GA4_SCOPES
            )
            self.client = BetaAnalyticsDataClient(credentials=credentials)
        else:
            # Use default credentials (for local development with gcloud auth)
            self.client = BetaAnalyticsDataClient()

    def _format_property_id(self) -> str:
        if not self.property_id.startswith('properties/'):
            return f'properties/{self.property_id}'
        return self.property_id

    def get_traffic_overview(
        self, 
        start_date: str = '30daysAgo', 
        end_date: str = 'today'
    ) -> Dict:
        request = RunReportRequest(
            property=self._format_property_id(),
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[
                Dimension(name='date'),
                Dimension(name='sessionDefaultChannelGroup')
            ],
            metrics=[
                Metric(name='sessions'),
                Metric(name='users'),
                Metric(name='newUsers'),
                Metric(name='bounceRate'),
                Metric(name='averageSessionDuration'),
                Metric(name='screenPageViews')
            ]
        )

        response = self.client.run_report(request)

        data = []
        for row in response.rows:
            data.append({
                'date': row.dimension_values[0].value,
                'channel': row.dimension_values[1].value,
                'sessions': int(row.metric_values[0].value),
                'users': int(row.metric_values[1].value),
                'new_users': int(row.metric_values[2].value),
                'bounce_rate': float(row.metric_values[3].value),
                'avg_session_duration': float(row.metric_values[4].value),
                'pageviews': int(row.metric_values[5].value)
            })

        return {
            'data': data,
            'totals': {
                'sessions': sum(d['sessions'] for d in data),
                'users': sum(d['users'] for d in data),
                'pageviews': sum(d['pageviews'] for d in data)
            }
        }

    def get_top_pages(
        self, 
        start_date: str = '30daysAgo', 
        end_date: str = 'today',
        limit: int = 50
    ) -> List[Dict]:
        request = RunReportRequest(
            property=self._format_property_id(),
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[
                Dimension(name='pagePath'),
                Dimension(name='pageTitle')
            ],
            metrics=[
                Metric(name='screenPageViews'),
                Metric(name='sessions'),
                Metric(name='users'),
                Metric(name='bounceRate'),
                Metric(name='averageSessionDuration'),
                Metric(name='engagementRate')
            ],
            order_bys=[{
                'metric': {'metric_name': 'screenPageViews'},
                'desc': True
            }],
            limit=limit
        )

        response = self.client.run_report(request)

        pages = []
        for row in response.rows:
            pages.append({
                'path': row.dimension_values[0].value,
                'title': row.dimension_values[1].value,
                'pageviews': int(row.metric_values[0].value),
                'sessions': int(row.metric_values[1].value),
                'users': int(row.metric_values[2].value),
                'bounce_rate': float(row.metric_values[3].value),
                'avg_session_duration': float(row.metric_values[4].value),
                'engagement_rate': float(row.metric_values[5].value)
            })

        return pages

    def get_search_queries(
        self,
        start_date: str = '30daysAgo',
        end_date: str = 'today',
        limit: int = 100
    ) -> List[Dict]:
        request = RunReportRequest(
            property=self._format_property_id(),
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[
                Dimension(name='searchTerm')
            ],
            metrics=[
                Metric(name='sessions'),
                Metric(name='screenPageViews'),
                Metric(name='bounceRate')
            ],
            order_bys=[{
                'metric': {'metric_name': 'sessions'},
                'desc': True
            }],
            limit=limit
        )

        response = self.client.run_report(request)

        queries = []
        for row in response.rows:
            queries.append({
                'query': row.dimension_values[0].value,
                'sessions': int(row.metric_values[0].value),
                'pageviews': int(row.metric_values[1].value),
                'bounce_rate': float(row.metric_values[2].value)
            })

        return queries

    def get_device_breakdown(
        self,
        start_date: str = '30daysAgo',
        end_date: str = 'today'
    ) -> List[Dict]:
        request = RunReportRequest(
            property=self._format_property_id(),
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[
                Dimension(name='deviceCategory')
            ],
            metrics=[
                Metric(name='sessions'),
                Metric(name='users'),
                Metric(name='bounceRate'),
                Metric(name='averageSessionDuration')
            ]
        )

        response = self.client.run_report(request)

        devices = []
        for row in response.rows:
            devices.append({
                'device': row.dimension_values[0].value,
                'sessions': int(row.metric_values[0].value),
                'users': int(row.metric_values[1].value),
                'bounce_rate': float(row.metric_values[2].value),
                'avg_session_duration': float(row.metric_values[3].value)
            })

        return devices

    def get_country_breakdown(
        self,
        start_date: str = '30daysAgo',
        end_date: str = 'today',
        limit: int = 20
    ) -> List[Dict]:
        request = RunReportRequest(
            property=self._format_property_id(),
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[
                Dimension(name='country')
            ],
            metrics=[
                Metric(name='sessions'),
                Metric(name='users'),
                Metric(name='screenPageViews')
            ],
            order_bys=[{
                'metric': {'metric_name': 'sessions'},
                'desc': True
            }],
            limit=limit
        )

        response = self.client.run_report(request)

        countries = []
        for row in response.rows:
            countries.append({
                'country': row.dimension_values[0].value,
                'sessions': int(row.metric_values[0].value),
                'users': int(row.metric_values[1].value),
                'pageviews': int(row.metric_values[2].value)
            })

        return countries

    def get_conversion_events(
        self,
        start_date: str = '30daysAgo',
        end_date: str = 'today'
    ) -> List[Dict]:
        request = RunReportRequest(
            property=self._format_property_id(),
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[
                Dimension(name='eventName')
            ],
            metrics=[
                Metric(name='eventCount'),
                Metric(name='eventCountPerUser')
            ],
            dimension_filter=FilterExpression(
                filter=Filter(
                    field_name='eventName',
                    string_filter=Filter.StringFilter(
                        match_type=Filter.StringFilter.MatchType.PARTIAL_REGEXP,
                        value='conversion|purchase|lead|submit|sign'
                    )
                )
            )
        )

        response = self.client.run_report(request)

        events = []
        for row in response.rows:
            events.append({
                'event_name': row.dimension_values[0].value,
                'count': int(row.metric_values[0].value),
                'per_user': float(row.metric_values[1].value)
            })

        return events

    def get_full_report(self, days: int = 30) -> Dict:
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')

        return {
            'traffic_overview': self.get_traffic_overview(start_date, end_date),
            'top_pages': self.get_top_pages(start_date, end_date),
            'search_queries': self.get_search_queries(start_date, end_date),
            'device_breakdown': self.get_device_breakdown(start_date, end_date),
            'country_breakdown': self.get_country_breakdown(start_date, end_date),
            'conversion_events': self.get_conversion_events(start_date, end_date)
        }

    def get_page_performance_vs_crawl(
        self, 
        crawled_urls: List[str],
        start_date: str = '30daysAgo',
        end_date: str = 'today'
    ) -> List[Dict]:
        request = RunReportRequest(
            property=self._format_property_id(),
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[
                Dimension(name='pagePath')
            ],
            metrics=[
                Metric(name='screenPageViews'),
                Metric(name='sessions'),
                Metric(name='bounceRate'),
                Metric(name='averageSessionDuration'),
                Metric(name='engagementRate')
            ]
        )

        response = self.client.run_report(request)

        ga_data = {}
        for row in response.rows:
            path = row.dimension_values[0].value
            ga_data[path] = {
                'pageviews': int(row.metric_values[0].value),
                'sessions': int(row.metric_values[1].value),
                'bounce_rate': float(row.metric_values[2].value),
                'avg_session_duration': float(row.metric_values[3].value),
                'engagement_rate': float(row.metric_values[4].value)
            }

        # Merge with crawl data
        merged = []
        for url in crawled_urls:
            parsed = __import__('urllib.parse').parse.urlparse(url)
            path = parsed.path or '/'

            merged.append({
                'url': url,
                'path': path,
                'ga_data': ga_data.get(path, {
                    'pageviews': 0,
                    'sessions': 0,
                    'bounce_rate': 0,
                    'avg_session_duration': 0,
                    'engagement_rate': 0
                })
            })

        return merged
