import secrets

from django.conf import settings
from django.db import connection
from django.http import HttpRequest, JsonResponse


def health(request: HttpRequest) -> JsonResponse:
    """GET /health/ — checagem leve de prontidão (DB SELECT 1).

    Se ``HEALTH_CHECK_TOKEN`` estiver definido, exige header ``X-Health-Token``
    ou query ``?token=`` com o mesmo valor (mitiga exposição pública).
    """
    token = getattr(settings, 'HEALTH_CHECK_TOKEN', '') or ''
    if token:
        provided = request.headers.get('X-Health-Token') or request.GET.get(
            'token',
            '',
        )
        if not provided or not secrets.compare_digest(provided, token):
            return JsonResponse({'status': 'error'}, status=404)

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        return JsonResponse(
            {'status': 'error', 'database': 'error'},
            status=503,
        )
    return JsonResponse({'status': 'ok', 'database': 'ok'})
