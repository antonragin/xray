from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction

from refdata.models import (
    EconomicExposure, TaxProfile, IssuerType, Issuer, InstrumentTemplate,
)
from refdata.health import run_all_checks
from .serializers import (
    EconomicExposureSerializer, TaxProfileSerializer,
    IssuerTypeSerializer, IssuerSerializer, InstrumentTemplateSerializer,
)
from .filters import (
    EconomicExposureFilter, TaxProfileFilter, IssuerTypeFilter,
    IssuerFilter, InstrumentTemplateFilter,
)
from .schema_definition import SCHEMA


class ReferenceViewSetMixin:
    """Shared: idempotent POST, no DELETE, deactivation guard."""
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def create(self, request, *args, **kwargs):
        code_field = self.lookup_field
        code = request.data.get(code_field)
        if code:
            existing = self.get_queryset().filter(**{code_field: code}).first()
            if existing:
                serializer = self.get_serializer(existing)
                return Response(
                    {
                        'error': 'conflict',
                        'message': f'A record with {code_field}={code!r} already exists.',
                        'existing': serializer.data,
                    },
                    status=status.HTTP_409_CONFLICT,
                )
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if 'active' in request.data and request.data['active'] is False and instance.active:
            refs = self._check_references(instance)
            if refs:
                return Response(
                    {
                        'error': 'deactivation_blocked',
                        'message': f'Cannot deactivate: referenced by {len(refs)} active record(s).',
                        'references': refs,
                    },
                    status=status.HTTP_409_CONFLICT,
                )
        return super().partial_update(request, *args, **kwargs)

    def _check_references(self, instance):
        return []


class EconomicExposureViewSet(ReferenceViewSetMixin, viewsets.ModelViewSet):
    queryset = EconomicExposure.objects.all()
    serializer_class = EconomicExposureSerializer
    lookup_field = 'exposure_code'
    filterset_class = EconomicExposureFilter
    search_fields = ['exposure_code', 'name', 'description']
    ordering_fields = ['exposure_code', 'name', 'created_at', 'updated_at']
    ordering = ['exposure_code']

    def _check_references(self, instance):
        refs = []
        for t in InstrumentTemplate.objects.filter(active=True, primary_economic_exposure=instance):
            refs.append({'table': 'instrument_template', 'code': t.template_code, 'field': 'primary_economic_exposure'})
        for t in InstrumentTemplate.objects.filter(active=True, economic_exposure_weights_json__isnull=False):
            if instance.exposure_code in (t.economic_exposure_weights_json or {}):
                refs.append({'table': 'instrument_template', 'code': t.template_code, 'field': 'economic_exposure_weights_json'})
        return refs


class TaxProfileViewSet(ReferenceViewSetMixin, viewsets.ModelViewSet):
    queryset = TaxProfile.objects.all()
    serializer_class = TaxProfileSerializer
    lookup_field = 'tax_profile_code'
    filterset_class = TaxProfileFilter
    search_fields = ['tax_profile_code', 'name', 'description']
    ordering_fields = ['tax_profile_code', 'name', 'created_at', 'updated_at']
    ordering = ['tax_profile_code']

    def _check_references(self, instance):
        refs = []
        for t in InstrumentTemplate.objects.filter(active=True, tax_profile=instance):
            refs.append({'table': 'instrument_template', 'code': t.template_code, 'field': 'tax_profile'})
        return refs


class IssuerTypeViewSet(ReferenceViewSetMixin, viewsets.ModelViewSet):
    queryset = IssuerType.objects.all()
    serializer_class = IssuerTypeSerializer
    lookup_field = 'issuer_type_code'
    filterset_class = IssuerTypeFilter
    search_fields = ['issuer_type_code', 'name', 'description']
    ordering_fields = ['issuer_type_code', 'name', 'created_at', 'updated_at']
    ordering = ['issuer_type_code']

    def _check_references(self, instance):
        refs = []
        for i in Issuer.objects.filter(active=True, issuer_type=instance):
            refs.append({'table': 'issuer', 'code': i.issuer_code, 'field': 'issuer_type'})
        for t in InstrumentTemplate.objects.filter(active=True, primary_issuer_type=instance):
            refs.append({'table': 'instrument_template', 'code': t.template_code, 'field': 'primary_issuer_type'})
        for t in InstrumentTemplate.objects.filter(active=True, issuer_type_weights_json__isnull=False):
            if instance.issuer_type_code in (t.issuer_type_weights_json or {}):
                refs.append({'table': 'instrument_template', 'code': t.template_code, 'field': 'issuer_type_weights_json'})
        return refs


