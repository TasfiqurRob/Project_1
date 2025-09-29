"""Hallved Fashion Deals scraping toolkit."""

from .scraper import (
    DEFAULT_SITES,
    DISCOUNT_THRESHOLD,
    Product,
    SiteConfig,
    scrape_all,
)

__all__ = [
    "DEFAULT_SITES",
    "DISCOUNT_THRESHOLD",
    "Product",
    "SiteConfig",
    "scrape_all",
]
