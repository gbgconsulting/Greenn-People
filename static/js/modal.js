/**
 * Acessibilidade básica de modal HTMX (#modal-container).
 * - Foco no primeiro controle ao abrir
 * - Escape fecha
 * - Restore de foco no trigger ao fechar
 */
(function () {
  const CONTAINER_ID = 'modal-container';
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

    const focusable = dialog.querySelector(
      'button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'
    );
    if (focusable) {
      focusable.focus();
      return;
    }

    dialog.focus();
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
    if (e.key !== 'Escape' || !isOpen()) return;
    e.preventDefault();
    closeModal();
  });

  window.closeModal = closeModal;
  window.isAppModalOpen = isOpen;
})();
