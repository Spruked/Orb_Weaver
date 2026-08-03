from .engine import OrbWeaverCrawler, PageData
from .scoped import install_scope_support
from .analytics_tags import install_analytics_tag_support

install_scope_support(OrbWeaverCrawler)
install_analytics_tag_support(OrbWeaverCrawler, PageData)

__all__ = ["OrbWeaverCrawler", "PageData"]
