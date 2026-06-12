# ORB Weaver Intelligence Graph Spec v0.1

## 1. High-Level Scan Pipeline

ORB Weaver's intelligence spine is:

```text
Crawl -> Normalize -> Analyze -> Graph -> Diff -> Store -> Expose to ORB
```

The crawler should not only collect pages. It should normalize each page into stable intelligence objects, analyze those objects, build a site graph, compare the new graph to prior crawls, store durable client-local outputs, and expose selected context to the Website ORB.

## 2. PageDocument Schema

`PageDocument` is the normalized crawl object. All later intelligence should be built from this object.

```json
{
  "schema": "orb_weaver.page_document.v1",
  "url": "",
  "canonical_url": "",
  "status_code": 200,
  "content_hash": "",
  "title": "",
  "meta_description": "",
  "h1": "",
  "visible_text_blocks": [],
  "links": {
    "internal": [],
    "external": []
  },
  "media": {
    "images": [],
    "videos": [],
    "files": []
  },
  "structured_data": [],
  "http": {
    "headers": {},
    "robots": "",
    "last_modified": ""
  },
  "crawl": {
    "depth": 0,
    "discovered_from": "",
    "fetched_at": ""
  }
}
```

## 3. PageAnalysis Schema

`PageAnalysis` is the bridge between crawler data and Website ORB usage.

```json
{
  "schema": "orb_weaver.page_analysis.v1",
  "url": "",
  "page_purpose": {
    "primary": "informational",
    "secondary": []
  },
  "semantic": {
    "entities": [],
    "topics": [],
    "intent": "",
    "orb_semantic_score": 0
  },
  "conversion": {
    "ctas": [],
    "forms": [],
    "conversion_capable": false
  },
  "voice": {
    "tone": [],
    "sentiment": 0,
    "brand_match": "unknown"
  },
  "issues": [],
  "orb_usage": {
    "can_answer_from_this_page": true,
    "best_for_questions_about": [],
    "unsafe_claims": []
  }
}
```

## 4. SiteGraph Schema

`SiteGraph` represents the website as a connected intelligence object.

```json
{
  "schema": "orb_weaver.site_graph.v1",
  "project_id": "",
  "domain": "",
  "generated_at": "",
  "nodes": [
    {
      "url": "",
      "title": "",
      "page_purpose": "",
      "topics": [],
      "entities": [],
      "status_code": 200,
      "depth": 0,
      "content_hash": ""
    }
  ],
  "edges": [
    {
      "source_url": "",
      "target_url": "",
      "relationship": "internal_link",
      "anchor_text": ""
    }
  ],
  "clusters": [
    {
      "name": "",
      "topic": "",
      "pages": [],
      "hub_url": ""
    }
  ],
  "summary": {
    "total_pages": 0,
    "indexable_pages": 0,
    "primary_topics": [],
    "important_pages": []
  }
}
```

## 5. ChangeEvent Schema

`ChangeEvent` records what changed between the current crawl and prior known state.

```json
{
  "schema": "orb_weaver.change_event.v1",
  "project_id": "",
  "domain": "",
  "generated_at": "",
  "changes": [
    {
      "type": "page_added",
      "url": "",
      "previous_value": null,
      "current_value": {},
      "severity": "info",
      "summary": ""
    }
  ],
  "summary": {
    "pages_added": 0,
    "pages_removed": 0,
    "pages_changed": 0,
    "important_changes": []
  }
}
```

## 6. WebsiteOrbContext Schema

`WebsiteOrbContext` is the main ORB-facing object.

```json
{
  "schema": "orb_weaver.website_orb_context.v1",
  "project_id": "",
  "domain": "",
  "generated_at": "",
  "site_summary": {},
  "business_facts": [],
  "important_pages": [],
  "entities": [],
  "safe_answers": [],
  "unsupported_claims": [],
  "recommended_sources": [],
  "visitor_intents": [],
  "owner_improvements": [],
  "last_changed": []
}
```

## 7. Substrate Folder Outputs

Start with JSON files plus a SQLite local index. Do not start with a graph database.

```text
clients/<domain>/
  current/
    latest_crawl.json
    latest_audit.json
    latest_page_documents.json
    latest_page_analysis.json
    latest_site_graph.json
    latest_change_log.json
  website_orb_context/
    latest_context.json
    answer_sources.json
    safe_claims.json
    unsupported_claims.json
  history/
    crawl_<id>.json
    graph_<id>.json
    changes_<id>.json
  local_index/
    client_index.sqlite
```

Must-have outputs for v0.1:

```text
latest_crawl.json
latest_audit.json
latest_site_graph.json
latest_change_log.json
latest_orb_context.json
```

## 8. ORB-Facing API Endpoints

Use the existing project model and route namespace.

```text
GET /api/projects/{project_id}/whats-new
GET /api/projects/{project_id}/issues
GET /api/projects/{project_id}/entities
GET /api/projects/{project_id}/journeys
GET /api/projects/{project_id}/orb-context
POST /api/projects/{project_id}/answer
```

Primary endpoint:

```text
GET /api/projects/{project_id}/orb-context
```

Expected response:

```json
{
  "site_summary": {},
  "business_facts": [],
  "important_pages": [],
  "entities": [],
  "safe_answers": [],
  "unsupported_claims": [],
  "recommended_sources": [],
  "visitor_intents": [],
  "owner_improvements": [],
  "last_changed": []
}
```

## 9. Phase 1 Implementation Scope

Pass 1 is the Minimum Intelligence Graph.

Must-have objects:

```text
PageDocument
PageAnalysis
SiteGraph
ChangeEvent
WebsiteOrbContext
```

Must-have scan layers:

```text
1. Semantic Structure
2. Content Purpose Mapping
3. Internal Link Graph
4. Change Tracking
5. Schema / Structured Data
6. Conversion Elements
```

First implementation target after app workflows are stable:

```text
Generate latest_site_graph.json and latest_orb_context.json after a successful crawl.
```

## 10. Explicitly Deferred

Do not implement all intelligence layers at once.

Deferred to Pass 2, Experience Intelligence:

```text
7. User Journey Paths
8. Media Intelligence
9. Performance Signals
10. Sentiment & Tone
```

Deferred to Pass 3, Strategic Intelligence:

```text
11. Competitive Gaps
12. Behavioral Predictions
```

Deferred infrastructure:

```text
Neo4j
External graph database
Vector storage
Cloud storage
Complex graph database migrations
```

The first goal is durable, queryable local intelligence:

```text
JSON files + SQLite local index
```

## Current Priority Boundary

Do not layer this implementation onto broken workflows.

Current priority order:

```text
1. Restore working app workflows.
2. Consolidate and stabilize backend ownership routes.
3. Then implement Intelligence Graph v0.1.
```
