from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse, Http404
from django.conf import settings
import os
import base64


def _check_basic_auth(request):
    """Check for Basic auth or token query param. Returns True if authorized."""
    # Check query param
    token = request.GET.get('token', '')
    if token == settings.XRAY_API_TOKEN:
        return True

    # Check Basic auth (username ignored, password = token)
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if auth.startswith('Basic '):
        try:
            decoded = base64.b64decode(auth[6:]).decode('utf-8')
            _, password = decoded.split(':', 1)
            if password == settings.XRAY_API_TOKEN:
                return True
        except Exception:
            pass

    # Check Bearer token
    if auth.startswith('Bearer ') and auth[7:].strip() == settings.XRAY_API_TOKEN:
        return True

    return False


def _require_auth(view_func):
    """Decorator requiring auth for web views."""
    def wrapped(request, *args, **kwargs):
        if _check_basic_auth(request):
            return view_func(request, *args, **kwargs)
        response = HttpResponse('Authentication required.', status=401)
        response['WWW-Authenticate'] = 'Basic realm="X-Ray"'
        return response
    return wrapped


@_require_auth
def serve_report(request, client):
    report_path = os.path.join(settings.BASE_DIR, 'staticfiles', 'reports', f'{client}.html')
    if not os.path.exists(report_path):
        raise Http404(f'No report for client "{client}"')
    with open(report_path, 'r') as f:
        return HttpResponse(f.read(), content_type='text/html')


@_require_auth
def report_index(request):
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
