/**
 * Matriz 9-box interativa — HTML5 DnD + feedback do drawer (SC-004).
 * Carregado só em templates/talent/matrix.html (extra_js).
 *
 * T017: loading (aria-busy + indicadores), erros PT-BR, preservar DOM em falha.
 * T020: DnD dragstart/drop + POST move; Esc/fora → zero POST + restore visual.
 * T021: snap R4 — card em (desempenho_derivado, P′); toast se linha incompatível.
 * T022: erro 403/400/rede/5xx → restore posição + toast; nunca sucesso silencioso.
 * Gates mobile (T023); a11y drawer: T027.
 *
 * Convenção DOM:
 *   #ninebox-matrix — grade com data-ciclo-id / data-move-url-template / data-admin
 *   #matrix-drawer — painel lateral HTMX (swap target)
 *   #matrix-drawer-indicator — indicador local (fora do swap)
 *   [data-user-pk] nos cards; células #cell-{desempenho}-{potencial}
 */
(function () {
  'use strict';

  var DRAWER_ID = 'matrix-drawer';
  var MATRIX_ID = 'ninebox-matrix';
  /** Touch / coarse pointer — DnD inadequado (FR-010 / research R5). */
  var MQ_POINTER_COARSE = '(pointer: coarse)';
  /** Viewport estreito (abaixo do breakpoint md Tailwind). */
  var MQ_NARROW_VIEWPORT = '(max-width: 767px)';
  var MSG_REDE =
    'Não foi possível completar a ação. Verifique a conexão e tente novamente.';
  var MSG_PERMISSAO = 'Você não tem permissão para esta ação.';
  var MSG_SERVIDOR = 'Ocorreu um erro no servidor. Tente novamente.';

  function getDrawer() {
    return document.getElementById(DRAWER_ID);
  }

  function getMatrixRoot() {
    return document.getElementById(MATRIX_ID);
  }

  function isMatrixSwapTarget(el) {
    return !!(el && el.id === DRAWER_ID);
  }

  function isMatrixRequestEvent(evt) {
    var detail = evt.detail || {};
    var target = detail.target;
    var elt = detail.elt;
    if (isMatrixSwapTarget(target)) {
      return true;
    }
    if (elt && elt.closest) {
      if (elt.closest('#' + DRAWER_ID)) {
        return true;
      }
      if (elt.getAttribute && elt.getAttribute('hx-target') === '#' + DRAWER_ID) {
        return true;
      }
      if (elt.closest('[aria-controls="' + DRAWER_ID + '"]')) {
        return true;
      }
    }
    return false;
  }

  function setDrawerBusy(busy) {
    var drawer = getDrawer();
    if (!drawer) {
      return;
    }
    drawer.setAttribute('aria-busy', busy ? 'true' : 'false');
    drawer.classList.toggle('opacity-60', !!busy);
    drawer.classList.toggle('pointer-events-none', !!busy);
  }

  function showToast(message, level) {
    if (!message) {
      return;
    }
    document.body.dispatchEvent(
      new CustomEvent('showMessage', {
        detail: { message: message, level: level || 'error' },
      }),
    );
  }

  function messageForStatus(status) {
    if (status === 0) {
      return MSG_REDE;
    }
    if (status === 403 || status === 401) {
      return MSG_PERMISSAO;
    }
    if (status >= 500) {
      return MSG_SERVIDOR;
    }
    if (status >= 400) {
      return 'Não foi possível salvar. Verifique os dados e tente novamente.';
    }
    return MSG_REDE;
  }

  function triggerAlreadyHasMessage(xhr) {
    if (!xhr) {
      return false;
    }
    var raw = xhr.getResponseHeader('HX-Trigger');
    if (!raw) {
      return false;
    }
    try {
      var parsed = JSON.parse(raw);
      return !!(parsed && parsed.showMessage);
    } catch (err) {
      return raw.indexOf('showMessage') !== -1;
    }
  }

  /**
   * T023 / FR-010: DnD desligado em pointer coarse ou viewport estreito.
   * Drawer permanece o caminho completo de calibração.
   */
  function isDragDisabled() {
    if (typeof window.matchMedia !== 'function') {
      return false;
    }
    return (
      window.matchMedia(MQ_POINTER_COARSE).matches ||
      window.matchMedia(MQ_NARROW_VIEWPORT).matches
    );
  }

  /**
   * Aplica gates client-side: só cards com data-dnd-capable (admin no template)
   * ficam draggable, e só quando o ambiente permite DnD.
   */
  function applyDragGates(root) {
    root = root || getMatrixRoot();
    if (!root) {
      return;
    }
    var isAdmin = root.getAttribute('data-admin') === '1';
    var disabled = !isAdmin || isDragDisabled();
    root.setAttribute('data-dnd-enabled', disabled ? '0' : '1');

    root.querySelectorAll('[data-user-pk]').forEach(function (card) {
      var capable = card.getAttribute('data-dnd-capable') === '1';
      if (!capable || disabled) {
        card.setAttribute('draggable', 'false');
        card.classList.remove('cursor-grab', 'active:cursor-grabbing');
        return;
      }
      card.setAttribute('draggable', 'true');
      card.classList.add('cursor-grab', 'active:cursor-grabbing');
    });
  }

  function bindMediaQueryChange(query, handler) {
    if (typeof window.matchMedia !== 'function') {
      return;
    }
    var mql = window.matchMedia(query);
    if (mql.addEventListener) {
      mql.addEventListener('change', handler);
    } else if (mql.addListener) {
      mql.addListener(handler);
    }
  }

  /**
   * HTML5 DnD (T020) + política de snap R4 (T021) + revert on error (T022).
   * Drop → POST só com potencial da coluna; card final via OOB em
   * (desempenho_derivado, P′) — nunca permanece na linha incompatível.
   * Linha incompatível → toast servidor (“Só o potencial é alterado…”).
   * Erro 403/400/rede/5xx → restore posição anterior + toast; sem sucesso silencioso.
   * Gates mobile/admin (T023): applyDragGates + checks em dragstart.
   */
  function initDragAndDrop() {
    var root = getMatrixRoot();
    if (!root || root.getAttribute('data-admin') !== '1') {
      return;
    }
    if (typeof htmx === 'undefined') {
      return;
    }

    var dragState = null;
    /**
     * Move em voo (T022): origem visual até OOB de sucesso ou restore em erro.
     * @type {{card: Element, userPk: string, potencial: string, desempenho: string, originCell: Element|null}|null}
     */
    var pendingMove = null;
    /** Highlight quando a linha do drop = desempenho derivado. */
    var DROP_HL = 'ring-2 ring-emerald-400 ring-inset';
    /** Highlight quando haverá snap de linha (só potencial muda). */
    var SNAP_HL = 'ring-2 ring-amber-400 ring-inset';
    var ALL_HL = (DROP_HL + ' ' + SNAP_HL).split(/\s+/);

    function clearDropHighlight() {
      root.querySelectorAll('[id^="cell-"]').forEach(function (cell) {
        ALL_HL.forEach(function (cls) {
          cell.classList.remove(cls);
        });
        cell.removeAttribute('data-drop-snap');
      });
    }

    function willSnapToCell(cell) {
      if (!dragState || !cell) {
        return false;
      }
      return (
        String(cell.getAttribute('data-desempenho')) !==
        String(dragState.desempenho)
      );
    }

    function setDropHighlight(cell, on) {
      if (!cell) {
        return;
      }
      ALL_HL.forEach(function (cls) {
        cell.classList.remove(cls);
      });
      cell.removeAttribute('data-drop-snap');
      if (!on) {
        return;
      }
      var snap = willSnapToCell(cell);
      var classes = (snap ? SNAP_HL : DROP_HL).split(/\s+/);
      classes.forEach(function (cls) {
        cell.classList.add(cls);
      });
      if (snap) {
        cell.setAttribute('data-drop-snap', '1');
      }
    }

    function resetDragVisual(card) {
      if (!card) {
        return;
      }
      card.classList.remove('opacity-40');
      card.removeAttribute('aria-grabbed');
      card.removeAttribute('aria-busy');
    }

    function setPendingVisual(card, on) {
      if (!card) {
        return;
      }
      card.classList.toggle('opacity-40', !!on);
      if (on) {
        card.setAttribute('aria-busy', 'true');
      } else {
        card.removeAttribute('aria-busy');
      }
    }

    function buildMoveUrl(userPk) {
      var tmpl = root.getAttribute('data-move-url-template') || '';
      return tmpl.replace('999999999', String(userPk));
    }

    function findCardByUserPk(userPk) {
      return root.querySelector('[data-user-pk="' + String(userPk) + '"]');
    }

    function restoreCardToOrigin(state) {
      if (!state) {
        return;
      }
      var card = findCardByUserPk(state.userPk) || state.card;
      if (!card) {
        return;
      }
      resetDragVisual(card);
      card.setAttribute('data-potencial', String(state.potencial));
      card.setAttribute('data-desempenho', String(state.desempenho));

      var originCell = state.originCell;
      if (!originCell || !originCell.isConnected) {
        return;
      }
      var list = originCell.querySelector('ul');
      if (list && card.parentElement !== list) {
        list.appendChild(card);
      }
    }

    /**
     * T022 / SC-004: restore + toast erro; idempotente (afterRequest + responseError).
     * Se o servidor já enviou HX-Trigger showMessage, não duplica o toast.
     */
    function failPendingMove(xhr) {
      if (!pendingMove) {
        return;
      }
      var state = pendingMove;
      pendingMove = null;
      restoreCardToOrigin(state);
      if (triggerAlreadyHasMessage(xhr)) {
        return;
      }
      var status = xhr ? xhr.status : 0;
      showToast(messageForStatus(status), 'error');
    }

    function clearPendingMoveSuccess() {
      if (!pendingMove) {
        return;
      }
      // OOB substitui células; limpa só o estado em voo (card antigo some do DOM).
      pendingMove = null;
    }

    function isMoveRequestEvent(evt) {
      var detail = evt.detail || {};
      var pathInfo = detail.pathInfo || {};
      var path = pathInfo.requestPath || '';
      if (!path && detail.xhr && detail.xhr.responseURL) {
        path = detail.xhr.responseURL;
      }
      if (path.indexOf('/talent/matrix/move/') !== -1) {
        return true;
      }
      // Fallback: request em voo cujo target é a grade.
      if (pendingMove && detail.target === root) {
        return true;
      }
      return false;
    }

    function cancelDrag() {
      if (!dragState) {
        return;
      }
      dragState.cancelled = true;
      resetDragVisual(dragState.card);
      clearDropHighlight();
    }

    /** Encerra drag em curso (gate mobile / media change) sem POST. */
    function abortActiveDrag() {
      if (!dragState) {
        return;
      }
      resetDragVisual(dragState.card);
      clearDropHighlight();
      dragState = null;
    }

    function postMove(userPk, potencial, desempenhoCelulaAlvo) {
      var values = {
        ciclo_id: root.getAttribute('data-ciclo-id') || '',
        potencial: String(potencial),
        // desempenho da célula sob o cursor: só para o servidor detectar snap;
        // NÃO muta desempenho (contrato drag-persist / R4).
        desempenho: String(desempenhoCelulaAlvo),
      };
      var areaId = root.getAttribute('data-area-id');
      var cargoId = root.getAttribute('data-cargo-id');
      if (areaId) {
        values.area = areaId;
      }
      if (cargoId) {
        values.cargo = cargoId;
      }

      // swap none: OOB posiciona em (D_derivado, P′); HX-Trigger → toast (snap/sucesso).
      // Erro → failPendingMove (T022); sem swap de HTML de erro na grade.
      htmx.ajax('POST', buildMoveUrl(userPk), {
        target: root,
        swap: 'none',
        values: values,
      });
    }

    root.addEventListener('dragstart', function (evt) {
      var card = evt.target.closest('[data-user-pk]');
      if (!card || !root.contains(card)) {
        return;
      }
      // T023: nunca inicia drag se gate mobile/coarse ou card sem capable.
      if (
        isDragDisabled() ||
        root.getAttribute('data-dnd-enabled') !== '1' ||
        card.getAttribute('data-dnd-capable') !== '1' ||
        card.getAttribute('draggable') !== 'true'
      ) {
        evt.preventDefault();
        return;
      }
      // Evita segundo drag enquanto um POST move está em voo.
      if (pendingMove) {
        evt.preventDefault();
        return;
      }

      dragState = {
        card: card,
        userPk: card.getAttribute('data-user-pk'),
        potencial: card.getAttribute('data-potencial'),
        desempenho: card.getAttribute('data-desempenho'),
        cancelled: false,
      };

      card.classList.add('opacity-40');
      card.setAttribute('aria-grabbed', 'true');

      if (evt.dataTransfer) {
        evt.dataTransfer.effectAllowed = 'move';
        evt.dataTransfer.setData('text/plain', dragState.userPk || '');
      }
    });

    root.addEventListener('dragover', function (evt) {
      if (!dragState || dragState.cancelled) {
        return;
      }
      var cell = evt.target.closest('[id^="cell-"]');
      if (!cell || !root.contains(cell)) {
        return;
      }
      evt.preventDefault();
      if (evt.dataTransfer) {
        evt.dataTransfer.dropEffect = 'move';
      }
      clearDropHighlight();
      setDropHighlight(cell, true);
    });

    root.addEventListener('dragleave', function (evt) {
      var cell = evt.target.closest('[id^="cell-"]');
      if (!cell) {
        return;
      }
      var related = evt.relatedTarget;
      if (related && cell.contains(related)) {
        return;
      }
      setDropHighlight(cell, false);
    });

    root.addEventListener('drop', function (evt) {
      if (!dragState) {
        return;
      }

      var cell = evt.target.closest('[id^="cell-"]');
      clearDropHighlight();

      if (dragState.cancelled || !cell || !root.contains(cell)) {
        // Fora da grade / cancelado → zero POST; visual restaurado no dragend.
        evt.preventDefault();
        return;
      }

      evt.preventDefault();

      var targetPotencial = cell.getAttribute('data-potencial');
      var targetDesempenho = cell.getAttribute('data-desempenho');
      var userPk = dragState.userPk;
      var card = dragState.card;

      // Mesmo potencial (mesmo que outra linha) → noop client-side, sem POST.
      if (String(targetPotencial) === String(dragState.potencial)) {
        resetDragVisual(card);
        dragState = null;
        return;
      }

      // R4 / T021: card permanece na origem até OOB em (desempenho_derivado, P′).
      // T022: pendingMove guarda origem; em erro → restore + toast (SC-004).
      pendingMove = {
        card: card,
        userPk: String(userPk),
        potencial: String(dragState.potencial),
        desempenho: String(dragState.desempenho),
        originCell: card.closest('[id^="cell-"]'),
      };
      card.removeAttribute('aria-grabbed');
      setPendingVisual(card, true);
      postMove(userPk, targetPotencial, targetDesempenho);
      dragState = null;
    });

    root.addEventListener('dragend', function () {
      clearDropHighlight();
      if (!dragState) {
        return;
      }
      // Esc, drop fora da grade, ou cancel → card permanece na origem (sem POST).
      resetDragVisual(dragState.card);
      dragState = null;
    });

    document.addEventListener('keydown', function (evt) {
      if (evt.key !== 'Escape' || !dragState) {
        return;
      }
      cancelDrag();
    });

    // --- T022: lifecycle do POST move (SC-004) ---
    document.body.addEventListener('htmx:afterRequest', function (evt) {
      if (!pendingMove || !isMoveRequestEvent(evt)) {
        return;
      }
      var detail = evt.detail || {};
      if (detail.successful) {
        clearPendingMoveSuccess();
        return;
      }
      if (detail.failed) {
        failPendingMove(detail.xhr);
      }
    });

    document.body.addEventListener('htmx:responseError', function (evt) {
      if (!pendingMove || !isMoveRequestEvent(evt)) {
        return;
      }
      failPendingMove((evt.detail || {}).xhr);
    });

    document.body.addEventListener('htmx:sendError', function (evt) {
      if (!pendingMove || !isMoveRequestEvent(evt)) {
        return;
      }
      // Rede / CORS / abort — sem HX-Trigger; toast + restore obrigatórios.
      failPendingMove(null);
    });

    // Não injeta HTML de erro 4xx/5xx na grade (swap none já evita; reforço SC-004).
    document.body.addEventListener('htmx:beforeSwap', function (evt) {
      if (!isMoveRequestEvent(evt)) {
        return;
      }
      var detail = evt.detail || {};
      var xhr = detail.xhr;
      if (!xhr || xhr.status < 400) {
        return;
      }
      detail.shouldSwap = false;
      detail.isError = true;
    });

    // T023: reaplicar gates após OOB/swap (cards novos do servidor vêm draggable).
    document.body.addEventListener('htmx:afterSettle', function () {
      applyDragGates(root);
      if (isDragDisabled()) {
        abortActiveDrag();
      }
    });

    // T023: coarse / resize estreito → strip handles; cancela drag em curso.
    function onGateMediaChange() {
      applyDragGates(root);
      if (isDragDisabled()) {
        abortActiveDrag();
      }
    }
    bindMediaQueryChange(MQ_POINTER_COARSE, onGateMediaChange);
    bindMediaQueryChange(MQ_NARROW_VIEWPORT, onGateMediaChange);
  }

  /**
   * Feedback honesto HTMX no drawer/grade (SC-004 / FR-005):
   * - aria-busy + indicadores durante request
   * - não swapear HTML de erro 4xx/5xx no drawer (estado anterior permanece)
   * - toast PT-BR se a resposta não trouxe HX-Trigger showMessage
   */
  function initHonestFeedback() {
    if (!getDrawer()) {
      return;
    }

    document.body.addEventListener('htmx:beforeRequest', function (evt) {
      if (!isMatrixRequestEvent(evt)) {
        return;
      }
      setDrawerBusy(true);
    });

    document.body.addEventListener('htmx:afterRequest', function (evt) {
      if (!isMatrixRequestEvent(evt)) {
        return;
      }
      setDrawerBusy(false);
    });

    document.body.addEventListener('htmx:beforeSwap', function (evt) {
      var detail = evt.detail || {};
      if (!isMatrixSwapTarget(detail.target)) {
        return;
      }
      var xhr = detail.xhr;
      if (!xhr || xhr.status < 400) {
        return;
      }
      // Preserva drawer/grade: não injeta página 403/5xx no painel.
      detail.shouldSwap = false;
      detail.isError = true;
    });

    document.body.addEventListener('htmx:responseError', function (evt) {
      if (!isMatrixRequestEvent(evt)) {
        return;
      }
      var xhr = (evt.detail || {}).xhr;
      if (triggerAlreadyHasMessage(xhr)) {
        return;
      }
      var status = xhr ? xhr.status : 0;
      showToast(messageForStatus(status), 'error');
    });

    document.body.addEventListener('htmx:sendError', function (evt) {
      if (!isMatrixRequestEvent(evt)) {
        return;
      }
      showToast(MSG_REDE, 'error');
    });
  }

  /**
   * Inicializa foco / Escape / restore no drawer (#matrix-drawer).
   * Implementação completa em T027 (espelhar static/js/modal.js).
   */
  function initDrawer() {
    if (!getDrawer()) {
      return;
    }
    // stub a11y — focus on open, focus trap, Escape close, restore trigger focus
  }

  function init() {
    initDrawer();
    initHonestFeedback();
    // T023: gates antes dos listeners — strip draggable em coarse/narrow.
    applyDragGates();
    // Sempre registra DnD se admin; gates bloqueiam dragstart / strip attrs.
    initDragAndDrop();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
