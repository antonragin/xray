import os
import tempfile
from datetime import date
from dataclasses import dataclass
from typing import Optional

from django.conf import settings

from .validators import validate_csv
from .resolver import resolve_positions
from .allocations import compute_allocations, compute_coverage
from .charts import generate_all_charts
from .html_preview import generate_html_preview
from .bundler import build_bundle, write_zip, generate_run_id


@dataclass
class ProcessingResult:
    success: bool
    run_id: Optional[str] = None
    zip_path: Optional[str] = None
    row_count: int = 0
    errors: list = None
    warnings: list = None
    html_preview_url: Optional[str] = None


def process_portfolio(csv_input, output_dir=None, upload_date=None):
    """Main entry point. Returns ProcessingResult."""
    if output_dir is None:
        output_dir = settings.XRAY_OUTPUT_DIR
    if upload_date is None:
        upload_date = date.today()

    # 1. Validate
    validation = validate_csv(csv_input)
    if not validation.is_valid:
        return ProcessingResult(
            success=False, errors=validation.errors, warnings=validation.warnings,
        )

    # 2. Resolve
    positions = resolve_positions(validation.rows, upload_date)

    # 3. Allocations
    allocations = compute_allocations(positions)
    coverage = compute_coverage(positions)

    # 4. Charts
    run_id = generate_run_id()
    charts_dir = os.path.join(tempfile.mkdtemp(), 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    generate_all_charts(allocations, charts_dir)

    # 5. HTML preview
    html_content = generate_html_preview(
        run_id, upload_date, validation, positions, allocations, coverage, charts_dir,
    )

    # 6. Read original CSV content
    if isinstance(csv_input, str):
        with open(csv_input, 'r') as f:
            original_csv = f.read()
    elif hasattr(csv_input, 'seek'):
        csv_input.seek(0)
        raw = csv_input.read()
        original_csv = raw.decode('utf-8') if isinstance(raw, bytes) else raw
    else:
        original_csv = ''

    # 7. Build bundle
    files = build_bundle(
        run_id, upload_date, original_csv, validation,
        positions, allocations, coverage, charts_dir, html_content,
    )

    # 8. Write ZIP
    zip_path = os.path.join(output_dir, f'{run_id}.zip')
    write_zip(files, zip_path)

    return ProcessingResult(
        success=True,
        run_id=run_id,
        zip_path=zip_path,
        row_count=len(positions),
        errors=[],
        warnings=validation.warnings,
    )


def process_portfolio_from_upload(uploaded_file):
    """Wrapper for Django admin upload. Returns dict for template context."""
    result = process_portfolio(uploaded_file)
    if not result.success:
        raise ValueError('; '.join(result.errors))
    return {
        'run_id': result.run_id,
        'row_count': result.row_count,
        'zip_path': result.zip_path,
    }
