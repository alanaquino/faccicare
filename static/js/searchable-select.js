/*
 * searchable-select.js
 * Progressive enhancement: turns any <select data-searchable> into a
 * type-to-filter combobox. The original <select> is kept (visually hidden)
 * as the real form value holder, so name/value/required and server-side
 * handling keep working with zero backend changes.
 *
 * Usage:  <select name="paciente" data-searchable required> ... </select>
 * Optional: data-placeholder="Escriba para buscar…"
 */
(function () {
  'use strict';

  var MAX_RESULTS = 50;

  function normalize(text) {
    return (text || '')
      .toString()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, ''); // strip accents
  }

  function enhance(select) {
    if (select.dataset.searchableReady) return;
    select.dataset.searchableReady = '1';

    // Snapshot options before we touch anything.
    var options = Array.prototype.map.call(select.options, function (o) {
      return { value: o.value, label: (o.textContent || '').trim(), disabled: o.disabled };
    });

    var placeholderOpt = options.length && options[0].value === '' ? options[0] : null;
    var placeholderText =
      select.getAttribute('data-placeholder') ||
      (placeholderOpt ? placeholderOpt.label : 'Escriba para buscar…');

    var originalClass = select.className;

    // --- Build DOM ---------------------------------------------------------
    var wrapper = document.createElement('div');
    wrapper.className = 'relative';
    select.parentNode.insertBefore(wrapper, select);
    wrapper.appendChild(select);

    // Hide the native select but keep it focusable so HTML5 validation works
    // (sr-only avoids display:none / visibility:hidden, which break .reportValidity()).
    select.classList.add('sr-only');
    select.setAttribute('tabindex', '-1');
    select.setAttribute('aria-hidden', 'true');

    var input = document.createElement('input');
    input.type = 'text';
    input.autocomplete = 'off';
    input.className = originalClass;
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-expanded', 'false');
    input.placeholder = placeholderText;
    wrapper.appendChild(input);

    var list = document.createElement('ul');
    list.setAttribute('role', 'listbox');
    // Positioned as fixed (see positionList) so it is never clipped by an
    // ancestor with overflow:hidden/auto/clip.
    list.className =
      'hidden max-h-64 overflow-y-auto bg-surface ' +
      'rounded-lg border border-outline-variant shadow-lg font-body-md text-body-md';
    wrapper.appendChild(list);

    var activeIndex = -1;
    var rendered = []; // options currently shown in the list
    var repositionHandler = null;
    // Minimum characters typed before options appear (default 3). Override with data-min-chars.
    var minChars = parseInt(select.getAttribute('data-min-chars'), 10);
    if (isNaN(minChars) || minChars < 0) minChars = 3;

    // Anchor the dropdown to the input using fixed coordinates so no
    // overflow:hidden/auto ancestor (cards, table wrappers) can clip it.
    function positionList() {
      var r = input.getBoundingClientRect();
      list.style.position = 'fixed';
      list.style.top = (r.bottom + 4) + 'px';
      list.style.left = r.left + 'px';
      list.style.width = r.width + 'px';
      list.style.zIndex = '1000';
    }

    // If a value is preselected, reflect its label in the input.
    if (select.value) {
      var sel = options.find(function (o) { return o.value === select.value; });
      if (sel) input.value = sel.label;
    }

    // --- Behaviour ---------------------------------------------------------
    function matches(query) {
      var q = normalize(query);
      var out = [];
      for (var i = 0; i < options.length; i++) {
        var opt = options[i];
        if (opt.value === '' || opt.disabled) continue; // skip placeholder / disabled
        if (!q || normalize(opt.label).indexOf(q) !== -1) {
          out.push(opt);
          if (out.length >= MAX_RESULTS) break;
        }
      }
      return out;
    }

    function close() {
      list.classList.add('hidden');
      input.setAttribute('aria-expanded', 'false');
      activeIndex = -1;
      if (repositionHandler) {
        window.removeEventListener('scroll', repositionHandler, true);
        window.removeEventListener('resize', repositionHandler);
        repositionHandler = null;
      }
    }

    function setActive(idx) {
      activeIndex = idx;
      Array.prototype.forEach.call(list.children, function (li, i) {
        if (i === idx) {
          li.classList.add('bg-surface-container-low');
          li.scrollIntoView({ block: 'nearest' });
        } else {
          li.classList.remove('bg-surface-container-low');
        }
      });
    }

    function choose(opt) {
      select.value = opt.value;
      input.value = opt.label;
      select.dispatchEvent(new Event('change', { bubbles: true }));
      close();
    }

    function render(query) {
      rendered = matches(query);
      list.innerHTML = '';

      if (rendered.length === 0) {
        var empty = document.createElement('li');
        empty.className = 'px-4 py-3 text-on-surface-variant';
        empty.textContent = 'Sin resultados';
        list.appendChild(empty);
      } else {
        rendered.forEach(function (opt, i) {
          var li = document.createElement('li');
          li.setAttribute('role', 'option');
          li.className =
            'px-4 py-2.5 cursor-pointer text-on-surface hover:bg-surface-container-low transition-colors';
          li.textContent = opt.label;
          li.addEventListener('mousedown', function (e) {
            e.preventDefault(); // keep focus, avoid blur closing first
            choose(opt);
          });
          li.addEventListener('mouseenter', function () { setActive(i); });
          list.appendChild(li);
        });
        if (rendered.length >= MAX_RESULTS) {
          var more = document.createElement('li');
          more.className = 'px-4 py-2 text-label-sm text-on-surface-variant border-t border-outline-variant';
          more.textContent = 'Mostrando los primeros ' + MAX_RESULTS + '. Refine la búsqueda…';
          list.appendChild(more);
        }
      }

      list.classList.remove('hidden');
      positionList();
      if (!repositionHandler) {
        repositionHandler = function () { positionList(); };
        window.addEventListener('scroll', repositionHandler, true);
        window.addEventListener('resize', repositionHandler);
      }
      input.setAttribute('aria-expanded', 'true');
      activeIndex = -1;
    }

    input.addEventListener('focus', function () {
      // Do not open on focus; preselect the text so typing replaces a prior choice.
      if (input.value) input.select();
    });
    input.addEventListener('input', function () {
      // Typing invalidates any prior confirmed selection until they pick again.
      select.value = '';
      if (input.value.trim().length >= minChars) {
        render(input.value);
      } else {
        close();
      }
    });

    function select_selectedLabel() {
      var s = options.find(function (o) { return o.value === select.value; });
      return s ? s.label : null;
    }

    input.addEventListener('keydown', function (e) {
      var isOpen = !list.classList.contains('hidden');
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (!isOpen) { if (input.value.trim().length >= minChars) render(input.value); return; }
        setActive(Math.min(activeIndex + 1, rendered.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (isOpen) setActive(Math.max(activeIndex - 1, 0));
      } else if (e.key === 'Enter') {
        if (isOpen && activeIndex >= 0 && rendered[activeIndex]) {
          e.preventDefault();
          choose(rendered[activeIndex]);
        }
      } else if (e.key === 'Escape') {
        close();
      }
    });

    // Restore the confirmed label if the user leaves with an unconfirmed query.
    input.addEventListener('blur', function () {
      setTimeout(function () {
        close();
        var label = select_selectedLabel();
        input.value = label || '';
      }, 120);
    });

    // Close when clicking elsewhere.
    document.addEventListener('click', function (e) {
      if (!wrapper.contains(e.target)) close();
    });
  }

  function init(root) {
    (root || document).querySelectorAll('select[data-searchable]').forEach(enhance);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { init(); });
  } else {
    init();
  }

  // Expose for dynamically injected forms.
  window.SearchableSelect = { init: init, enhance: enhance };
})();
