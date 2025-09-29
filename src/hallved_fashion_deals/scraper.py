import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from functools import partial
import re
from typing import Any, Callable, Dict, List, Optional, Sequence

import requests

Product = Dict[str, Any]
DISCOUNT_THRESHOLD = 50.0
REQUEST_TIMEOUT = 10
SHOPIFY_LIMIT = 500
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}
WOMENS_KEYWORDS = {
    "women",
    "women's",
    "womens",
    "ladies",
    "girl",
    "girls",
    "female",
    "dress",
    "dresses",
    "skirt",
    "romper",
    "bra",
    "blouse",
    "legging",
    "leggings",
    "tights",
    "heels",
    "sirene",
    "gown",
}


UNISEX_KEYWORDS = {
    "unisex",
    "all-gender",
    "all gender",
    "gender neutral",
    "gender-neutral",
}

MENS_KEYWORDS = {
    "mens",
    "men",
    "male",
    "guy",
    "guys",
}


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


@dataclass(frozen=True)
class SiteConfig:
    name: str
    loader: Callable[[], Any]
    parser: Callable[[Any], List[Product]]


def fetch_url_json(url: str) -> Any:
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()
    if "json" not in content_type:
        raise ValueError(f"Non-JSON response ({content_type}) from {url}")

    try:
        return response.json()
    except UnicodeDecodeError as exc:
        logging.warning("Falling back to apparent encoding for %s due to %s", url, exc)
        response.encoding = response.apparent_encoding or "utf-8"
        return response.json()


def _normalize_image_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    if url.startswith("//"):
        return f"https:{url}"
    return url


def _choose_image(product: Dict[str, Any], variant: Dict[str, Any]) -> Optional[str]:
    variant_image = variant.get("featured_image") or {}
    src = variant_image.get("src") if isinstance(variant_image, dict) else None
    if src:
        return _normalize_image_url(src)
    images = product.get("images", []) or []
    if images and isinstance(images[0], dict):
        src = images[0].get("src")
        return _normalize_image_url(src)
    return None




def _contains_keyword(text: str, keywords: Sequence[str]) -> bool:
    if not text:
        return False
    lowered = text.lower()
    for keyword in keywords:
        escaped = re.escape(keyword.lower()).replace('\\ ', r'\\s+')
        pattern = rf"\b{escaped}\b"
        if re.search(pattern, lowered):
            return True
    return False


def _collect_product_text(product: Dict[str, Any]) -> str:
    parts: List[str] = []
    title = product.get("title")
    if isinstance(title, str):
        parts.append(title.lower())
    product_type = product.get("product_type")
    if isinstance(product_type, str):
        parts.append(product_type.lower())
    tags = product.get("tags")
    if isinstance(tags, list):
        parts.extend(str(tag).lower() for tag in tags if isinstance(tag, (str, int, float)))
    body_html = product.get("body_html")
    if isinstance(body_html, str):
        parts.append(body_html.lower())
    return " ".join(parts)


def _should_skip_product(product: Dict[str, Any]) -> bool:
    text = _collect_product_text(product)
    if not text:
        return False
    contains_womens = _contains_keyword(text, WOMENS_KEYWORDS)
    contains_mens = _contains_keyword(text, MENS_KEYWORDS)
    contains_unisex = _contains_keyword(text, UNISEX_KEYWORDS)
    if contains_womens and not contains_mens and not contains_unisex:
        return True
    return False

def parse_shopify_collection(data: Any, site_name: str, domain: str) -> List[Product]:
    products: List[Product] = []
    if not isinstance(data, dict):
        return products

    for product in data.get("products", []):
        if _should_skip_product(product):
            continue
        title = product.get("title")
        handle = product.get("handle")
        if not title or not handle:
            continue

        best_variant: Optional[Dict[str, Any]] = None
        best_discount = 0.0

        for variant in product.get("variants", []):
            price_raw = variant.get("price")
            compare_raw = variant.get("compare_at_price")
            try:
                price = float(price_raw)
                compare = float(compare_raw)
            except (TypeError, ValueError):
                continue

            if price <= 0 or compare <= 0 or price >= compare:
                continue

            discount = (compare - price) / compare * 100
            if discount < DISCOUNT_THRESHOLD:
                continue

            if discount > best_discount:
                best_discount = discount
                best_variant = {
                    "price": price,
                    "compare": compare,
                    "image_url": _choose_image(product, variant),
                }

        if not best_variant:
            continue

        products.append(
            {
                "site": site_name,
                "title": title,
                "old_price": round(best_variant["compare"], 2),
                "new_price": round(best_variant["price"], 2),
                "discount_percent": round(best_discount, 2),
                "url": f"https://{domain}/products/{handle}",
                "image_url": best_variant["image_url"],
            }
        )

    return products


