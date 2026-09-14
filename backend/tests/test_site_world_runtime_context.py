import time

import main


def test_compiled_retrieval_bundle_keeps_provenance_and_bounds_context():
    context = {
        "domain": "example.test",
        "knowledge_chunks": {"chunks": [
            {
                "chunk_id": "plans", "route": "/plans", "source_url": "https://example.test/plans",
                "title": "Plans", "heading": "Commercial plans", "text": "Commercial Plus is available.",
                "content_hash": "plans-hash", "provenance": [{"source_type": "crawl"}],
            },
        ]},
        "retrieval_index": {"postings": {"commercial": ["plans"]}},
        "lexical_index": {"aliases": {}},
        "page_knowledge": [{"route": "/plans", "title": "Plans", "summary": "Commercial plans", "content_hash": "plans-hash"}],
        "route_classification": {"routes": [{"route": "/plans", "category": "public_content"}]},
        "authority_flow": {"pages": [{"url": "https://example.test/plans", "authority": 1.0}]},
        "knowledge_graph": {"edges": []},
        "commercial_catalog": {"entries": [{"catalog_id": "plus", "name": "Commercial Plus", "kind": "Product", "url": "https://example.test/plans", "confidence": 0.9}]},
        "source_validation": {"checks": [{"chunk_id": "plans", "status": "VALID", "content_hash": "plans-hash"}]},
    }
    bundle = main._build_site_world_evidence_bundle(
        context, {"route": "/plans", "current_url": "https://example.test/plans"}, "commercial offering"
    )

    assert bundle["selection"] == "compiled_retrieval_index_with_route_boost"
    assert bundle["chunks"][0]["evidence_id"] == "chunk:plans"
    assert bundle["chunks"][0]["provenance"] == [{"source_type": "crawl"}]
    assert bundle["commercial_catalog"][0]["evidence_id"] == "catalog:plus"
    assert bundle["source_validation"][0]["status"] == "VALID"
    assert bundle["context_metrics"]["approximate_characters"] < 10000


def test_anonymous_context_is_session_scoped_and_expires():
    main._anonymous_orb_contexts.clear()
    first_session, second_session = "a" * 24, "b" * 24
    main._update_orb_recent_context(None, "Tell me about plans", "Commercial Plus is available.", None, first_session)

    first = main._orb_memory_summary(None, None, first_session)
    second = main._orb_memory_summary(None, None, second_session)
    assert "Commercial Plus" in first["recent_context"]["summary"]
    assert second["recent_context"] is None

    main._anonymous_orb_contexts[first_session]["expires_at"] = time.time() - 1
    main._prune_anonymous_orb_contexts()
    assert main._orb_memory_summary(None, None, first_session)["recent_context"] is None
