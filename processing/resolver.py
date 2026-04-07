from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from refdata.models import (
    EconomicExposure, IssuerType, ReferenceBase,
)


@dataclass
class ResolvedPosition:
    row_number: int
    template_code: str
    weight: Decimal
    instrument_kind: str
    short_name: str

    # Display name (prefer long_name, fall back to short_name)
    display_name: str = ''

    # Resolved references
    tax_profile_code: str = ''
    tax_profile_name: str = ''
    issuer_code: Optional[str] = None
    issuer_name: Optional[str] = None
    issuer_type_code: Optional[str] = None
    issuer_type_name: Optional[str] = None
    economic_exposures: list = field(default_factory=list)
    issuer_type_weights: list = field(default_factory=list)

    # Derived
    expiry_date: Optional[date] = None
    days_to_expiry: Optional[int] = None
    years_to_expiry: Optional[float] = None
    maturity_bucket: Optional[str] = None
    country_bucket: Optional[str] = None

    # Instructions per angle
    instructions: dict = field(default_factory=dict)

    # Template metadata carried forward
    template_metadata: dict = field(default_factory=dict)


def resolve_positions(parsed_rows, upload_date=None):
    """Resolve a list of parsed rows into ResolvedPositions."""
    if upload_date is None:
        upload_date = date.today()

    # Pre-load lookup dicts
    exposures = {e.exposure_code: e for e in EconomicExposure.objects.filter(active=True)}
    issuer_types = {it.issuer_type_code: it for it in IssuerType.objects.filter(active=True)}

    positions = []
    for row in parsed_rows:
        pos = _resolve_single(row, upload_date, exposures, issuer_types)
        positions.append(pos)
    return positions


def _resolve_single(row, upload_date, exposures, issuer_types):
    template = row['template']
    weight = row['weight']

    # 1. Basic fields
    pos = ResolvedPosition(
        row_number=row['row_number'],
        template_code=row['template_code'],
        weight=weight,
        instrument_kind=template.instrument_kind,
        short_name=template.short_name,
        display_name=template.long_name.strip() if template.long_name and template.long_name.strip() else template.short_name,
        tax_profile_code=template.tax_profile.tax_profile_code,
        tax_profile_name=template.tax_profile.name,
    )

    # Template metadata
    pos.template_metadata = {
        'long_name': template.long_name,
        'cnpj': template.cnpj,
        'b3_listed': template.b3_listed,
        'is_bdr': template.is_bdr,
        'yearly_fee_pct': float(template.yearly_fee_pct) if template.yearly_fee_pct is not None else None,
        'performance_fee_pct': float(template.performance_fee_pct) if template.performance_fee_pct is not None else None,
        'has_fgc': template.has_fgc,
        'requires_expiry_date': template.requires_expiry_date,
    }

    # 3. Resolve effective issuer
    issuer = row.get('issuer')
    if not issuer and template.issuer_id:
        issuer = template.issuer
    if issuer:
        pos.issuer_code = issuer.issuer_code
        pos.issuer_name = issuer.name

    # 4. Resolve effective issuer type
    if issuer:
        pos.issuer_type_code = issuer.issuer_type.issuer_type_code
        pos.issuer_type_name = issuer.issuer_type.name
        pos.issuer_type_weights = [{'code': issuer.issuer_type.issuer_type_code, 'name': issuer.issuer_type.name, 'weight': 1.0}]
    elif row.get('issuer_type_override'):
        it = row['issuer_type_override']
        pos.issuer_type_code = it.issuer_type_code
        pos.issuer_type_name = it.name
        pos.issuer_type_weights = [{'code': it.issuer_type_code, 'name': it.name, 'weight': 1.0}]
    elif template.primary_issuer_type_id:
        it = template.primary_issuer_type
        pos.issuer_type_code = it.issuer_type_code
        pos.issuer_type_name = it.name
        pos.issuer_type_weights = [{'code': it.issuer_type_code, 'name': it.name, 'weight': 1.0}]
    elif template.issuer_type_weights_json:
        pos.issuer_type_weights = [
            {'code': code, 'name': issuer_types[code].name if code in issuer_types else code, 'weight': w}
            for code, w in sorted(template.issuer_type_weights_json.items(), key=lambda x: -x[1])
        ]
        if pos.issuer_type_weights:
            pos.issuer_type_code = pos.issuer_type_weights[0]['code']
            pos.issuer_type_name = pos.issuer_type_weights[0].get('name', '')

    # 5. Resolve economic exposure
    if template.primary_economic_exposure_id:
        exp = template.primary_economic_exposure
        pos.economic_exposures = [{'code': exp.exposure_code, 'name': exp.name, 'weight': 1.0}]
    elif template.economic_exposure_weights_json:
        pos.economic_exposures = [
            {'code': code, 'name': exposures[code].name if code in exposures else code, 'weight': w}
            for code, w in sorted(template.economic_exposure_weights_json.items(), key=lambda x: -x[1])
        ]

    # 7. Expiry / maturity
    pos.expiry_date = row.get('expiry_date')
    if pos.expiry_date:
        delta = pos.expiry_date - upload_date
        pos.days_to_expiry = delta.days
        pos.years_to_expiry = round(delta.days / 365.25, 2)
        pos.maturity_bucket = _maturity_bucket(delta.days)

    # Country bucket
    pos.country_bucket = _country_bucket(pos)

    # 8. Collect instructions
    pos.instructions = _collect_instructions(template, issuer, pos, exposures, issuer_types)

    return pos


