from types import SimpleNamespace

from bs4 import BeautifulSoup

from app.catalog.compiler import compile_commercial_catalog
from app.crawler.browser_observation import inspect_rendered_html
from app.crawler.site_intelligence import detect_assistant, detect_platform
from app.orb.pointer_plot import extract_pointer_plot_records


def test_initial_pointer_extraction_never_grants_point_authority():
    soup = BeautifulSoup('<nav><a id="contact" href="/contact">Contact Sales</a></nav>', 'lxml')
    records = extract_pointer_plot_records('https://example.com/', soup)
    assert records
    record = records[0]
    assert record['confidence_class'] == 'UNVERIFIED'
    assert record['lifecycle_state'] == 'CANDIDATE'
    assert record['runtime_policy']['may_point'] is False
    assert record['confidence_evidence']['verification_resolution'] == 'not_run'
    assert 'last_verified_at' not in record
    assert 'last_verified_time' not in record['confidence_evidence']


def test_rendered_observation_detects_digiium_runtime_interface():
    html = '''
    <html><body>
      <script src="https://cdn.digiium.ai/widget.js"></script>
      <div class="digiium-chat-launcher">Live Chat</div>
      <iframe src="https://digiium.ai/widget"></iframe>
    </body></html>
    '''
    observed = inspect_rendered_html(html, 'https://example.com/')
    assert observed['conversational_interface_detected'] is True
    assert 'digiium.ai' in observed['assistant_vendors']
    assert observed['floating_control_candidates']


def test_wordpress_platform_is_evidence_based_and_builder_is_not_guessed():
    page = SimpleNamespace(url='https://example.com/admin', title='WordPress › Update')
    result = detect_platform([page], {'https://example.com/admin': '<html><head><link href="/wp-content/a.css"></head></html>'})
    assert result['platform'] == 'WordPress'
    assert result['evidence_state'] == 'VERIFIED'


def test_catalog_recognizes_ai_employee_offerings_without_inventing_price():
    page = SimpleNamespace(
        url='https://digiium.example/',
        h1="AI Employees That 10x Your Team's Output",
        h2_tags=['Alfred', 'AI Executive Assistant', 'AI Sales Representative'],
        schema_markup=[],
        entity_analysis={'product_names': []},
        semantic_analysis={'pointer_plot_records': []},
    )
    catalog = compile_commercial_catalog([page])
    assert catalog['schema'] == 'orb_weaver.commercial_catalog.v2'
    assert catalog['offering_type_counts']['ai_agent'] >= 2
    assert catalog['priced_entry_count'] == 0
    assert all(entry.get('offers') == [] for entry in catalog['entries'])
