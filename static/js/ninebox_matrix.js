/**
 * Matriz 9-box interativa — HTML5 DnD + feedback do drawer (SC-004).
 * Carregado só em templates/talent/matrix.html (extra_js).
 *
 * T017: loading (aria-busy + indicadores), erros PT-BR, preservar DOM em falha.
 * T020: DnD dragstart/drop + POST move; Esc/fora → zero POST + restore visual.
 * T021: snap R4 — card em (desempenho_derivado, P′); toast se linha incompatível.
 * T022: erro 403/400/rede/5xx → restore posição + toast; nunca sucesso silencioso.
 * T026: empty definitivo (#ninebox-matrix-empty) ≠ loading (aria-busy + indicador).
 * T027: a11y drawer — foco ao abrir, focus trap, Escape fecha, restore no trigger
 *   (espelha static/js/modal.js).
 * T028: rótulos além da cor nas células; handles DnD com nome acessível
 *   (escondidos em coarse/narrow — FR-010).
 * T035 (007): polish visual drag (opacity/ring/cursor DS v2) + live region
 *   de suporte — sem mudar POST / potencial-only / handlers 006.
 *
 * Convenção DOM:
 *   #matrix-results — região com aria-busy; loading ≠ empty
 *   #ninebox-matrix — grade com data-ciclo-id / data-move-url-template / data-admin
 *   #ninebox-matrix-empty — empty Freeze quando zero classificados
 *   #matrix-drawer — painel lateral HTMX (swap target)
 *   #matrix-drawer-indicator / #matrix-loading-indicator — fora do swap
 *   [data-user-pk] nos cards; células #cell-{desempenho}-{potencial}
 */
