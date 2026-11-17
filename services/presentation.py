"""Safe, deterministic customer-facing offer grouping.

Only confirmed, available offers can be featured. Price equality is scoped to
retailer and product identity, never across different stores or configurations.
"""
from collections import OrderedDict
from math import isfinite


def _confirmed(offer):
    """Only eligible in-stock, positively assessed offers enter best-price ranking."""
    confidence = str(offer.get('match_confidence') or '').lower()
    availability = str(offer.get('availability') or '').strip().lower().replace('-', ' ')
    try:
        price = float(offer.get('price'))
    except (ValueError, TypeError):
        return False
    blocked = ('out of stock', 'not in stock', 'unavailable', 'not available', 'sold out', 'soldout')
    return (confidence in {'high', 'medium'}
            and not offer.get('unverified_attributes')
            and isfinite(price) and price > 0
            and not any(term in availability for term in blocked))


def _identity(offer):
    # Comparison keys include hard-checked model/configuration attributes.
    # Colour alone may differ when the retailer and listed price are equal.
    key = offer.get('comparison_key')
    if key:
        return '|'.join(part for part in str(key).split('|')
                        if not part.startswith(('color=', 'colour=')))
    # Never guess that distinct product keys refer to the same configuration.
    return str(offer.get('product_key') or offer.get('sku') or offer.get('name') or '')


def _colour(offer):
    attrs = offer.get('attributes') or {}
    return str(attrs.get('color') or attrs.get('colour') or '').strip()


def prepare_comparison(offers):
    confirmed, review = [], []
    for item in offers:
        (confirmed if _confirmed(item) else review).append(dict(item))
    confirmed.sort(key=lambda p: (float(p.get('price') or float('inf')), str(p.get('retailer', '')).lower()))
    best_price = float(confirmed[0]['price']) if confirmed else None
    for p in confirmed:
        p['featured_best'] = best_price is not None and float(p['price']) == best_price
    # Collapse colour listings only when retailer, canonical identity and price
    # are identical. Keep distinct URLs available as variant links.
    groups = OrderedDict()
    for item in confirmed:
        key = (str(item.get('retailer', '')).casefold(), _identity(item), float(item['price']))
        if key not in groups:
            entry = dict(item)
            entry['colour_options'] = []
            entry['variant_links'] = []
            groups[key] = entry
        entry = groups[key]
        colour = _colour(item)
        if colour and colour not in entry['colour_options']:
            entry['colour_options'].append(colour)
        if item.get('url') and not any(v['url'] == item['url'] for v in entry['variant_links']):
            entry['variant_links'].append({'colour': colour or 'View variant', 'url': item['url']})
    return list(groups.values()), review, best_price
