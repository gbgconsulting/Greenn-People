/**
 * Acessibilidade básica de modal HTMX (#modal-container).
 * - Foco no primeiro controle ao abrir
 * - Focus trap Tab / Shift+Tab enquanto aberto
 * - Escape fecha
 * - Restore de foco no trigger ao fechar
 */
(function () {
  const CONTAINER_ID = 'modal-container';
  const FOCUSABLE_SELECTOR = [
    'a[href]',
    'button:not([disabled])',
    'textarea:not([disabled])',
    'input:not([disabled]):not([type="hidden"])',
    'select:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(', ');

  let lastTrigger = null;

  function getContainer() {
    return document.getElementById(CONTAINER_ID);
  }

  function getDialog() {
    const container = getContainer();
    if (!container) return null;
    return container.querySelector('[role="dialog"][aria-modal="true"]');
  }

  function isOpen() {
    return !!getDialog();
  }

  function isVisible(el) {
    return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  }

  function getFocusable(dialog) {
    return Array.from(dialog.querySelectorAll(FOCUSABLE_SELECTOR)).filter((el) => {
      if (el.hasAttribute('disabled') || el.getAttribute('aria-hidden') === 'true') return false;
      if (el.closest('[aria-hidden="true"]')) return false;
      return isVisible(el);
    });
  }

  function rememberTrigger(el) {
    if (!el || el.nodeType !== 1) return;
    lastTrigger = el.closest('button, a, [href], [tabindex]') || el;
  }

  function focusInitial() {
    const dialog = getDialog();
    if (!dialog) return;

    const preferred = dialog.querySelector(
      'input:not([type="hidden"]):not([disabled]), textarea:not([disabled]), select:not([disabled])'
    );
    if (preferred) {
      preferred.focus();
      return;
    }

    const focusable = getFocusable(dialog);
    if (focusable.length) {
      focusable[0].focus();
      return;
    }

    dialog.focus();
  }

  function trapFocus(e) {
    if (e.key !== 'Tab' || !isOpen()) return;

    const dialog = getDialog();
    if (!dialog) return;

    const focusable = getFocusable(dialog);

    if (focusable.length === 0) {
      e.preventDefault();
      if (typeof dialog.focus === 'function') dialog.focus();
      return;
    }

    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const active = document.activeElement;
    const outside = !dialog.contains(active);
    const index = focusable.indexOf(active);

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

  function closeModal() {
    const container = getContainer();
    if (!container) return;

    const hadDialog = !!getDialog();
    container.innerHTML = '';

    if (hadDialog && lastTrigger && typeof lastTrigger.focus === 'function') {
      try {
        lastTrigger.focus();
      } catch (_) {
        /* elemento removido do DOM */
      }
    }
    lastTrigger = null;
  }

  document.body.addEventListener('htmx:beforeRequest', (e) => {
    const target = e.detail && e.detail.target;
    if (target && target.id === CONTAINER_ID) {
      rememberTrigger(e.detail.elt);
    }
  });

  document.body.addEventListener('htmx:afterSwap', (e) => {
    const target = e.detail && e.detail.target;
    if (target && target.id === CONTAINER_ID && isOpen()) {
      // Deixa o browser terminar o swap antes de focar
      requestAnimationFrame(focusInitial);
    }
  });

  document.body.addEventListener('closeModal', () => {
    closeModal();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && isOpen()) {
      e.preventDefault();
      closeModal();
      return;
    }
    trapFocus(e);
  });

  window.closeModal = closeModal;
  window.isAppModalOpen = isOpen;
})();
