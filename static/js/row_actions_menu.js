/**
 * Menu ⋮ por linha — posicionamento fixo com detecção de espaço acima/abaixo.
 * Escapa `overflow` dos frames de tabela sem esticar a largura do painel.
 */
(function () {
  const MENU_SELECTOR = 'details.row-actions-menu';
  const VIEWPORT_PADDING = 8;
  const GAP = 4;

  function getPanel(details) {
    return details.querySelector('.row-actions-panel');
  }

  function resetPanel(details) {
    const panel = getPanel(details);
    if (!panel) return;

    panel.classList.remove('row-actions-panel--floating');
    panel.style.cssText = '';
    details.classList.remove('row-actions-menu--dropup');
  }

  function closeAll(except) {
    document.querySelectorAll(`${MENU_SELECTOR}[open]`).forEach((details) => {
      if (details === except) return;
      details.open = false;
      resetPanel(details);
    });
  }

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function positionPanel(details) {
    const trigger = details.querySelector('.row-actions-trigger');
    const panel = getPanel(details);
    if (!trigger || !panel) return;

    panel.classList.add('row-actions-panel--floating');
    panel.style.visibility = 'hidden';
    panel.style.top = '0';
    panel.style.left = '0';

    const triggerRect = trigger.getBoundingClientRect();
    const panelRect = panel.getBoundingClientRect();
    if (panelRect.height === 0 || panelRect.width === 0) {
      requestAnimationFrame(() => positionPanel(details));
      return;
    }

    const panelHeight = panelRect.height;
    const panelWidth = panelRect.width;

    const spaceBelow =
      window.innerHeight - triggerRect.bottom - GAP - VIEWPORT_PADDING;
    const spaceAbove = triggerRect.top - GAP - VIEWPORT_PADDING;
    const fitsBelow = panelHeight <= spaceBelow;
    const fitsAbove = panelHeight <= spaceAbove;
    const openDown = fitsBelow || (!fitsAbove && spaceBelow >= spaceAbove);

    let top;
    if (openDown) {
      top = triggerRect.bottom + GAP;
      details.classList.remove('row-actions-menu--dropup');
    } else {
      top = triggerRect.top - panelHeight - GAP;
      details.classList.add('row-actions-menu--dropup');
    }

    top = clamp(
      top,
      VIEWPORT_PADDING,
      window.innerHeight - panelHeight - VIEWPORT_PADDING,
    );

    let left = triggerRect.right - panelWidth;
    left = clamp(
      left,
      VIEWPORT_PADDING,
      window.innerWidth - panelWidth - VIEWPORT_PADDING,
    );

    panel.style.top = `${Math.round(top)}px`;
    panel.style.left = `${Math.round(left)}px`;
    panel.style.visibility = '';
  }

  function repositionOpenMenus() {
    document.querySelectorAll(`${MENU_SELECTOR}[open]`).forEach(positionPanel);
  }

  document.addEventListener(
    'toggle',
    (event) => {
      const details = event.target;
      if (!(details instanceof HTMLDetailsElement)) return;
      if (!details.matches(MENU_SELECTOR)) return;

      if (details.open) {
        closeAll(details);
        requestAnimationFrame(() => positionPanel(details));
        return;
      }

      resetPanel(details);
    },
    true,
  );

  document.addEventListener('click', (event) => {
    if (event.target.closest(MENU_SELECTOR)) return;
    closeAll();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    closeAll();
  });

  window.addEventListener('resize', repositionOpenMenus);
  document.addEventListener('scroll', repositionOpenMenus, true);
})();
