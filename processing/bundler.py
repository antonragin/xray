import csv
import io
import json
import os
import zipfile
from datetime import date, datetime
from uuid import uuid4

from .resolver import flatten_instructions


def build_bundle(run_id, upload_date, original_csv_content, validation_result,
                 positions, allocations, coverage, charts_dir, html_content):
    """Assemble the output bundle as a dict of {relative_path: content_bytes}."""
    files = {}

    # input/original.csv
    files[f'{run_id}/input/original.csv'] = _to_bytes(original_csv_content)

    # machine/unrolled_positions.csv
    files[f'{run_id}/machine/unrolled_positions.csv'] = _to_bytes(
        _unrolled_csv(positions)
    )

    # machine/unrolled_positions.json
    files[f'{run_id}/machine/unrolled_positions.json'] = _to_bytes(
        json.dumps(_unrolled_json(positions), indent=2, ensure_ascii=False, sort_keys=True)
    )

    # machine/allocation CSVs
    for alloc_name, alloc_data in allocations.items():
        csv_name = f'allocation_{alloc_name}.csv'
        files[f'{run_id}/machine/{csv_name}'] = _to_bytes(_allocation_csv(alloc_data))

    # machine/angle CSVs
    for angle in ['diversification', 'liquidity', 'fees', 'tax', 'risk', 'performance']:
        files[f'{run_id}/machine/angle_{angle}.csv'] = _to_bytes(
            _angle_csv(positions, angle)
        )

    # machine/report_input_bundle.json
    bundle = _report_input_bundle(run_id, upload_date, positions, allocations, coverage)
    files[f'{run_id}/machine/report_input_bundle.json'] = _to_bytes(
        json.dumps(bundle, indent=2, ensure_ascii=False, sort_keys=True)
    )

    # machine/coverage_summary.json
    files[f'{run_id}/machine/coverage_summary.json'] = _to_bytes(
        json.dumps(coverage, indent=2, sort_keys=True)
    )

    # html/preview.html
    files[f'{run_id}/html/preview.html'] = _to_bytes(html_content)

    # charts/*.svg
    if os.path.isdir(charts_dir):
        for fname in os.listdir(charts_dir):
            if fname.endswith('.svg'):
                with open(os.path.join(charts_dir, fname), 'rb') as f:
                    files[f'{run_id}/charts/{fname}'] = f.read()

    # meta/run_metadata.json
    meta = {
        'run_id': run_id,
        'upload_date': str(upload_date),
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'row_count': len(positions),
        'total_weight': sum(float(p.weight) for p in positions),
    }
    files[f'{run_id}/meta/run_metadata.json'] = _to_bytes(
        json.dumps(meta, indent=2, sort_keys=True)
    )

    # meta/validation.json
    val = {
        'is_valid': validation_result.is_valid,
        'errors': validation_result.errors,
        'warnings': validation_result.warnings,
        'row_count': validation_result.row_count,
        'total_weight': validation_result.total_weight,
    }
    files[f'{run_id}/meta/validation.json'] = _to_bytes(
        json.dumps(val, indent=2, sort_keys=True)
    )

    return files


