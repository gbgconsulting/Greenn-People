from django.db import connection
from django.http import HttpRequest, JsonResponse


def health(request: HttpRequest) -> JsonResponse:
    """GET /health/ — checagem leve de prontidão (DB SELECT 1). Sem autenticação."""
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
