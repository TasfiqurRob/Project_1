from __future__ import annotations

from datetime import datetime
from html import escape
from statistics import mean
from typing import Dict, List, Sequence, Union

import streamlit as st

from hallved_fashion_deals.scraper import DEFAULT_SITES, Product, SiteConfig, scrape_all

st.set_page_config(page_title="Hallved Fashion Deals", page_icon="???", layout="wide")

BRAND_COLORS: Dict[str, str] = {
    "primary": "#00AFB9",
    "primary_dark": "#0081A7",
    "muted": "#F07167",
    "background": "#FDFCDC",
    "card": "#FED9B7",
}

CUSTOM_CSS = f"""
<style>
:root {{
    color-scheme: light;
}}

[data-testid="stAppViewContainer"] {{
    font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: linear-gradient(180deg, {BRAND_COLORS['background']} 0%, {BRAND_COLORS['card']} 100%);
    color: #0f172a;
}}

[data-testid="stHeader"] {{
    background: transparent;
}}

.hero {{
    background: linear-gradient(135deg, {BRAND_COLORS['primary_dark']}, {BRAND_COLORS['primary']});
    color: #fff;
    padding: 2.5rem 3rem;
    border-radius: 1.5rem;
    box-shadow: 0 20px 35px rgba(0, 175, 185, 0.25);
    margin-bottom: 2.5rem;
}}

.hero h1 {{
    margin: 0;
    font-size: 2.5rem;
    font-weight: 700;
}}

.hero p {{
    margin-top: 0.75rem;
    max-width: 40rem;
    color: rgba(255, 255, 255, 0.85);
}}

.metric-card {{
    background: {BRAND_COLORS['card']};
    border-radius: 1.25rem;
    padding: 1.5rem;
    border: 1px solid rgba(15, 23, 42, 0.08);
    box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
}}

.metric-card h3 {{
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.16em;
    margin: 0;
    color: {BRAND_COLORS['muted']};
}}

.metric-card p {{
    margin: 0.75rem 0 0;
    font-size: 1.8rem;
    font-weight: 600;
    color: #0f172a;
}}

.deal-card {{
    background: {BRAND_COLORS['card']};
    border-radius: 1.5rem;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(15, 23, 42, 0.06);
    box-shadow: 0 18px 35px rgba(15, 23, 42, 0.1);
}}

.deal-card img {{
    aspect-ratio: 4 / 5;
    object-fit: cover;
    width: 100%;
}}

.deal-body {{
    padding: 1.25rem 1.5rem 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}}

.deal-body h3 {{
    margin: 0;
    font-size: 1.05rem;
}}

.deal-body p {{
    margin: 0;
}}

.deal-meta {{
    color: {BRAND_COLORS['muted']};
    font-size: 0.9rem;
}}

.price-line {{
    font-size: 1.1rem;
    display: flex;
    gap: 0.5rem;
    align-items: baseline;
}}

.price-line span {{
    color: {BRAND_COLORS['muted']};
    font-size: 0.9rem;
}}

.deal-link {{
    margin-top: auto;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.55rem 0.9rem;
    border-radius: 0.75rem;
    background: rgba(0, 175, 185, 0.12);
    color: {BRAND_COLORS['primary_dark']};
    font-weight: 600;
    text-decoration: none;
}}

.pagination-wrapper {{
    margin-top: 2rem;
}}

.pagination-status {{
    text-align: center;
    color: {BRAND_COLORS['muted']};
    font-size: 0.95rem;
    margin-bottom: 0.75rem;
}}

.pagination-chip {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2.5rem;
    height: 2.5rem;
    padding: 0 0.85rem;
    border-radius: 999px;
    background: #e2e8f0;
    color: #0f172a;
    font-weight: 600;
    box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.55);
}}

.pagination-chip--active {{
    background: {BRAND_COLORS['primary']};
    color: #ffffff;
    box-shadow: 0 8px 18px rgba(0, 175, 185, 0.25);
}}

.pagination-chip--ellipsis {{
    background: transparent;
    box-shadow: none;
    color: {BRAND_COLORS['muted']};
    min-width: unset;
    padding: 0 0.4rem;
}}

div[data-testid="baseButton-secondary"] > button {{
    border-radius: 999px;
    border: 1px solid rgba(15, 23, 42, 0.14);
    padding: 0.5rem 0.9rem;
    background: #ffffff;
    color: #1f2937;
    font-weight: 600;
    box-shadow: 0 3px 8px rgba(15, 23, 42, 0.08);
}}

div[data-testid="baseButton-secondary"] > button:hover:not(:disabled) {{
    border-color: rgba(0, 175, 185, 0.45);
    color: {BRAND_COLORS['primary_dark']};
    background: rgba(0, 175, 185, 0.08);
}}

div[data-testid="baseButton-secondary"] > button:disabled {{
    opacity: 0.4;
    box-shadow: none;
    color: rgba(15, 23, 42, 0.5);
}}

.pagination-jump {{
    margin-top: 1rem;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.75rem;
    color: {BRAND_COLORS['muted']};
    font-size: 0.9rem;
}}

.pagination-jump input[type="number"] {{
    width: 5rem;
    text-align: center;
    border-radius: 0.65rem;
    border: 1px solid rgba(15, 23, 42, 0.2);
    padding: 0.35rem 0.5rem;
}}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

SITE_MAP: Dict[str, SiteConfig] = {config.name: config for config in DEFAULT_SITES}
SITE_CHOICES: Sequence[str] = tuple(SITE_MAP)
SORT_FIELDS = {
    "Discount": "discount_percent",
    "Price": "new_price",
}
PAGE_SIZE_OPTIONS = [30, 60, 90]


def trigger_rerun() -> None:
    rerun = getattr(st, "rerun", None)
    if callable(rerun):
        rerun()
        return
    experimental = getattr(st, "experimental_rerun", None)
    if callable(experimental):
        experimental()


if "results" not in st.session_state:
    st.session_state["results"] = []
if "last_updated" not in st.session_state:
    st.session_state["last_updated"] = None
if "page_number" not in st.session_state:
    st.session_state["page_number"] = 1
if "page_size" not in st.session_state:
    st.session_state["page_size"] = PAGE_SIZE_OPTIONS[0]


def format_currency(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"${value:,.2f}"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "-"
    return f"${numeric:,.2f}"


def format_percent(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2f}%"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "-"
    return f"{numeric:.2f}%"



def build_pagination_sequence(current_page: int, total_pages: int, window: int = 2) -> List[Union[int, str]]:
    if total_pages <= 1:
        return [1]
    pages = {1, total_pages, current_page}
    for offset in range(-window, window + 1):
        candidate = current_page + offset
        if 1 <= candidate <= total_pages:
            pages.add(candidate)
    ordered = sorted(pages)
    sequence: List[Union[int, str]] = []
    previous = None
    for page in ordered:
        if previous is not None and page - previous > 1:
            sequence.append('ellipsis')
        sequence.append(page)
        previous = page
    return sequence


def render_pagination(current_page: int, total_pages: int) -> None:
    if total_pages <= 1:
        return

    st.markdown(
        f"<div class='pagination-wrapper'><div class='pagination-status'>Page {current_page} of {total_pages}</div></div>",
        unsafe_allow_html=True,
    )

    sequence = build_pagination_sequence(current_page, total_pages)

    elements: List[dict[str, Union[int, str, bool]]] = [
        {'type': 'control', 'name': 'first', 'label': '<<', 'disabled': current_page == 1, 'target': 1},
        {'type': 'control', 'name': 'prev', 'label': '<', 'disabled': current_page == 1, 'target': max(1, current_page - 1)},
    ]

    for item in sequence:
        if isinstance(item, int):
            elements.append({'type': 'page', 'page': item})
        else:
            elements.append({'type': 'ellipsis'})

    elements.extend(
        [
            {'type': 'control', 'name': 'next', 'label': '>', 'disabled': current_page >= total_pages, 'target': min(total_pages, current_page + 1)},
            {'type': 'control', 'name': 'last', 'label': '>>', 'disabled': current_page >= total_pages, 'target': total_pages},
        ]
    )

    outer_cols = st.columns([1, 6, 1])
    with outer_cols[1]:
        cols = st.columns(len(elements))
        for column, element in zip(cols, elements):
            with column:
                if element['type'] == 'ellipsis':
                    st.markdown("<div class='pagination-chip pagination-chip--ellipsis'>&hellip;</div>", unsafe_allow_html=True)
                elif element['type'] == 'page':
                    page_num = int(element['page'])
                    if page_num == current_page:
                        st.markdown(
                            f"<div class='pagination-chip pagination-chip--active'>{page_num}</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        if st.button(
                            str(page_num),
                            key=f'pagination_page_{page_num}',
                            type='secondary',
                            use_container_width=True,
                        ):
                            st.session_state['page_number'] = page_num
                            trigger_rerun()
                else:
                    if st.button(
                        element['label'],
                        key=f"pagination_{element['name']}",
                        disabled=bool(element['disabled']),
                        type='secondary',
                        use_container_width=True,
                    ):
                        st.session_state['page_number'] = int(element['target'])
                        trigger_rerun()

    jump_cols = st.columns([3, 2, 3])
    with jump_cols[1]:
        jump_value = st.number_input(
            'Jump to page',
            min_value=1,
            max_value=total_pages,
            value=current_page,
            step=1,
            format='%d',
        )
        if int(jump_value) != current_page:
            st.session_state['page_number'] = int(jump_value)
            trigger_rerun()



def run_scrape(site_names: Sequence[str]) -> List[Product]:
    configs = [SITE_MAP[name] for name in site_names]
    return scrape_all(configs)


st.markdown(
    """
    <section class="hero">
      <h1>Hallved Fashion Deals</h1>
      <p>Hand-curated menswear markdowns from top retailers. Filter, sort, and open deals in a click.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Filters")
    selected_sites = st.multiselect(
        "Retailers",
        options=SITE_CHOICES,
        default=list(SITE_CHOICES),
    )
    if not selected_sites:
        st.info("Select at least one retailer to fetch deals.")

    sort_field_label = st.selectbox("Sort by", options=list(SORT_FIELDS.keys()), index=0)
    sort_direction = st.radio("Direction", options=["Descending", "Ascending"], index=0, horizontal=True)
    page_size = st.selectbox("Items per page", options=PAGE_SIZE_OPTIONS, index=0)

    if page_size != st.session_state["page_size"]:
        st.session_state["page_size"] = page_size
        st.session_state["page_number"] = 1

    if st.button("Refresh deals", type="primary", use_container_width=True):
        if selected_sites:
            with st.spinner("Fetching latest deals..."):
                st.session_state["results"] = run_scrape(selected_sites)
                st.session_state["last_updated"] = datetime.utcnow()
                st.session_state["page_number"] = 1
        else:
            st.warning("Please choose at least one retailer before refreshing.")

