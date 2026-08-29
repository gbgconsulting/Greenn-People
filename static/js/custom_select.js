/**
 * Select customizado — dropdown com posicionamento fixo para não ser cortado
 * por containers com overflow. Mantém o <select> nativo oculto para o submit.
 */
(function initCustomSelect() {
  const MAX_HEIGHT = 240;

  function getSelectedLabel(select) {
    const option = select.options[select.selectedIndex];
    if (!option) return '';
    return option.textContent.trim();
  }

  function syncTriggerLabel(select, trigger) {
    const label = getSelectedLabel(select);
    const isPlaceholder = !select.value;
    trigger.textContent = label;
    trigger.classList.toggle('text-slate-400', isPlaceholder);
    trigger.classList.toggle('text-slate-800', !isPlaceholder);
  }

  function positionList(trigger, list) {
    const rect = trigger.getBoundingClientRect();
    list.style.position = 'fixed';
    list.style.left = `${rect.left}px`;
    list.style.width = `${rect.width}px`;
    list.style.zIndex = '50';

    list.classList.remove('hidden');
    const contentHeight = Math.min(list.scrollHeight, MAX_HEIGHT);
    const spaceBelow = window.innerHeight - rect.bottom - 8;
    const spaceAbove = rect.top - 8;

    if (spaceBelow >= contentHeight || spaceBelow >= spaceAbove) {
      list.style.top = `${rect.bottom + 4}px`;
      list.style.bottom = 'auto';
      list.style.maxHeight = `${Math.min(MAX_HEIGHT, Math.max(spaceBelow, 120))}px`;
    } else {
      list.style.top = 'auto';
      list.style.bottom = `${window.innerHeight - rect.top + 4}px`;
      list.style.maxHeight = `${Math.min(MAX_HEIGHT, Math.max(spaceAbove, 120))}px`;
    }
  }

  function enhanceWrapper(wrapper) {
    const select = wrapper.querySelector('select');
    if (!select || select.dataset.customSelectInit) return;
    select.dataset.customSelectInit = '1';

    select.classList.add('sr-only');
    select.tabIndex = -1;

    const trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = `${select.className.replace(/\bsr-only\b/g, '').trim()} text-left`;
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');
    trigger.id = `${select.id}-trigger`;
    syncTriggerLabel(select, trigger);

    const list = document.createElement('ul');
    list.setAttribute('role', 'listbox');
    list.setAttribute('aria-labelledby', trigger.id);
    list.className =
      'hidden overflow-y-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg';

    let isOpen = false;

    function close() {
      if (!isOpen) return;
      isOpen = false;
      list.classList.add('hidden');
      trigger.setAttribute('aria-expanded', 'false');
    }

    function buildOptions() {
      list.innerHTML = '';
      Array.from(select.options).forEach((option) => {
        if (option.disabled && option.value === '') return;

        const item = document.createElement('li');
        item.setAttribute('role', 'option');
        item.dataset.value = option.value;
        item.textContent = option.textContent.trim();
        item.className =
          'cursor-pointer px-4 py-2.5 font-ui text-base text-slate-800 hover:bg-slate-50';
        item.setAttribute(
          'aria-selected',
          option.selected ? 'true' : 'false',
        );
        if (option.selected) {
          item.classList.add('bg-emerald-50', 'text-emerald-800');
        }

        item.addEventListener('click', () => {
          select.value = option.value;
          select.dispatchEvent(new Event('change', { bubbles: true }));
          syncTriggerLabel(select, trigger);
          buildOptions();
          close();
        });

        list.appendChild(item);
      });
    }

    function open() {
      buildOptions();
      positionList(trigger, list);
      isOpen = true;
      trigger.setAttribute('aria-expanded', 'true');
    }

    function toggle() {
      if (isOpen) close();
      else open();
    }

    trigger.addEventListener('click', toggle);

    document.addEventListener('click', (event) => {
      if (!wrapper.contains(event.target) && !list.contains(event.target)) {
        close();
      }
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') close();
    });

    window.addEventListener(
      'resize',
      () => {
        if (isOpen) positionList(trigger, list);
      },
      { passive: true },
    );

    window.addEventListener(
      'scroll',
      () => {
        if (isOpen) positionList(trigger, list);
      },
      { passive: true, capture: true },
    );

    select.addEventListener('change', () => {
      syncTriggerLabel(select, trigger);
      buildOptions();
    });

    wrapper.insertBefore(trigger, select);
    document.body.appendChild(list);
    buildOptions();

    const label = document.querySelector(`label[for="${select.id}"]`);
    if (label) {
      label.setAttribute('for', trigger.id);
    }
  }

  function init(root) {
    (root || document)
      .querySelectorAll('[data-custom-select]')
      .forEach(enhanceWrapper);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => init());
  } else {
    init();
  }

  document.body.addEventListener('htmx:afterSwap', (event) => {
    init(event.detail.target);
  });
})();
