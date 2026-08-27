from __future__ import annotations

from django import forms
from django.utils.html import format_html, format_html_join


class ScaleRatingWidget(forms.Widget):
    """Botões de nota discretos (escala inteira pequena)."""

    def __init__(self, *, min_value: int, max_value: int, **kwargs):
        self.min_value = min_value
        self.max_value = max_value
        super().__init__(**kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        input_id = attrs.get('id', f'id_{name}')
        selected = ''
        if value is not None and value != '':
            try:
                selected = str(int(value))
            except (TypeError, ValueError):
                selected = str(value)

        disabled = attrs.get('disabled', False)
        options = []
        for option in range(self.min_value, self.max_value + 1):
            option_id = f'{input_id}_{option}'
            is_checked = selected == str(option)
            options.append(
                format_html(
                    '<div class="relative">'
                    '<input type="radio" name="{}" value="{}" id="{}"'
                    ' class="rating-radio sr-only"{}{}>'
                    '<label for="{}" class="rating-radio-label">{}</label>'
                    '</div>',
                    name,
                    option,
                    option_id,
                    ' checked' if is_checked else '',
                    ' disabled' if disabled else '',
                    option_id,
                    option,
                ),
            )

        return format_html(
            '<div class="flex flex-wrap gap-3" role="radiogroup"'
            ' aria-label="Autoavaliação">{}</div>',
            format_html_join('', '{}', ((option,) for option in options)),
        )