results: List[Product] = st.session_state.get("results") or []
sort_key = SORT_FIELDS[sort_field_label]
reverse = sort_direction == "Descending"
results = sorted(
    results,
    key=lambda item: item.get(sort_key) if isinstance(item.get(sort_key), (int, float)) else 0,
    reverse=reverse,
)

total_items = len(results)
if total_items == 0:
    st.warning("No deals yet. Use the sidebar to refresh.")
    st.stop()

values = [
    float(item.get("discount_percent"))
    for item in results
    if isinstance(item.get("discount_percent"), (int, float))
]
average_discount = mean(values) if values else 0.0
best_discount = max(values) if values else 0.0
sites_contributing = {item.get("site") for item in results if item.get("site")}

col1, col2, col3 = st.columns(3)
col1.markdown(
    f"""
    <div class="metric-card">
      <h3>Items</h3>
      <p>{total_items}</p>
    </div>
    """,
    unsafe_allow_html=True,
)
col2.markdown(
    f"""
    <div class="metric-card">
      <h3>Retailers</h3>
      <p>{len(sites_contributing)}</p>
    </div>
    """,
    unsafe_allow_html=True,
)
col3.markdown(
    f"""
    <div class="metric-card">
      <h3>Average Discount</h3>
      <p>{format_percent(average_discount)}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

current_page = st.session_state.get("page_number", 1)
page_size = st.session_state.get("page_size", PAGE_SIZE_OPTIONS[0])
total_pages = max(1, (total_items + page_size - 1) // page_size)
current_page = min(max(1, current_page), total_pages)
st.session_state["page_number"] = current_page

start_index = (current_page - 1) * page_size
end_index = min(total_items, start_index + page_size)
page_results = results[start_index:end_index]

last_updated = st.session_state.get("last_updated")
if last_updated:
    st.caption(f"Last updated: {last_updated.strftime('%Y-%m-%d %H:%M:%S')} UTC")

st.caption(f"Showing items {start_index + 1}-{end_index} of {total_items} total results.")

for row_start in range(0, len(page_results), 3):
    cards = page_results[row_start : row_start + 3]
    columns = st.columns(3)
    for column, deal in zip(columns, cards):
        title = escape(str(deal.get("title", "Untitled")))
        site = escape(str(deal.get("site", "Unknown retailer")))
        price = format_currency(deal.get("new_price"))
        old_price = format_currency(deal.get("old_price"))
        discount = format_percent(deal.get("discount_percent"))
        image_url = deal.get("image_url")
        link = deal.get("url")

        image_html = (
            f'<img src="{escape(str(image_url))}" alt="{title}">' if image_url else ""
        )
        link_section = (
            f'<a class="deal-link" href="{escape(str(link))}" target="_blank" rel="noreferrer">View product &rarr;</a>'
            if link
            else '<p class="deal-meta">No product link available</p>'
        )

        card_html = f"""
        <div class="deal-card">
            {image_html}
            <div class="deal-body">
                <h3>{title}</h3>
                <p class="deal-meta">{site}</p>
                <div class="price-line">
                    <strong>{price}</strong>
                    <span>was {old_price}</span>
                </div>
                <p class="deal-meta">Discount: {discount}</p>
                {link_section}
            </div>
        </div>
        """
        column.markdown(card_html, unsafe_allow_html=True)

render_pagination(current_page, total_pages)


