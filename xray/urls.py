from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse, Http404
import os
from django.conf import settings


def serve_report(request, client):
    """Serve a client HTML report."""
    # Check in output dir for latest ZIP, or static reports
    report_path = os.path.join(settings.BASE_DIR, 'staticfiles', 'reports', f'{client}.html')
    if not os.path.exists(report_path):
        raise Http404(f'No report for client "{client}"')
    with open(report_path, 'r') as f:
        return HttpResponse(f.read(), content_type='text/html')


def report_index(request):
    """List available client reports."""
    reports_dir = os.path.join(settings.BASE_DIR, 'staticfiles', 'reports')
    reports = []
    if os.path.isdir(reports_dir):
        for fname in sorted(os.listdir(reports_dir)):
            if fname.endswith('.html'):
                client = fname.replace('.html', '')
                reports.append(client)
    html = '<html><body><h1>Portfolio X-Ray Reports</h1><ul>'
    for client in reports:
        html += f'<li><a href="/reports/{client}/">{client.title()}</a></li>'
    html += '</ul></body></html>'
    return HttpResponse(html)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    path('reports/', report_index, name='report-index'),
    path('reports/<str:client>/', serve_report, name='serve-report'),
]
