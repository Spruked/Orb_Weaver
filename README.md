# Orb Weaver - Website ORB Intelligence Engine

A local-first website intelligence platform featuring real-time crawling, ORB-readable semantic scoring, authority flow analysis, competitor gap detection, historical tracking, and Google Analytics 4 integration.

## Features

### Website ORB Crawler Engine
- **Async Web Crawling**: Crawl up to 5,000 pages with configurable depth and delay
- **On-Page SEO Analysis**: Title tags, meta descriptions, H1-H6 structure, canonical URLs
- **Technical SEO**: SSL detection, robots.txt analysis, sitemap.xml parsing, schema markup extraction
- **Content Analysis**: Word count, duplicate content detection, image alt text analysis
- **Performance Metrics**: Page load times, redirect chains, mobile viewport detection
- **Link Analysis**: Internal/external link counts, broken link detection

### SEO Audit Engine
- **8 Category Scores**: Overall, SEO, Performance, Accessibility, Content, Technical, Mobile, Security
- **3 Severity Levels**: Critical (fix immediately), Warnings (should fix), Opportunities (improve rankings)
- **Impact Scoring**: Each issue rated 1-100 for prioritization
- **Actionable Recommendations**: Specific fixes with time estimates
- **Affected URL Tracking**: See exactly which pages have each issue

### Google Analytics 4 Integration
- **Traffic Overview**: Sessions, users, pageviews, bounce rate, engagement rate
- **Top Pages**: Most visited pages with engagement metrics
- **Search Queries**: What users are searching to find your site
- **Device Breakdown**: Mobile vs desktop vs tablet performance
- **Geographic Data**: Country-level traffic analysis
- **Conversion Tracking**: Event-based conversion monitoring

### Dashboard
- **Real-time Score Circles**: Visual score indicators with color coding
- **Issue Cards**: Expandable cards with severity, impact, and recommendations
- **Progress Tracking**: Crawl progress bars with live updates
- **Data Visualization**: Charts for traffic trends, device breakdown, geographic data
- **Export**: PDF reports and CSV data exports

## Architecture

```
Orb_Weaver/
├── backend/
│   ├── app/
│   │   ├── crawler/          # Async website ORB crawler engine
│   │   ├── audit/            # SEO scoring and issue detection
│   │   ├── analytics/        # GA4 API integration
│   │   ├── models/           # SQLAlchemy database models
│   │   ├── core/             # Configuration and settings
│   │   └── api/              # FastAPI endpoints
│   ├── main.py               # FastAPI application entry
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            # Dashboard, Projects, Audit, GA4
│   │   ├── services/         # API client
│   │   └── hooks/            # Custom React hooks
│   ├── public/
│   └── package.json
└── scripts/                  # Deployment scripts
```

## Quick Start

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your GA4 credentials

# Initialize database
python -c "from app.models.database import init_db, get_engine; init_db(get_engine('sqlite:///./data/orb_weaver.db'))"

# Run the server
uvicorn main:app --reload --host 127.0.0.1 --port 16500
```

### Frontend Setup

```bash
cd frontend
npm install
npm run build
npx serve -s build -l 16510
```

The frontend will be available at `http://localhost:16510` and the backend API at `http://localhost:16500`.

## Google Analytics 4 Setup

1. Create a service account in Google Cloud Console
2. Enable the Google Analytics Data API
3. Download the JSON credentials file
4. Add the service account email to your GA4 property with "Read & Analyze" permissions
5. Set `GA4_CREDENTIALS_PATH` in your `.env` file

## API Endpoints

### Projects
- `POST /api/projects` - Create new project
- `GET /api/projects` - List all projects
- `GET /api/projects/{id}` - Get project details

### Crawling
- `POST /api/projects/{id}/crawl` - Start crawl job
- `GET /api/crawl-jobs/{id}` - Get crawl status
- `GET /api/crawl-jobs/{id}/pages` - Get crawled pages

### Auditing
- `POST /api/crawl-jobs/{id}/audit` - Run SEO audit
- `GET /api/audit-reports/{id}` - Get audit report

### GA4 Analytics
- `POST /api/ga4/connect` - Test GA4 connection
- `GET /api/ga4/{property_id}/overview` - Full traffic report
- `GET /api/ga4/{property_id}/top-pages` - Top pages
- `GET /api/ga4/{property_id}/search-queries` - Search queries
- `GET /api/ga4/{property_id}/devices` - Device breakdown

### Combined
- `GET /api/combined/{project_id}/dashboard` - Unified dashboard data

## Configuration

All settings are managed via environment variables or `.env` file:

```env
# App
DEBUG=false
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://user:pass@localhost/orb_weaver
REDIS_URL=redis://localhost:6379/0

# Google Analytics
GA4_PROPERTY_ID=123456789
GA4_CREDENTIALS_PATH=./credentials.json

# Crawler
CRAWL_MAX_PAGES=1000
CRAWL_DELAY=1.0
CRAWL_TIMEOUT=30
CRAWL_MAX_DEPTH=5

# Audit Thresholds
MIN_PAGE_SPEED_SCORE=50
MAX_TITLE_LENGTH=60
MAX_META_DESC_LENGTH=160
MIN_CONTENT_WORDS=300
```

## Scoring System

| Score | Rating | Action |
|-------|--------|--------|
| 90-100 | Excellent | Maintain current performance |
| 80-89 | Good | Minor improvements needed |
| 60-79 | Fair | Significant issues to address |
| 40-59 | Poor | Major issues requiring attention |
| 0-39 | Critical | Immediate action required |

## License

Proprietary. All rights reserved.

## Credits

Built with FastAPI, React, and the Google Analytics Data API.
