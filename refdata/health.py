from .models import (
    EconomicExposure, TaxProfile, IssuerType, Issuer, InstrumentTemplate,
    ReferenceBase,
)


def run_all_checks():
    """Return a list of {name, severity, items} check results."""
    checks = []

    # 1. Templates with no economic exposure
    bad = list(
        InstrumentTemplate.objects.filter(
            active=True,
            primary_economic_exposure__isnull=True,
            economic_exposure_weights_json__isnull=True,
        ).values_list('template_code', flat=True)
    )
    checks.append({
        'name': 'Templates missing economic exposure',
        'severity': 'error',
        'items': bad,
    })

    # 2. Weighted exposure totals != 1.0
    bad = []
    for t in InstrumentTemplate.objects.filter(
        active=True, economic_exposure_weights_json__isnull=False
    ):
        total = sum(t.economic_exposure_weights_json.values())
        if abs(total - 1.0) > 0.0005:
            bad.append(f'{t.template_code} (sum={total:.4f})')
    checks.append({
        'name': 'Templates with invalid exposure weight totals',
        'severity': 'error',
        'items': bad,
    })

    # 3. Weighted issuer-type totals != 1.0
    bad = []
    for t in InstrumentTemplate.objects.filter(
        active=True, issuer_type_weights_json__isnull=False
    ):
        total = sum(t.issuer_type_weights_json.values())
        if abs(total - 1.0) > 0.0005:
            bad.append(f'{t.template_code} (sum={total:.4f})')
    checks.append({
        'name': 'Templates with invalid issuer-type weight totals',
        'severity': 'error',
        'items': bad,
    })

    # 4. Active templates missing tax profile (belt-and-suspenders)
    bad = list(
        InstrumentTemplate.objects.filter(
            active=True, tax_profile__isnull=True,
        ).values_list('template_code', flat=True)
    )
    checks.append({
        'name': 'Active templates missing tax profile',
        'severity': 'error',
        'items': bad,
    })

    # 5. Active issuers pointing to inactive issuer types
    bad = list(
        Issuer.objects.filter(
            active=True, issuer_type__active=False,
        ).values_list('issuer_code', flat=True)
    )
    checks.append({
        'name': 'Active issuers with inactive issuer type',
        'severity': 'warning',
        'items': bad,
    })

    # 6. Templates requiring expiry_date but missing risk/performance instructions
    bad = []
    for t in InstrumentTemplate.objects.filter(
        active=True, requires_expiry_date=True
    ):
        missing = []
        if not t.instructions_performance.strip():
            missing.append('instructions_performance')
        if not t.instructions_risk.strip():
            missing.append('instructions_risk')
        if missing:
            bad.append(f'{t.template_code} (missing: {", ".join(missing)})')
    checks.append({
        'name': 'Templates requiring expiry_date but missing risk/performance instructions',
        'severity': 'warning',
        'items': bad,
    })

    # 7. Instruction coverage summary
    coverage = {}
    for model, code_field in [
        (EconomicExposure, 'exposure_code'),
        (TaxProfile, 'tax_profile_code'),
        (IssuerType, 'issuer_type_code'),
        (Issuer, 'issuer_code'),
        (InstrumentTemplate, 'template_code'),
    ]:
        active_qs = model.objects.filter(active=True)
        total = active_qs.count()
        with_all = 0
        with_none = 0
        for obj in active_qs:
            filled = sum(1 for f in ReferenceBase.INSTRUCTION_FIELDS if getattr(obj, f, '').strip())
            if filled == 6:
                with_all += 1
            elif filled == 0:
                with_none += 1
        coverage[model.__name__] = {
            'total': total, 'with_all_6': with_all, 'with_none': with_none,
        }
    checks.append({
        'name': 'Instruction coverage summary',
        'severity': 'info',
        'coverage': coverage,
    })

    return checks
