/**
 * Drawer de perfil do colaborador na Estrutura.
 * Abre no swap HTMX para #structure-collaborator-drawer-panel;
 * Escape / backdrop / botão fechar restauram idle.
 *
 * Posicionamento via style (translateX / max-width): utilitários Tailwind
 * como translate-x-full podem não estar no CSS compilado.
 */
(function () {
  'use strict';

  var DRAWER_ID = 'structure-collaborator-drawer';
  var PANEL_ID = 'structure-collaborator-drawer-panel';
  var BACKDROP_SEL = '[data-structure-drawer-backdrop]';
  var lastTrigger = null;

  function getDrawer() {
    return document.getElementById(DRAWER_ID);
  }

  function getPanel() {
    return document.getElementById(PANEL_ID);
  }

  function getBackdrop() {
    return document.querySelector(BACKDROP_SEL);
  }

  function openDrawer(trigger) {
    var drawer = getDrawer();
    var backdrop = getBackdrop();
    if (!drawer || !backdrop) {
      return;
    }
    lastTrigger = trigger || null;
    drawer.hidden = false;
    drawer.style.transform = 'translateX(0)';
    drawer.setAttribute('aria-hidden', 'false');
    backdrop.hidden = false;
    backdrop.classList.remove('pointer-events-none', 'opacity-0');
    backdrop.classList.add('opacity-100');
    document.documentElement.classList.add('overflow-hidden');
    window.requestAnimationFrame(function () {
      var heading = drawer.querySelector('#structure-collaborator-drawer-heading');
      if (heading && heading.focus) {
        heading.focus();
      }
    });
  }

  function closeDrawer() {
    var drawer = getDrawer();
    var backdrop = getBackdrop();
    var panel = getPanel();
    if (!drawer || !backdrop) {
      return;
    }
    drawer.style.transform = 'translateX(100%)';
    drawer.setAttribute('aria-hidden', 'true');
    backdrop.classList.add('pointer-events-none', 'opacity-0');
    backdrop.classList.remove('opacity-100');
    window.setTimeout(function () {
      drawer.hidden = true;
      backdrop.hidden = true;
      if (panel) {
        panel.innerHTML = '';
      }
    }, 280);
    document.documentElement.classList.remove('overflow-hidden');
    if (lastTrigger && lastTrigger.focus) {
      lastTrigger.focus();
    }
    lastTrigger = null;
  }

  function isStructureDrawerEvent(evt) {
    var detail = evt.detail || {};
    var target = detail.target;
    return !!(target && target.id === PANEL_ID);
  }

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    if (!isStructureDrawerEvent(evt)) {
      return;
    }
    var trigger = (evt.detail && evt.detail.elt) || null;
    openDrawer(trigger);
  });

  document.addEventListener('click', function (evt) {
    var closeBtn = evt.target.closest('[data-structure-drawer-close]');
    if (closeBtn) {
      evt.preventDefault();
      closeDrawer();
      return;
    }
    if (evt.target.closest(BACKDROP_SEL)) {
      closeDrawer();
      return;
    }
    var toggle = evt.target.closest('[data-toggle-older-cycles]');
    if (toggle) {
      var older = document.querySelector('[data-older-cycles]');
      var label = toggle.querySelector('[data-toggle-older-label]');
      if (!older) {
        return;
      }
      var expanded = toggle.getAttribute('aria-expanded') === 'true';
      older.classList.toggle('hidden', expanded);
      toggle.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      if (label) {
        var total = toggle.getAttribute('data-total-cycles') || '';
        label.textContent = expanded
          ? 'Ver histórico completo (' + total + ' ciclos)'
          : 'Recolher histórico';
      }
    }
  });

  document.addEventListener('keydown', function (evt) {
    if (evt.key !== 'Escape') {
      return;
    }
    var drawer = getDrawer();
    if (drawer && drawer.getAttribute('aria-hidden') === 'false') {
      closeDrawer();
    }
  });
})();
