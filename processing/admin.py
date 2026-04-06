from django.contrib import admin
from django.urls import path
from django.template.response import TemplateResponse
from django.http import FileResponse, HttpResponseRedirect
from django.contrib import messages

from refdata.health import run_all_checks


def get_processing_urls(admin_site):
    """Return custom admin URLs for processing and health."""
    return [
        path(
            'processing/upload/',
            admin_site.admin_view(upload_csv_view),
            name='processing_upload',
        ),
        path(
            'processing/download/<str:run_id>/',
            admin_site.admin_view(download_bundle_view),
            name='processing_download',
        ),
        path(
            'refdata-health/',
            admin_site.admin_view(health_dashboard_view),
            name='refdata_health',
        ),
    ]


def upload_csv_view(request):
    result = None
    errors = None
    if request.method == 'POST' and request.FILES.get('csv_file'):
        try:
            from processing.service import process_portfolio_from_upload
            result = process_portfolio_from_upload(request.FILES['csv_file'])
        except Exception as e:
            errors = [str(e)]
    context = {
        **admin.site.each_context(request),
        'title': 'Portfolio Processing',
        'result': result,
        'errors': errors,
    }
    return TemplateResponse(request, 'processing/upload.html', context)


def download_bundle_view(request, run_id):
    import os
    from django.conf import settings
    bundle_path = os.path.join(settings.XRAY_OUTPUT_DIR, f'{run_id}.zip')
    if os.path.exists(bundle_path):
        return FileResponse(
            open(bundle_path, 'rb'),
            as_attachment=True,
            filename=f'{run_id}.zip',
        )
    messages.error(request, f'Bundle {run_id} not found.')
    return HttpResponseRedirect('/admin/processing/upload/')


def health_dashboard_view(request):
    checks = run_all_checks()
    context = {
        **admin.site.each_context(request),
        'title': 'Reference Data Health',
        'checks': checks,
    }
    return TemplateResponse(request, 'processing/health_dashboard.html', context)


# Inject custom URLs into the default admin site
_original_get_urls = admin.AdminSite.get_urls


def _patched_get_urls(self):
    custom = get_processing_urls(self)
    return custom + _original_get_urls(self)


admin.AdminSite.get_urls = _patched_get_urls