(function () {
  'use strict';

  var DRAWER_ID = 'matrix-drawer';
  var MATRIX_ID = 'ninebox-matrix';
  var MATRIX_RESULTS_ID = 'matrix-results';
  var MATRIX_LOADING_ID = 'matrix-loading-indicator';
  var FILTERS_ID = 'matrix-filters';
  /** Touch / coarse pointer — DnD inadequado (FR-010 / research R5). */
  var MQ_POINTER_COARSE = '(pointer: coarse)';
  /** Viewport estreito (abaixo do breakpoint md Tailwind). */
  var MQ_NARROW_VIEWPORT = '(max-width: 767px)';
  var MSG_REDE =
    'Não foi possível completar a ação. Verifique a conexão e tente novamente.';
  var MSG_PERMISSAO = 'Você não tem permissão para esta ação.';
  var MSG_SERVIDOR = 'Ocorreu um erro no servidor. Tente novamente.';
  /** Anúncios ARIA do drag (live region #ninebox-drag-status) — T035. */
  var MSG_DRAG_START =
    'Arrastando pessoa. Solte em outra coluna de potencial.';
  var MSG_DROP_COMPAT =
    'Célula compatível. Solte para alterar o potencial.';
  var MSG_DROP_SNAP =
    'Só o potencial será alterado; o desempenho permanece o derivado.';
  var MSG_MOVE_PENDING = 'Salvando nova posição…';
  var DRAG_STATUS_ID = 'ninebox-drag-status';
  /** Controles focáveis no drawer (mesmo conjunto de modal.js). */
  var FOCUSABLE_SELECTOR = [
    'a[href]',
    'button:not([disabled])',
    'textarea:not([disabled])',
    'input:not([disabled]):not([type="hidden"])',
    'select:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(', ');

  /** HTML do placeholder idle — capturado no init para restore no Escape/Fechar. */
  var drawerIdleHtml = null;
  /** Trigger (card/button) que abriu o drawer — restore de foco ao fechar. */
  var drawerLastTrigger = null;

  function getDrawer() {
    return document.getElementById(DRAWER_ID);
  }

  function getMatrixRoot() {
    return document.getElementById(MATRIX_ID);
  }

  function getMatrixResults() {
    return document.getElementById(MATRIX_RESULTS_ID);
  }

  /**
   * Loading honesto da região da grade (T026 / FR-005):
   * preserva conteúdo atual (grade ou empty anterior); NÃO troca por empty definitivo.
   */
  function setMatrixResultsBusy(busy) {
    var region = getMatrixResults();
    if (!region) {
      return;
    }
    region.setAttribute('aria-busy', busy ? 'true' : 'false');
    region.classList.toggle('htmx-request', !!busy);
    var matrix = getMatrixRoot();
    if (matrix) {
      matrix.classList.toggle('opacity-60', !!busy);
    }
    var empty = region.querySelector('[data-matrix-state="empty"]');
    if (empty) {
      // Empty definitivo só anuncia quando não estamos em loading.
      empty.setAttribute('aria-hidden', busy ? 'true' : 'false');
    }
    var ind = document.getElementById(MATRIX_LOADING_ID);
    if (ind) {
      ind.setAttribute('aria-hidden', busy ? 'false' : 'true');
    }
  }

  function resolveDrawerState(drawer) {
    if (!drawer) {
      return 'idle';
    }
    if (drawer.getAttribute('aria-busy') === 'true') {
      return 'loading';
    }
    if (drawer.querySelector('[data-drawer-placeholder="idle"]')) {
      return 'idle';
    }
    return 'open';
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
    // loading ≠ empty definitivo (placeholder idle permanece no DOM até o swap)
    drawer.setAttribute(
      'data-drawer-state',
      busy ? 'loading' : resolveDrawerState(drawer),
    );
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
   * T028: handles [data-dnd-handle] + aria-grabbed só quando DnD ativo;
   * ausentes/ocultos no mobile (contrato a11y-matrix-drawer).
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
      var handle = card.querySelector('[data-dnd-handle]');
      if (!capable || disabled) {
        card.setAttribute('draggable', 'false');
        card.classList.remove('cursor-grab', 'active:cursor-grabbing');
        card.removeAttribute('aria-grabbed');
        if (handle) {
          handle.setAttribute('aria-hidden', 'true');
          handle.setAttribute('hidden', '');
        }
        return;
      }
      card.setAttribute('draggable', 'true');
      card.classList.add('cursor-grab', 'active:cursor-grabbing');
      if (!card.hasAttribute('aria-grabbed')) {
        card.setAttribute('aria-grabbed', 'false');
      }
      if (handle) {
        handle.removeAttribute('aria-hidden');
        handle.removeAttribute('hidden');
      }
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
    /** Última célula anunciada (evita spam no dragover). */
    var lastAnnounceCellId = null;
    /**
     * T035 — tokens DS v2 (focus ring emerald / Status Triad amber alerta).
     * Highlight quando a linha do drop = desempenho derivado.
     */
    var DROP_HL = 'ring-2 ring-emerald-500 ring-inset bg-emerald-50/40';
    /** Highlight quando haverá snap de linha (só potencial muda). */
    var SNAP_HL = 'ring-2 ring-amber-500 ring-inset bg-amber-50/40';
    /** Card em arraste: opacity + ring shell + cursor grabbing. */
    var DRAG_CARD =
      'opacity-60 ring-2 ring-emerald-500 ring-offset-1 ring-offset-surface cursor-grabbing select-none';
    /** Card com POST move em voo. */
    var PENDING_CARD = 'opacity-50';
    var ALL_HL = [];
    (DROP_HL + ' ' + SNAP_HL)
      .split(/\s+/)
      .forEach(function (cls) {
        if (cls && ALL_HL.indexOf(cls) === -1) {
          ALL_HL.push(cls);
        }
      });

    function addClassTokens(el, tokens) {
      if (!el || !tokens) {
        return;
      }
      tokens.split(/\s+/).forEach(function (cls) {
        if (cls) {
          el.classList.add(cls);
        }
      });
    }

    function removeClassTokens(el, tokens) {
      if (!el || !tokens) {
        return;
      }
      tokens.split(/\s+/).forEach(function (cls) {
        if (cls) {
          el.classList.remove(cls);
        }
      });
    }

    function ensureDragStatus() {
      var el = document.getElementById(DRAG_STATUS_ID);
      if (el) {
        return el;
      }
      el = document.createElement('div');
      el.id = DRAG_STATUS_ID;
      el.className = 'sr-only';
      el.setAttribute('role', 'status');
      el.setAttribute('aria-live', 'polite');
      el.setAttribute('aria-atomic', 'true');
      var host = getMatrixResults() || root.parentElement || document.body;
      host.appendChild(el);
      return el;
    }

    function announceDrag(message) {
      var el = ensureDragStatus();
      el.textContent = '';
      if (!message) {
        return;
      }
      window.requestAnimationFrame(function () {
        el.textContent = message;
      });
    }

    function clearDropHighlight() {
      root.querySelectorAll('[id^="cell-"]').forEach(function (cell) {
        ALL_HL.forEach(function (cls) {
          cell.classList.remove(cls);
        });
        cell.removeAttribute('data-drop-snap');
        cell.removeAttribute('data-drop-target');
      });
      lastAnnounceCellId = null;
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
      cell.removeAttribute('data-drop-target');
      if (!on) {
        return;
      }
      var snap = willSnapToCell(cell);
      addClassTokens(cell, snap ? SNAP_HL : DROP_HL);
      cell.setAttribute('data-drop-target', '1');
      if (snap) {
        cell.setAttribute('data-drop-snap', '1');
      }
      if (cell.id && cell.id !== lastAnnounceCellId) {
        lastAnnounceCellId = cell.id;
        announceDrag(snap ? MSG_DROP_SNAP : MSG_DROP_COMPAT);
      }
    }

    function resetDragVisual(card) {
      if (!card) {
        return;
      }
      removeClassTokens(card, DRAG_CARD + ' ' + PENDING_CARD + ' opacity-40');
      // Idle grabbable → false; applyDragGates remove o attr se DnD desligado.
      if (
        card.getAttribute('data-dnd-capable') === '1' &&
        card.getAttribute('draggable') === 'true'
      ) {
        card.setAttribute('aria-grabbed', 'false');
      } else {
        card.removeAttribute('aria-grabbed');
      }
      card.removeAttribute('aria-busy');
    }

    function setPendingVisual(card, on) {
      if (!card) {
        return;
      }
      removeClassTokens(card, DRAG_CARD + ' opacity-40');
      if (on) {
        addClassTokens(card, PENDING_CARD);
        card.setAttribute('aria-busy', 'true');
      } else {
        removeClassTokens(card, PENDING_CARD);
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
      announceDrag('');
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
      announceDrag('');
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
      announceDrag('');
    }

    /** Encerra drag em curso (gate mobile / media change) sem POST. */
    function abortActiveDrag() {
      if (!dragState) {
        return;
      }
      resetDragVisual(dragState.card);
      clearDropHighlight();
      dragState = null;
      announceDrag('');
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

      addClassTokens(card, DRAG_CARD);
      card.setAttribute('aria-grabbed', 'true');
      announceDrag(MSG_DRAG_START);

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
        announceDrag('');
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
      announceDrag(MSG_MOVE_PENDING);
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
      announceDrag('');
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
   * Feedback honesto HTMX no drawer/grade (SC-004 / FR-005 / T026):
   * - aria-busy + indicadores durante request (≠ empty definitivo)
   * - não swapear HTML de erro 4xx/5xx no drawer (estado anterior permanece)
   * - toast PT-BR se a resposta não trouxe HX-Trigger showMessage
   */
  function initHonestFeedback() {
    if (!getDrawer() && !getMatrixResults()) {
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

    document.body.addEventListener('htmx:afterSwap', function (evt) {
      var detail = evt.detail || {};
      if (!isMatrixSwapTarget(detail.target)) {
        return;
      }
      var drawer = getDrawer();
      if (!drawer) {
        return;
      }
      // Conteúdo já trocado; loading ainda pode estar ativo até afterRequest.
      if (drawer.getAttribute('aria-busy') === 'true') {
        drawer.setAttribute('data-drawer-state', 'loading');
        return;
      }
      drawer.setAttribute(
        'data-drawer-state',
        drawer.querySelector('[data-drawer-placeholder="idle"]') ? 'idle' : 'open',
      );
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
   * Filtros GET: ao mudar/submeter, marca loading na região — não apresenta empty
   * definitivo até a nova página (T026 / quickstart slice 3).
   * Usa change + submit: requestSubmit dispara submit; form.submit() legado não.
   */
  function initFilterHonestLoading() {
    var form = document.getElementById(FILTERS_ID);
    if (!form || !getMatrixResults()) {
      return;
    }
    function markLoading() {
      setMatrixResultsBusy(true);
    }
    form.addEventListener('change', markLoading);
    form.addEventListener('submit', markLoading);
  }

  /**
   * A11y do drawer (#matrix-drawer) — espelha static/js/modal.js (T027 / FR-011):
   * - Foco no primeiro controle (ou heading) ao abrir via HTMX
   * - Focus trap Tab / Shift+Tab enquanto aberto
   * - Escape / botão Fechar fecham e restauram foco no card trigger
   * - Swap de save/toggle dentro do drawer NÃO sobrescreve o trigger
   */
  function initDrawer() {
    var drawer = getDrawer();
    if (!drawer) {
      return;
    }

    if (drawer.querySelector('[data-drawer-placeholder="idle"]')) {
      drawerIdleHtml = drawer.innerHTML;
    }

    function getDialog() {
      var el = getDrawer();
      if (!el) {
        return null;
      }
      return el.querySelector('[role="dialog"][aria-modal="true"]');
    }

    function isDrawerOpen() {
      return !!getDialog();
    }

    function isVisible(el) {
      return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
    }

    function getFocusable(dialog) {
      return Array.prototype.slice
        .call(dialog.querySelectorAll(FOCUSABLE_SELECTOR))
        .filter(function (el) {
          if (el.hasAttribute('disabled') || el.getAttribute('aria-hidden') === 'true') {
            return false;
          }
          if (el.closest('[aria-hidden="true"]')) {
            return false;
          }
          return isVisible(el);
        });
    }

    function rememberTrigger(el) {
      if (!el || el.nodeType !== 1) {
        return;
      }
      var panel = getDrawer();
      // Save/toggle HTMX dentro do drawer não deve trocar o restore target.
      if (panel && panel.contains(el)) {
        return;
      }
      drawerLastTrigger =
        el.closest('button, a, [href], [tabindex]') || el;
    }

    function focusInitial() {
      var dialog = getDialog();
      if (!dialog) {
        return;
      }

      var preferred = dialog.querySelector(
        'input:not([type="hidden"]):not([disabled]), textarea:not([disabled]), select:not([disabled])',
      );
      if (preferred) {
        preferred.focus();
        return;
      }

      var focusable = getFocusable(dialog);
      if (focusable.length) {
        focusable[0].focus();
        return;
      }

      var heading = dialog.querySelector('#matrix-drawer-heading');
      if (heading && typeof heading.focus === 'function') {
        heading.focus();
        return;
      }

      if (typeof dialog.focus === 'function') {
        dialog.focus();
      }
    }

    function trapFocus(e) {
      if (e.key !== 'Tab' || !isDrawerOpen()) {
        return;
      }

      var dialog = getDialog();
      if (!dialog) {
        return;
      }

      var focusable = getFocusable(dialog);

      if (focusable.length === 0) {
        e.preventDefault();
        if (typeof dialog.focus === 'function') {
          dialog.focus();
        }
        return;
      }

      var first = focusable[0];
      var last = focusable[focusable.length - 1];
      var active = document.activeElement;
      var outside = !dialog.contains(active);
      var index = focusable.indexOf(active);

      if (e.shiftKey) {
        if (outside || index <= 0) {
          e.preventDefault();
          last.focus();
        }
      } else if (outside || index === -1 || index === focusable.length - 1) {
        e.preventDefault();
        first.focus();
      }
    }

    function closeDrawer() {
      var panel = getDrawer();
      if (!panel) {
        return;
      }

      var hadDialog = isDrawerOpen();
      if (drawerIdleHtml != null) {
        panel.innerHTML = drawerIdleHtml;
      } else {
        panel.innerHTML = '';
      }
      panel.setAttribute('aria-busy', 'false');
      panel.setAttribute('data-drawer-state', 'idle');
      panel.classList.remove('opacity-60', 'pointer-events-none');

      if (hadDialog && drawerLastTrigger && typeof drawerLastTrigger.focus === 'function') {
        try {
          drawerLastTrigger.focus();
        } catch (err) {
          /* elemento removido do DOM (ex.: OOB move) */
        }
      }
      drawerLastTrigger = null;
    }

    function isDragInProgress() {
      var matrix = getMatrixRoot();
      return !!(matrix && matrix.querySelector('[aria-grabbed="true"]'));
    }

    document.body.addEventListener('htmx:beforeRequest', function (e) {
      var detail = e.detail || {};
      var target = detail.target;
      if (target && target.id === DRAWER_ID) {
        rememberTrigger(detail.elt);
      }
    });

    document.body.addEventListener('htmx:afterSwap', function (e) {
      var detail = e.detail || {};
      var target = detail.target;
      if (target && target.id === DRAWER_ID && isDrawerOpen()) {
        requestAnimationFrame(focusInitial);
      }
    });

    document.body.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-drawer-close]');
      if (!btn) {
        return;
      }
      var panel = getDrawer();
      if (!panel || !panel.contains(btn)) {
        return;
      }
      e.preventDefault();
      closeDrawer();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && isDrawerOpen()) {
        // DnD ativo: deixa o handler de drag cancelar o arraste (zero POST).
        if (isDragInProgress()) {
          return;
        }
        e.preventDefault();
        closeDrawer();
        return;
      }
      trapFocus(e);
    });

    window.closeMatrixDrawer = closeDrawer;
  }

  function init() {
    initDrawer();
    initHonestFeedback();
    initFilterHonestLoading();
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
