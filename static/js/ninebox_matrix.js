/**
 * Matriz 9-box interativa — HTML5 DnD + init do drawer.
 * Carregado só em templates/talent/matrix.html (extra_js).
 *
 * Escopo deste esqueleto (T003): estrutura e pontos de extensão.
 * Lógica completa: T020–T023 (DnD/snap/revert/gates) e T027 (a11y drawer).
 *
 * Convenção DOM (futura):
 *   #matrix-drawer — painel lateral HTMX
 *   [data-user-pk] nos cards; células #cell-{desempenho}-{potencial}
 */
(function () {
  'use strict';

  var DRAWER_ID = 'matrix-drawer';

  function getDrawer() {
    return document.getElementById(DRAWER_ID);
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
   * Inicializa foco / Escape / restore no drawer (#matrix-drawer).
   * Implementação completa em T027 (espelhar static/js/modal.js).
   */
  function initDrawer() {
    // stub — focus on open, focus trap, Escape close, restore trigger focus
    if (!getDrawer()) {
      return;
    }
  }

  function init() {
    initDrawer();
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
