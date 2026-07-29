from .engine import OrbWeaverCrawler, PageData
from .scoped import install_scope_support

install_scope_support(OrbWeaverCrawler)

__all__ = ["OrbWeaverCrawler", "PageData"]