def write_zip(files, output_path):
    """Write a dict of {path: bytes} to a ZIP file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for path, data in sorted(files.items()):
            zf.writestr(path, data)
    return output_path


def generate_run_id():
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    short = uuid4().hex[:6]
    return f'run_{ts}_{short}'


def _to_bytes(text):
    return text.encode('utf-8') if isinstance(text, str) else text


def _unrolled_csv(positions):
    out = io.StringIO()
    writer = csv.writer(out)
    header = [
        'row_number', 'template_code', 'display_name', 'weight', 'instrument_kind',
        'tax_profile_code', 'tax_profile_name',
        'issuer_code', 'issuer_name', 'issuer_type_code', 'issuer_type_name',
        'economic_exposures', 'expiry_date', 'days_to_expiry',
        'years_to_expiry', 'maturity_bucket', 'country_bucket',
        'instructions_diversification', 'instructions_liquidity',
        'instructions_fees', 'instructions_tax',
        'instructions_risk', 'instructions_performance',
    ]
    writer.writerow(header)
    for p in positions:
        exp_str = '; '.join(
            f"{e['code']}({e.get('name', e['code'])}):{e['weight']}"
            for e in p.economic_exposures
        )
        writer.writerow([
            p.row_number, p.template_code, p.display_name, f"{float(p.weight):.6f}",
            p.instrument_kind,
            p.tax_profile_code, p.tax_profile_name,
            p.issuer_code or '', p.issuer_name or '',
            p.issuer_type_code or '', p.issuer_type_name or '',
            exp_str, p.expiry_date or '', p.days_to_expiry or '',
            p.years_to_expiry or '', p.maturity_bucket or '', p.country_bucket or '',
            flatten_instructions(p.instructions.get('diversification', [])),
            flatten_instructions(p.instructions.get('liquidity', [])),
            flatten_instructions(p.instructions.get('fees', [])),
            flatten_instructions(p.instructions.get('tax', [])),
            flatten_instructions(p.instructions.get('risk', [])),
            flatten_instructions(p.instructions.get('performance', [])),
        ])
    return out.getvalue()


def _unrolled_json(positions):
    result = []
    for p in positions:
        result.append({
            'row_number': p.row_number,
            'input': {
                'instrument_template_code': p.template_code,
                'weight': float(p.weight),
            },
            'resolved': {
                'instrument_kind': p.instrument_kind,
                'short_name': p.short_name,
                'display_name': p.display_name,
                'tax_profile_code': p.tax_profile_code,
                'tax_profile_name': p.tax_profile_name,
                'issuer_code': p.issuer_code,
                'issuer_name': p.issuer_name,
                'issuer_type_code': p.issuer_type_code,
                'issuer_type_name': p.issuer_type_name,
                'economic_exposures': p.economic_exposures,
                'issuer_type_weights': p.issuer_type_weights,
            },
            'derived': {
                'expiry_date': str(p.expiry_date) if p.expiry_date else None,
                'days_to_expiry': p.days_to_expiry,
                'years_to_expiry': p.years_to_expiry,
                'maturity_bucket': p.maturity_bucket,
                'country_bucket': p.country_bucket,
            },
            'template_metadata': p.template_metadata,
            'instructions': p.instructions,
        })
    return result


def _allocation_csv(alloc_data):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(['code', 'name', 'weight', 'pct'])
    for d in alloc_data:
        writer.writerow([d['code'], d.get('name', d['code']), f"{d['weight']:.6f}", f"{d['weight'] * 100:.2f}"])
    return out.getvalue()


def _angle_csv(positions, angle):
    """Generate angle-specific CSV with relevant columns."""
    out = io.StringIO()
    writer = csv.writer(out)

    base_cols = ['row_number', 'template_code', 'display_name', 'weight', 'instrument_kind']

    if angle == 'diversification':
        extra_cols = ['issuer_code', 'issuer_type_code', 'economic_exposures', 'country_bucket']
    elif angle == 'liquidity':
        extra_cols = ['expiry_date', 'days_to_expiry', 'maturity_bucket', 'has_fgc']
    elif angle == 'fees':
        extra_cols = ['yearly_fee_pct', 'performance_fee_pct', 'tax_profile_code']
    elif angle == 'tax':
        extra_cols = ['tax_profile_code', 'expiry_date', 'days_to_expiry']
    elif angle == 'risk':
        extra_cols = ['economic_exposures', 'maturity_bucket', 'issuer_code', 'issuer_type_code', 'country_bucket']
    elif angle == 'performance':
        extra_cols = ['economic_exposures', 'maturity_bucket', 'years_to_expiry']
    else:
        extra_cols = []

    header = base_cols + extra_cols + [f'instructions_{angle}']
    writer.writerow(header)

    for p in positions:
        row = [p.row_number, p.template_code, p.display_name, f"{float(p.weight):.6f}", p.instrument_kind]

        for col in extra_cols:
            if col == 'economic_exposures':
                row.append('; '.join(f"{e['code']}:{e['weight']}" for e in p.economic_exposures))
            elif col == 'has_fgc':
                row.append(p.template_metadata.get('has_fgc', ''))
            elif col in ('yearly_fee_pct', 'performance_fee_pct'):
                val = p.template_metadata.get(col)
                row.append(f"{val:.4f}" if val is not None else '')
            else:
                row.append(getattr(p, col, '') or '')

        row.append(flatten_instructions(p.instructions.get(angle, [])))
        writer.writerow(row)

    return out.getvalue()


def _report_input_bundle(run_id, upload_date, positions, allocations, coverage):
    return {
        'schema_version': '1.0',
        'system_type': 'mechanical_precursor',
        'run_id': run_id,
        'upload_date': str(upload_date),
        'input_contract': 'instrument_template_code,weight,expiry_date,issuer_code,issuer_type_code',
        'portfolio_summary': {
            'total_weight': round(sum(float(p.weight) for p in positions), 6),
            'row_count': len(positions),
            'unique_templates': len(set(p.template_code for p in positions)),
            **coverage,
        },
        'allocations': {
            k.replace('by_', ''): v for k, v in allocations.items()
        },
        'positions': _unrolled_json(positions),
    }