class IssuerViewSet(ReferenceViewSetMixin, viewsets.ModelViewSet):
    queryset = Issuer.objects.select_related('issuer_type').all()
    serializer_class = IssuerSerializer
    lookup_field = 'issuer_code'
    filterset_class = IssuerFilter
    search_fields = ['issuer_code', 'name', 'description']
    ordering_fields = ['issuer_code', 'name', 'created_at', 'updated_at']
    ordering = ['issuer_code']

    def _check_references(self, instance):
        refs = []
        for t in InstrumentTemplate.objects.filter(active=True, issuer=instance):
            refs.append({'table': 'instrument_template', 'code': t.template_code, 'field': 'issuer'})
        return refs


class InstrumentTemplateViewSet(ReferenceViewSetMixin, viewsets.ModelViewSet):
    queryset = InstrumentTemplate.objects.select_related(
        'primary_economic_exposure', 'tax_profile', 'primary_issuer_type', 'issuer',
    ).all()
    serializer_class = InstrumentTemplateSerializer
    lookup_field = 'template_code'
    filterset_class = InstrumentTemplateFilter
    search_fields = ['template_code', 'short_name', 'long_name', 'cnpj']
    ordering_fields = ['template_code', 'short_name', 'created_at', 'updated_at']
    ordering = ['template_code']


class SchemaView(APIView):
    def get(self, request):
        return Response(SCHEMA)


VALID_ANGLES = ['diversification', 'liquidity', 'fees', 'tax', 'risk', 'performance']
TABLE_MAP = {
    'economic_exposure': (EconomicExposure, 'exposure_code'),
    'tax_profile': (TaxProfile, 'tax_profile_code'),
    'issuer_type': (IssuerType, 'issuer_type_code'),
    'issuer': (Issuer, 'issuer_code'),
    'instrument_template': (InstrumentTemplate, 'template_code'),
}


