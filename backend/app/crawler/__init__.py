from .engine import OrbWeaverCrawler, PageData
from .scoped import install_scope_support
from .rendered_dom import install_rendered_dom_support
from .seed_contract import install_customer_seed_contract
from .analytics_tags import install_analytics_tag_support
from .analytics_persistence import install_analytics_persistence
from .browser_observation import install_browser_observation_support
from .site_intelligence import install_site_intelligence_support
from .technology_intelligence import install_technology_intelligence_support

install_scope_support(OrbWeaverCrawler)
install_rendered_dom_support(OrbWeaverCrawler)
install_customer_seed_contract(OrbWeaverCrawler)
install_analytics_tag_support(OrbWeaverCrawler, PageData)
install_analytics_persistence(OrbWeaverCrawler)
# Mandatory visitor-visible runtime observation follows the fast source crawl.
install_browser_observation_support(OrbWeaverCrawler)
# The intelligence dossier consumes source, analytics and rendered evidence.
install_site_intelligence_support(OrbWeaverCrawler)
# Technology/local SEO and final assurance gates enrich the same dossier.
install_technology_intelligence_support(OrbWeaverCrawler)

__all__ = ["OrbWeaverCrawler", "PageData"]
