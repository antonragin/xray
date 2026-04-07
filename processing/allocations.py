from collections import defaultdict
from decimal import Decimal


def compute_allocations(positions):
    """Compute all allocation tables from resolved positions.
    Returns a dict of allocation_name -> sorted list of {code, name, weight} dicts.
    """
    acc = {
        'by_instrument_template': defaultdict(float),
        'by_economic_exposure': defaultdict(float),
        'by_exposure_group': defaultdict(float),
        'by_issuer_type': defaultdict(float),
        'by_issuer': defaultdict(float),
        'by_tax_profile': defaultdict(float),
        'by_instrument_kind': defaultdict(float),
        'by_maturity_bucket': defaultdict(float),
    }

    # Pre-load name lookups
    from refdata.models import EconomicExposure, TaxProfile, IssuerType, Issuer, InstrumentTemplate
    exp_map = {e.exposure_code: e for e in EconomicExposure.objects.filter(active=True)}
    exp_group_map = {e.exposure_code: e.exposure_group for e in exp_map.values()}
    tp_map = {t.tax_profile_code: t.name for t in TaxProfile.objects.filter(active=True)}
    it_map = {i.issuer_type_code: i.name for i in IssuerType.objects.filter(active=True)}
    iss_map = {i.issuer_code: i.name for i in Issuer.objects.filter(active=True)}
    tmpl_map = {}
    for t in InstrumentTemplate.objects.filter(active=True):
        tmpl_map[t.template_code] = t.long_name.strip() if t.long_name and t.long_name.strip() else t.short_name

    # Name lookups for groups and kinds
    group_names = {
        'fixed_income': 'Fixed Income', 'equity': 'Equity', 'real_estate': 'Real Estate',
        'crypto': 'Crypto', 'precious_metals': 'Precious Metals', 'undetermined': 'Undetermined',
    }
    kind_names = {
        'listed': 'Listed', 'fixed_income': 'Fixed Income', 'fund': 'Fund',
        'crypto': 'Crypto', 'other': 'Other',
    }

    # Build name resolvers per allocation type
    name_resolvers = {
        'by_instrument_template': lambda code: tmpl_map.get(code, code),
        'by_economic_exposure': lambda code: exp_map[code].name if code in exp_map else code,
        'by_exposure_group': lambda code: group_names.get(code, code),
        'by_issuer_type': lambda code: it_map.get(code, code),
        'by_issuer': lambda code: iss_map.get(code, code),
        'by_tax_profile': lambda code: tp_map.get(code, code),
        'by_instrument_kind': lambda code: kind_names.get(code, code),
        'by_maturity_bucket': lambda code: code,  # buckets are their own labels
    }

    for pos in positions:
        w = float(pos.weight)

        acc['by_instrument_template'][pos.template_code] += w
        acc['by_tax_profile'][pos.tax_profile_code] += w
        acc['by_instrument_kind'][pos.instrument_kind] += w

        for ew in pos.economic_exposures:
            portion = w * ew['weight']
            acc['by_economic_exposure'][ew['code']] += portion
            group = exp_group_map.get(ew['code'], 'unknown')
            acc['by_exposure_group'][group] += portion

        for itw in pos.issuer_type_weights:
            acc['by_issuer_type'][itw['code']] += w * itw['weight']

        if pos.issuer_code:
            acc['by_issuer'][pos.issuer_code] += w

        if pos.maturity_bucket:
            acc['by_maturity_bucket'][pos.maturity_bucket] += w

    result = {}
    for key, data in acc.items():
        resolver = name_resolvers.get(key, lambda c: c)
        result[key] = sorted(
            [{'code': k, 'name': resolver(k), 'weight': round(v, 6)} for k, v in data.items()],
            key=lambda x: -x['weight'],
        )
    return result


def compute_coverage(positions):
    """Compute coverage summary."""
    total_weight = sum(float(p.weight) for p in positions)
    if total_weight == 0:
        return {}

    exp_covered = sum(float(p.weight) for p in positions if p.economic_exposures)
    tp_covered = sum(float(p.weight) for p in positions if p.tax_profile_code)
    it_covered = sum(float(p.weight) for p in positions if p.issuer_type_code or p.issuer_type_weights)
    iss_covered = sum(float(p.weight) for p in positions if p.issuer_code)
    mat_covered = sum(float(p.weight) for p in positions if p.maturity_bucket)

    return {
        'economic_exposure_coverage': round(exp_covered / total_weight, 4),
        'tax_profile_coverage': round(tp_covered / total_weight, 4),
        'issuer_type_coverage': round(it_covered / total_weight, 4),
        'issuer_coverage': round(iss_covered / total_weight, 4),
        'maturity_coverage': round(mat_covered / total_weight, 4),
    }
