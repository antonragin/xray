from collections import defaultdict
from decimal import Decimal


def compute_allocations(positions):
    """Compute all allocation tables from resolved positions.
    Returns a dict of allocation_name -> sorted list of {code, weight} dicts.
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

    # Pre-load exposure group mapping
    from refdata.models import EconomicExposure
    exp_group_map = dict(
        EconomicExposure.objects.filter(active=True)
        .values_list('exposure_code', 'exposure_group')
    )

    for pos in positions:
        w = float(pos.weight)

        acc['by_instrument_template'][pos.template_code] += w
        acc['by_tax_profile'][pos.tax_profile_code] += w
        acc['by_instrument_kind'][pos.instrument_kind] += w

        # Economic exposure (split proportionally for weighted)
        for ew in pos.economic_exposures:
            portion = w * ew['weight']
            acc['by_economic_exposure'][ew['code']] += portion
            group = exp_group_map.get(ew['code'], 'unknown')
            acc['by_exposure_group'][group] += portion

        # Issuer type (split proportionally for weighted)
        for itw in pos.issuer_type_weights:
            acc['by_issuer_type'][itw['code']] += w * itw['weight']

        # Specific issuer
        if pos.issuer_code:
            acc['by_issuer'][pos.issuer_code] += w

        # Maturity bucket
        if pos.maturity_bucket:
            acc['by_maturity_bucket'][pos.maturity_bucket] += w

    # Sort each allocation by descending weight
    result = {}
    for key, data in acc.items():
        result[key] = sorted(
            [{'code': k, 'weight': round(v, 6)} for k, v in data.items()],
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