def _maturity_bucket(days):
    if days < 365:
        return '<1y'
    elif days < 1096:
        return '1-3y'
    elif days < 1826:
        return '3-5y'
    elif days < 3652:
        return '5-10y'
    else:
        return '10y+'


def _country_bucket(pos):
    """Derive Brazil / Non-Brazil from exposure or issuer type codes."""
    br_indicators = {'_br'}
    for exp in pos.economic_exposures:
        if exp['code'].endswith('_br'):
            return 'Brazil'
    if pos.issuer_type_code and pos.issuer_type_code.startswith('br_'):
        return 'Brazil'
    if pos.economic_exposures:
        return 'Non-Brazil'
    if pos.issuer_type_code and pos.issuer_type_code.startswith('nonbr_'):
        return 'Non-Brazil'
    return None


def _collect_instructions(template, issuer, pos, exposures, issuer_types):
    """Collect instruction texts from all relevant sources for each angle."""
    angles = ['diversification', 'liquidity', 'fees', 'tax', 'risk', 'performance']
    result = {}

    for angle in angles:
        field_name = f'instructions_{angle}'
        sources = []

        # From instrument_template
        text = getattr(template, field_name, '').strip()
        if text:
            sources.append({'source': 'instrument_template', 'code': template.template_code, 'text': text})

        # From issuer (if resolved)
        if issuer:
            text = getattr(issuer, field_name, '').strip()
            if text:
                sources.append({'source': 'issuer', 'code': issuer.issuer_code, 'text': text})

        # From issuer_type(s)
        for itw in pos.issuer_type_weights:
            it = issuer_types.get(itw['code'])
            if it:
                text = getattr(it, field_name, '').strip()
                if text:
                    sources.append({'source': 'issuer_type', 'code': it.issuer_type_code, 'text': text})

        # From economic_exposure(s)
        for ew in pos.economic_exposures:
            exp = exposures.get(ew['code'])
            if exp:
                text = getattr(exp, field_name, '').strip()
                if text:
                    sources.append({'source': 'economic_exposure', 'code': exp.exposure_code, 'text': text})

        # From tax_profile
        tp = template.tax_profile
        text = getattr(tp, field_name, '').strip()
        if text:
            sources.append({'source': 'tax_profile', 'code': tp.tax_profile_code, 'text': text})

        result[angle] = sources

    return result


def flatten_instructions(sources):
    """Flatten a list of instruction sources into the spec's text format."""
    if not sources:
        return ''
    blocks = []
    for s in sources:
        label = s['source'].upper()
        blocks.append(f'[{label}]\n{s["text"]}')
    return '\n'.join(blocks)
