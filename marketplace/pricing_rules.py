from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


MONEY = Decimal('0.01')


@dataclass
class PricingResult:
    unit_price: Decimal
    subtotal: Decimal
    log: dict = field(default_factory=dict)


@dataclass
class QuantityValidation:
    is_valid: bool
    message: str = ''
    suggested_quantity: int | None = None


def _money(value, default='0'):
    try:
        return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default).quantize(MONEY, rounding=ROUND_HALF_UP)


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _rules(item):
    rules = getattr(item, 'pricing_rules', None) or {}
    return rules if isinstance(rules, dict) else {}


def validate_quantity(item, quantity):
    """Strict quantity validation for product/supermarket wholesale controls."""
    qty = _int(quantity, 1)
    min_qty = max(1, _int(getattr(item, 'min_order_quantity', 1), 1))
    max_qty = getattr(item, 'max_order_quantity', None)
    max_qty = _int(max_qty, 0) if max_qty else None
    step = max(1, _int(getattr(item, 'quantity_step', 1), 1))

    if qty < min_qty:
        return QuantityValidation(False, f'最低购买数量为 {min_qty} 件', min_qty)
    if max_qty and qty > max_qty:
        return QuantityValidation(False, f'最多只能购买 {max_qty} 件', max_qty)
    if step > 1 and ((qty - min_qty) % step) != 0:
        next_qty = min_qty + (((qty - min_qty) // step) + 1) * step
        if max_qty and next_qty > max_qty:
            next_qty = max_qty
        return QuantityValidation(False, f'该商品必须按 {step} 件递增，建议数量：{next_qty}', next_qty)
    return QuantityValidation(True)


def _tier_price(base_price, quantity, rules, applied):
    best = None
    for tier in rules.get('tiers', []) or []:
        min_qty = _int(tier.get('min'), 1)
        max_raw = tier.get('max')
        max_qty = _int(max_raw, 0) if max_raw not in ('', None) else None
        if quantity >= min_qty and (max_qty is None or quantity <= max_qty):
            if best is None or min_qty > best['min']:
                best = {'min': min_qty, 'max': max_qty, 'unit_price': _money(tier.get('unit_price'), base_price)}
    if best:
        applied.append({'type': 'tier', **best})
        return best['unit_price']
    return base_price


def _discounted_subtotal(subtotal, rules, applied, context):
    best = None
    for rule in rules.get('discounts', []) or []:
        min_total = _money(rule.get('min_cart_total', '0'))
        role = (rule.get('user_role') or '').strip()
        category_id = rule.get('category_id')
        if min_total and subtotal < min_total:
            continue
        if role and role != (context.get('user_role') or ''):
            continue
        if category_id and str(category_id) != str(context.get('category_id') or ''):
            continue
        priority = _int(rule.get('priority'), 0)
        if best is None or priority > best['priority']:
            best = {**rule, 'priority': priority}
    if not best:
        return subtotal

    discount_type = best.get('type', 'percent')
    value = _money(best.get('value'), '0')
    if discount_type == 'fixed':
        subtotal = max(Decimal('0.00'), subtotal - value)
    else:
        subtotal = subtotal * (Decimal('1') - (value / Decimal('100')))
    subtotal = subtotal.quantize(MONEY, rounding=ROUND_HALF_UP)
    applied.append({'type': 'discount', 'rule': best})
    return subtotal


def _bogo_subtotal(unit_price, quantity, rules, applied):
    bogo = rules.get('bogo') or {}
    buy_qty = _int(bogo.get('buy_qty'), 0)
    get_qty = _int(bogo.get('get_qty'), 0)
    discount_percent = _money(bogo.get('discount_percent'), '100')
    if buy_qty <= 0 or get_qty <= 0 or quantity < buy_qty:
        return unit_price * quantity

    group_size = buy_qty + get_qty
    groups = quantity // group_size
    discounted_units = groups * get_qty
    discount = unit_price * discounted_units * (discount_percent / Decimal('100'))
    subtotal = max(Decimal('0.00'), (unit_price * quantity) - discount).quantize(MONEY, rounding=ROUND_HALF_UP)
    if discounted_units:
        applied.append({
            'type': 'bogo',
            'buy_qty': buy_qty,
            'get_qty': get_qty,
            'discount_percent': str(discount_percent),
            'discounted_units': discounted_units,
        })
    return subtotal


def pricing_display_context(item):
    """Ready-to-render summary of an item's active wholesale rules (tier
    ladder + BOGO) for the storefront product/supermarket detail pages —
    the engine in evaluate_pricing() was already applied correctly at
    cart/checkout time, but nothing ever showed the shopper the ladder
    itself, so there was no visible incentive to buy more."""
    base_price = _money(getattr(item, 'price', 0))
    rules = _rules(item)

    tiers = []
    for tier in sorted(rules.get('tiers') or [], key=lambda t: _int(t.get('min'), 1)):
        min_qty = _int(tier.get('min'), 1)
        max_raw = tier.get('max')
        max_qty = _int(max_raw, 0) if max_raw not in ('', None) else None
        unit_price = _money(tier.get('unit_price'), base_price)
        savings_percent = 0
        if base_price > 0 and unit_price < base_price:
            savings_percent = int(((base_price - unit_price) / base_price) * 100)
        tiers.append({
            'min': min_qty,
            'max': max_qty,
            'unit_price': unit_price,
            'savings_percent': savings_percent,
        })

    bogo = rules.get('bogo') or {}
    bogo_display = None
    buy_qty = _int(bogo.get('buy_qty'), 0)
    get_qty = _int(bogo.get('get_qty'), 0)
    if buy_qty > 0 and get_qty > 0:
        discount_percent = _money(bogo.get('discount_percent'), '100')
        bogo_display = {
            'buy_qty': buy_qty,
            'get_qty': get_qty,
            'discount_percent': discount_percent,
            'is_free': discount_percent >= 100,
        }

    return {
        'base_price': base_price,
        'tiers': tiers,
        'bogo': bogo_display,
        'has_wholesale': bool(tiers) or bogo_display is not None,
    }


def evaluate_pricing(item, item_type, quantity, context=None):
    """Evaluate active pricing rules without database lookups."""
    context = context or {}
    quantity = max(1, _int(quantity, 1))
    base_price = _money(getattr(item, 'price', 0))
    rules = _rules(item)
    applied = []

    context.setdefault('category_id', getattr(item, 'category_id', None))
    unit_price = _tier_price(base_price, quantity, rules, applied)
    subtotal = _bogo_subtotal(unit_price, quantity, rules, applied)
    subtotal = _discounted_subtotal(subtotal, rules, applied, context)

    if quantity:
        effective_unit = (subtotal / Decimal(quantity)).quantize(MONEY, rounding=ROUND_HALF_UP)
    else:
        effective_unit = unit_price

    return PricingResult(
        unit_price=effective_unit,
        subtotal=subtotal,
        log={
            'item_type': item_type,
            'quantity': quantity,
            'base_unit_price': str(base_price),
            'effective_unit_price': str(effective_unit),
            'subtotal': str(subtotal),
            'applied_rules': applied,
        },
    )
