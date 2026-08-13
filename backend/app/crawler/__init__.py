from .engine import OrbWeaverCrawler, PageData
from .scoped import install_scope_support
from .seed_contract import install_customer_seed_contract
from .analytics_tags import install_analytics_tag_support
from .analytics_persistence import install_analytics_persistence

install_scope_support(OrbWeaverCrawler)
install_customer_seed_contract(OrbWeaverCrawler)
install_analytics_tag_support(OrbWeaverCrawler, PageData)
install_analytics_persistence(OrbWeaverCrawler)

__all__ = ["OrbWeaverCrawler", "PageData"]
