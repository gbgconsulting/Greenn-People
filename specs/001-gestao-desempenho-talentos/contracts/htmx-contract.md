# Contract: HTMX e Formulários

**Apps**: `core` (helpers), todos os apps com interação parcial

## Detecção HTMX

```python
# apps/core/htmx.py

def is_htmx(request) -> bool:
    return request.headers.get('HX-Request') == 'true'

def htmx_response(request, full_template: str, partial_template: str, context: dict):
  template = partial_template if is_htmx(request) else full_template
  return render(request, template, context)
```

## Padrões de interação

### 1. Submissão de formulário sem reload

```html
<form hx-post="{% url 'pdi:action_create' pdi.pk %}"
      hx-target="#acao-list"
      hx-swap="innerHTML">
  {% csrf_token %}
  ...
</form>
```

**View**: `FormView` ou `CreateView`; em sucesso retorna partial `acao_list_partial.html`.

### 2. Atualização de status inline

```html
<button hx-post="{% url 'pdi:action_status' action.pk %}"
        hx-vals='{"status": "concluida"}'
        hx-target="#acao-{{ action.pk }}"
        hx-swap="outerHTML">
  Concluir
</button>
```

### 3. Modal de criação

```html
<button hx-get="{% url 'pdi:action_create_modal' pdi.pk %}"
        hx-target="#modal-container"
        hx-swap="innerHTML">
  Nova ação
</button>
```

**Partial**: `components/modal.html` wrapping o form.

## Formulários — validação

| Form | App | Regras principais |
|---|---|---|
| `RegisterForm` | accounts | E-mail `@greenn.com.br`; senha validators Django |
| `MetaForm` | goals | Bloqueio de edição fora da etapa permitida |
| `MetaProgressForm` | goals | `progresso` 0–100; só etapa `resultados` |
| `SelfAssessmentForm` | reviews | Notas dentro da escala da competência |
| `LeaderAssessmentForm` | reviews | Notas + comparação com `nivel_esperado_utilizado` |
| `AcaoPDIForm` | pdi | `prazo` >= today na criação |
| `ClassificacaoForm` | talent | `potencial` in (1, 2, 3) |

## Mensagens flash

- Sucesso/erro via `django.contrib.messages`.
- Em requests HTMX, incluir `HX-Trigger: showMessage` com payload JSON opcional para toast client-side (script mínimo em `base.html`).

## CSRF

- Todo `hx-post` inclui `{% csrf_token %}`.
- HTMX 2.x: configurar `hx-headers` global com token CSRF em `base.html`:

```html
<script>
  document.body.addEventListener('htmx:configRequest', (e) => {
    e.detail.headers['X-CSRFToken'] = '{{ csrf_token }}';
  });
</script>
```

## Componentes DTL reutilizáveis

| Partial | Path | Uso |
|---|---|---|
| Botão primário/secundário | `components/button.html` | `{% include %}` |
| Input com label | `components/input.html` | Forms |
| Card | `components/card.html` | Dashboards |
| Badge status | `components/badge_status.html` | PDI, aderência |
| Sidebar | `components/sidebar.html` | `base.html` |
| Topbar | `components/topbar.html` | `base.html` |

Parâmetros via `with`: `{% include "components/button.html" with label="Salvar" variant="primary" %}`.

## Paginação com HTMX

```html
<a hx-get="?page={{ page_obj.next_page_number }}"
   hx-target="#list-container"
   hx-swap="innerHTML">
  Próxima
</a>
```

View retorna partial da listagem com contexto paginado (`paginate_by=20`).