class BatchInstructionView(APIView):
    def patch(self, request):
        angle = request.data.get('angle')
        updates = request.data.get('updates', [])

        if angle not in VALID_ANGLES:
            return Response(
                {'error': 'validation_error', 'message': f'Invalid angle. Must be one of: {VALID_ANGLES}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not updates:
            return Response(
                {'error': 'validation_error', 'message': 'No updates provided.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        field_name = f'instructions_{angle}'
        errors = []
        resolved = []

        for i, entry in enumerate(updates):
            table_name = entry.get('table')
            code = entry.get('code')
            text = entry.get('text')

            if table_name not in TABLE_MAP:
                errors.append({'index': i, 'table': table_name, 'code': code,
                               'error': f'Invalid table. Valid: {list(TABLE_MAP.keys())}'})
                continue

            model_class, code_field = TABLE_MAP[table_name]
            obj = model_class.objects.filter(**{code_field: code}).first()
            if not obj:
                errors.append({'index': i, 'table': table_name, 'code': code,
                               'error': f'No {table_name} with code {code!r}.'})
                continue

            resolved.append((obj, field_name, text if text is not None else ''))

        if errors:
            return Response(
                {'error': 'validation_error',
                 'message': f'{len(errors)} of {len(updates)} failed. No changes applied.',
                 'details': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            results = []
            for obj, fn, text in resolved:
                setattr(obj, fn, text)
                obj.save(update_fields=[fn, 'updated_at'])
                code_field = TABLE_MAP[obj._meta.db_table][1]
                results.append({'table': obj._meta.db_table, 'code': getattr(obj, code_field), 'status': 'updated'})

        return Response({'angle': angle, 'updated': len(results), 'results': results})


class ReferenceHealthView(APIView):
    def get(self, request):
        checks = run_all_checks()
        overall = 'pass'
        for c in checks:
            if c.get('severity') == 'error' and c.get('items'):
                overall = 'fail'
                break
        return Response({'checks': checks, 'overall': overall})


class LoadFixtureView(APIView):
    """Load the production_seed fixture into the database.
    POST /api/v1/admin/load-fixture/
    """
    def post(self, request):
        from django.core.management import call_command
        import io
        out = io.StringIO()
        try:
            call_command('loaddata', 'production_seed', stdout=out, verbosity=1)
            return Response({'status': 'ok', 'message': out.getvalue().strip()})
        except Exception as e:
            return Response(
                {'error': 'load_failed', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ProcessPortfolioView(APIView):
    """Process a portfolio CSV and return the full bundle as JSON.

    POST /api/v1/process/
    Body: {"csv": "instrument_template_code,weight,...\\n..."} or multipart file upload
    Returns: full report_input_bundle.json content + angle-specific data
    """
    def post(self, request):
        import io
        from processing.service import process_portfolio
        from processing.validators import validate_csv
        from processing.resolver import resolve_positions
        from processing.allocations import compute_allocations, compute_coverage
        from processing.bundler import _unrolled_json, _report_input_bundle

        # Accept CSV as text in body or as file upload
        csv_text = request.data.get('csv', '')
        if not csv_text and request.FILES.get('file'):
            raw = request.FILES['file'].read()
            csv_text = raw.decode('utf-8') if isinstance(raw, bytes) else raw

        if not csv_text:
            return Response(
                {'error': 'validation_error', 'message': 'Provide CSV as "csv" field or file upload.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate
        csv_file = io.StringIO(csv_text)
        validation = validate_csv(csv_file)
        if not validation.is_valid:
            return Response(
                {'error': 'validation_error', 'errors': validation.errors, 'warnings': validation.warnings},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve
        from datetime import date
        upload_date = date.today()
        positions = resolve_positions(validation.rows, upload_date)
        allocations = compute_allocations(positions)
        coverage = compute_coverage(positions)

        from processing.bundler import generate_run_id
        run_id = generate_run_id()

        # Build the full bundle
        bundle = _report_input_bundle(run_id, upload_date, positions, allocations, coverage)

        # Add angle-specific data
        angles = {}
        for angle in VALID_ANGLES:
            angle_data = []
            for p in positions:
                angle_data.append({
                    'row_number': p.row_number,
                    'template_code': p.template_code,
                    'weight': float(p.weight),
                    'instrument_kind': p.instrument_kind,
                    'instructions': p.instructions.get(angle, []),
                })
            angles[angle] = angle_data

        return Response({
            'run_id': run_id,
            'validation': {
                'is_valid': True,
                'warnings': validation.warnings,
                'row_count': validation.row_count,
            },
            'bundle': bundle,
            'angles': angles,
        })


class ProcessPortfolioFullView(APIView):
    """Process a portfolio CSV and return the ZIP bundle for download.

    POST /api/v1/process/zip/
    Body: {"csv": "instrument_template_code,weight,...\\n..."}
    Returns: ZIP file download
    """
    def post(self, request):
        import io
        from django.http import FileResponse
        from processing.service import process_portfolio

        csv_text = request.data.get('csv', '')
        if not csv_text and request.FILES.get('file'):
            raw = request.FILES['file'].read()
            csv_text = raw.decode('utf-8') if isinstance(raw, bytes) else raw

        if not csv_text:
            return Response(
                {'error': 'validation_error', 'message': 'Provide CSV as "csv" field or file upload.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        csv_file = io.StringIO(csv_text)
        result = process_portfolio(csv_file)

        if not result.success:
            return Response(
                {'error': 'processing_error', 'errors': result.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return FileResponse(
            open(result.zip_path, 'rb'),
            as_attachment=True,
            filename=f'{result.run_id}.zip',
        )
