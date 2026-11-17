'use strict';
(() => {
  const forms = document.querySelectorAll('.searchbar');
  forms.forEach(form => {
    const input = form.querySelector('input[name="q"]');
    const clear = form.querySelector('.search-clear');
    if (!input) return;
    // Clear button stays visible at ALL times, including empty searches.
    if (clear) {
      clear.hidden = false;
      clear.addEventListener('click', () => {
        input.value = '';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.focus();
      });
    }
    if (form.dataset.autocomplete !== 'true') return;
    const menu = document.createElement('div');
    menu.className = 'search-suggestions';
    menu.setAttribute('role', 'listbox');
    menu.setAttribute('aria-label', 'Product search ideas');
    menu.hidden = true;
    form.appendChild(menu);
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-expanded', 'false');
    const menuId = 'suggestions-' + Math.random().toString(36).slice(2);
    menu.id = menuId;
    input.setAttribute('aria-controls', menuId);
    let controller, timeout, active = -1, suggestions = [];
    const close = () => {
      menu.hidden = true;
      menu.replaceChildren();
      suggestions = [];
      active = -1;
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
    };
    const select = item => {
      input.value = item.title;
      close();
      // Respect user intent: an explicit suggestion click submits the query.
      form.requestSubmit();
    };
    const paint = () => {
      menu.replaceChildren();
      suggestions.forEach((item, i) => {
        const option = document.createElement('button');
        option.type = 'button';
        option.className = 'search-suggestion' + (i === active ? ' active' : '');
        option.id = menuId + '-option-' + i;
        option.setAttribute('role', 'option');
        option.setAttribute('aria-selected', String(i === active));
        const name = document.createElement('strong');
        name.textContent = item.title;
        const category = document.createElement('small');
        category.textContent = item.category_name;
        option.append(name, category);
        option.addEventListener('mousedown', event => event.preventDefault());
        option.addEventListener('click', () => select(item));
        menu.appendChild(option);
      });
      menu.hidden = suggestions.length === 0;
      input.setAttribute('aria-expanded', String(!menu.hidden));
      if (active >= 0) input.setAttribute('aria-activedescendant', menuId + '-option-' + active);
      else input.removeAttribute('aria-activedescendant');
    };
    input.addEventListener('input', () => {
      clearTimeout(timeout);
      if (controller) controller.abort();
      close();
      const query = input.value.trim();
      if (query.length < 2) return;
      timeout = setTimeout(async () => {
        controller = new AbortController();
        try {
          const res = await fetch('/api/suggestions?q=' + encodeURIComponent(query), { signal: controller.signal });
          if (!res.ok) return;
          const data = await res.json();
          if (input.value.trim() !== query) return;
          suggestions = Array.isArray(data.suggestions) ? data.suggestions.slice(0, 6) : [];
          active = -1;
          paint();
        } catch (error) { if (error.name !== 'AbortError') close(); }
      }, 210);
    });
    input.addEventListener('keydown', event => {
      if (event.key === 'Escape') { close(); return; }
      if (!suggestions.length) return;
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        active = event.key === 'ArrowDown' ? (active + 1) % suggestions.length : (active - 1 + suggestions.length) % suggestions.length;
        paint();
      } else if (event.key === 'Enter' && active >= 0) {
        event.preventDefault(); select(suggestions[active]);
      }
    });
    input.addEventListener('blur', () => setTimeout(close, 150));
    form.addEventListener('submit', () => { if (controller) controller.abort(); });
  });
})();
