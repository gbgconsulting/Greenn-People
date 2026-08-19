from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def is_htmx(request: HttpRequest) -> bool:
    return request.headers.get('HX-Request') == 'true'


def htmx_response(
    request: HttpRequest,
    full_template: str,
    partial_template: str,
    context: dict,
) -> HttpResponse:
    template = partial_template if is_htmx(request) else full_template
    return render(request, template, context)
