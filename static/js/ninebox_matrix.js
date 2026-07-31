/**
 * Matriz 9-box interativa — HTML5 DnD + feedback do drawer (SC-004).
 * Carregado só em templates/talent/matrix.html (extra_js).
 *
 * T017: loading (aria-busy + indicadores), erros PT-BR, preservar DOM em falha.
 * DnD completo: T020–T023; a11y drawer: T027.
 *
 * Convenção DOM:
 *   #matrix-drawer — painel lateral HTMX (swap target)
 *   #matrix-drawer-indicator — indicador local (fora do swap)
 *   [data-user-pk] nos cards; células #cell-{desempenho}-{potencial}
 */
(function () {
  'use strict';

  var DRAWER_ID = 'matrix-drawer';
  var MSG_REDE =
    'Não foi possível completar a ação. Verifique a conexão e tente novamente.';
  var MSG_PERMISSAO = 'Você não tem permissão para esta ação.';
  var MSG_SERVIDOR = 'Ocorreu um erro no servidor. Tente novamente.';

  function getDrawer() {
    return document.getElementById(DRAWER_ID);
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
   * True quando DnD deve ficar desligado (mobile / pointer coarse / viewport estreito).
   * Implementação completa em T023 (FR-010).
   */
  function isDragDisabled() {
    return false;
  }

  /**
   * Inicializa HTML5 drag-and-drop entre células (potencial-only).
   * Implementação completa em T020–T022.
   */
  function initDragAndDrop() {
    // stub — dragstart/drop, POST move, cancel Esc/fora, snap, revert on error
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
    if (!isDragDisabled()) {
      initDragAndDrop();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
