import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings
from refdata.models import InstrumentTemplate, Issuer, IssuerType


REQUIRED_COLUMNS = ['instrument_template_code', 'weight', 'expiry_date', 'issuer_code', 'issuer_type_code']


@dataclass
class ValidationResult:
    is_valid: bool = True
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    row_count: int = 0
    total_weight: float = 0.0


def validate_csv(csv_input):
    """Validate a portfolio CSV. Accepts file path (str) or file-like object."""
    result = ValidationResult()

    if isinstance(csv_input, str):
        with open(csv_input, 'r', newline='') as f:
            content = f.read()
    elif hasattr(csv_input, 'read'):
        raw = csv_input.read()
        content = raw.decode('utf-8') if isinstance(raw, bytes) else raw
    else:
        result.is_valid = False
        result.errors.append('Invalid input: expected file path or file-like object.')
        return result

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        result.is_valid = False
        result.errors.append('CSV file is empty or has no headers.')
        return result

    missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
    if missing:
        result.is_valid = False
        result.errors.append(f'Missing required columns: {missing}')
        return result

    # Pre-load lookups
    templates = {t.template_code: t for t in InstrumentTemplate.objects.filter(active=True)}
    issuers = {i.issuer_code: i for i in Issuer.objects.filter(active=True).select_related('issuer_type')}
    issuer_types = {it.issuer_type_code: it for it in IssuerType.objects.filter(active=True)}

    total_weight = Decimal('0')
    parsed_rows = []

    for row_num, row in enumerate(reader, start=1):
        tc = row.get('instrument_template_code', '').strip()
        weight_str = row.get('weight', '').strip()
        expiry_str = row.get('expiry_date', '').strip()
        ic = row.get('issuer_code', '').strip()
        itc = row.get('issuer_type_code', '').strip()

        # 1. Template exists and active
        if not tc:
            result.errors.append(f'Row {row_num}: instrument_template_code is empty.')
            result.is_valid = False
            continue
        template = templates.get(tc)
        if not template:
            result.errors.append(f'Row {row_num}: unknown or inactive template code "{tc}".')
            result.is_valid = False
            continue

        # 2. Weight is numeric and positive
        try:
            weight = Decimal(weight_str)
        except (InvalidOperation, ValueError):
            result.errors.append(f'Row {row_num}: weight "{weight_str}" is not a valid number.')
            result.is_valid = False
            continue
        if weight <= 0:
            result.errors.append(f'Row {row_num}: weight must be strictly positive, got {weight}.')
            result.is_valid = False
            continue
        total_weight += weight

        # 3. Expiry date
        expiry_date = None
        if expiry_str:
            try:
                expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d').date()
            except ValueError:
                result.errors.append(f'Row {row_num}: invalid expiry_date "{expiry_str}" (expected YYYY-MM-DD).')
                result.is_valid = False
                continue

        # 4. Expiry required?
        if template.requires_expiry_date and not expiry_date:
            result.errors.append(f'Row {row_num}: template "{tc}" requires expiry_date but none provided.')
            result.is_valid = False
            continue

        # 5-6. Issuer/issuer_type resolution
        issuer = None
        issuer_type_override = None
        if ic:
            issuer = issuers.get(ic)
            if not issuer:
                result.errors.append(f'Row {row_num}: unknown or inactive issuer_code "{ic}".')
                result.is_valid = False
                continue
            if itc:
                result.warnings.append(f'Row {row_num}: both issuer_code and issuer_type_code provided. Using issuer_code.')
        elif itc:
            issuer_type_override = issuer_types.get(itc)
            if not issuer_type_override:
                result.errors.append(f'Row {row_num}: unknown or inactive issuer_type_code "{itc}".')
                result.is_valid = False
                continue

        # 8. Template requires issuer/issuer_type but neither provided
        if template.requires_issuer_or_issuer_type:
            has_issuer_info = (
                issuer is not None
                or issuer_type_override is not None
                or template.issuer_id is not None
                or template.primary_issuer_type_id is not None
                or template.issuer_type_weights_json is not None
            )
            if not has_issuer_info:
                result.errors.append(
                    f'Row {row_num}: template "{tc}" requires issuer or issuer_type but none available.'
                )
                result.is_valid = False
                continue

        parsed_rows.append({
            'row_number': row_num,
            'template_code': tc,
            'template': template,
            'weight': weight,
            'expiry_date': expiry_date,
            'issuer': issuer,
            'issuer_code': ic or None,
            'issuer_type_override': issuer_type_override,
            'issuer_type_code': itc or None,
        })

    if not parsed_rows and not result.errors:
        result.errors.append('CSV contains no data rows.')
        result.is_valid = False

    # 3. Total weight check
    tolerance = Decimal(str(settings.XRAY_WEIGHT_TOLERANCE))
    if abs(total_weight - Decimal('1')) > tolerance:
        result.errors.append(
            f'Total weight is {total_weight:.6f}, must be 1.0 within tolerance {tolerance}.'
        )
        result.is_valid = False

    result.rows = parsed_rows
    result.row_count = len(parsed_rows)
    result.total_weight = float(total_weight)
    return result