def make_shopify_site(site_name: str, domain: str, collection_url: str) -> SiteConfig:
    loader = partial(fetch_url_json, collection_url)
    parser = partial(parse_shopify_collection, site_name=site_name, domain=domain)
    return SiteConfig(name=site_name, loader=loader, parser=parser)


DEFAULT_SITES: Sequence[SiteConfig] = (
    make_shopify_site("Hyperdenim", "hyperdenim.com", f"https://hyperdenim.com/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Chubbies", "www.chubbies.com", f"https://www.chubbies.com/collections/last-call/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Mack Weldon", "mackweldon.com", f"https://mackweldon.com/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Goodlife", "goodlifeclothing.com", f"https://goodlifeclothing.com/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Ten Thousand", "www.tenthousand.cc", f"https://www.tenthousand.cc/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Everlane", "www.everlane.com", f"https://www.everlane.com/collections/mens-sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Todd Snyder", "www.toddsnyder.com", f"https://www.toddsnyder.com/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Patagonia Worn Wear", "wornwear.patagonia.com", f"https://wornwear.patagonia.com/collections/mens/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("American Trench", "www.americantrench.com", f"https://www.americantrench.com/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Champion", "www.champion.com", f"https://www.champion.com/collections/mens-sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Allbirds", "www.allbirds.com", f"https://www.allbirds.com/collections/mens-sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Outdoor Voices", "www.outdoorvoices.com", f"https://www.outdoorvoices.com/collections/mens-sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Vuori", "vuoriclothing.com", f"https://vuoriclothing.com/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Billy Reid", "www.billyreid.com", f"https://www.billyreid.com/collections/mens-sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Boston Proper", "www.bostonproper.com", f"https://www.bostonproper.com/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("State and Liberty", "stateandliberty.com", f"https://stateandliberty.com/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Ministry of Supply", "www.ministryofsupply.com", f"https://www.ministryofsupply.com/collections/mens-sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Western Rise", "westernrise.com", f"https://westernrise.com/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Rowing Blazers", "rowingblazers.com", f"https://rowingblazers.com/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Bluffworks", "shop.bluffworks.com", f"https://shop.bluffworks.com/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Helm Boots", "helmboots.com", f"https://helmboots.com/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Thursday Boot", "thursdayboots.com", f"https://thursdayboots.com/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Vincero Collective", "vincerocollective.com", f"https://vincerocollective.com/collections/mens-sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Bonobos", "bonobos.com", f"https://bonobos.com/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Club Monaco", "www.clubmonaco.com", f"https://www.clubmonaco.com/collections/mens-sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Faherty", "www.fahertybrand.com", f"https://www.fahertybrand.com/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Filson", "www.filson.com", f"https://www.filson.com/collections/mens-sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Marine Layer", "www.marinelayer.com", f"https://www.marinelayer.com/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
    make_shopify_site("Topo Designs", "topodesigns.com", f"https://topodesigns.com/collections/sale/products.json?limit={SHOPIFY_LIMIT}"),
)


def scrape_site(config: SiteConfig) -> List[Product]:
    logging.info("Scraping %s", config.name)
    try:
        payload = config.loader()
    except Exception as exc:  # noqa: BLE001 - top level fetch guard
        logging.error("Failed to fetch %s: %s", config.name, exc)
        return []

    try:
        results = config.parser(payload)
    except Exception as exc:  # noqa: BLE001 - parser guard
        logging.error("Failed to parse results for %s: %s", config.name, exc)
        return []

    logging.info("%d qualifying items found on %s", len(results), config.name)
    return results


def scrape_all(sites: Optional[Sequence[SiteConfig]] = None) -> List[Product]:
    sites_to_use = list(sites or DEFAULT_SITES)
    if not sites_to_use:
        return []

    master_list: List[Product] = []
    workers = min(6, len(sites_to_use))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {executor.submit(scrape_site, config): config.name for config in sites_to_use}
        for future in as_completed(future_map):
            try:
                master_list.extend(future.result())
            except Exception as exc:  # noqa: BLE001
                logging.error("Unexpected error scraping %s: %s", future_map[future], exc)

    master_list.sort(key=lambda item: item.get("discount_percent", 0), reverse=True)
    return master_list


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    master_list = scrape_all()

    if not master_list:
        logging.info("No items found with 65%+ discount.")
        return

    print("\n=== FINAL RESULTS (65%+ OFF) ===")
    for product in master_list:
        print(
            f"{product['site']} | {product['title']} | was ${product['old_price']} "
            f"now ${product['new_price']} (-{product['discount_percent']}%)"
        )
        if product.get("url"):
            print(f"    {product['url']}")
        if product.get("image_url"):
            print(f"    Image: {product['image_url']}")


if __name__ == "__main__":
    main()

