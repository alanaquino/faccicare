/*
 * live-filter.js
 * Client-side "type to filter" for list pages — no need to press Buscar/Filtrar.
 * Mirrors the searchable-select behaviour: filtering starts at the 3rd character,
 * accent-insensitive, instant.
 *
 * Usage:
 *   <input data-live-filter>                       -> filters "table tbody tr" (default)
 *   <input data-live-filter="#grid > div">         -> filters the given rows
 *   <tr data-no-filter>...</tr>                     -> never hidden (headers, empty-state)
 *   <tr data-filter-text="extra terms">            -> custom searchable text
 *   <select data-autosubmit>                        -> submits its form on change (no button)
 */
(function () {
  'use strict';

  var MIN_CHARS = 3;

  function normalize(text) {
    return (text || '')
      .toString()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '');
  }

  function apply(input) {
    var selector = input.getAttribute('data-live-filter') || 'table tbody tr';
    var rows = document.querySelectorAll(selector);
    var q = normalize(input.value.trim());
    var filtering = q.length >= MIN_CHARS;

    rows.forEach(function (row) {
      if (row.hasAttribute('data-no-filter')) return;
      var text = normalize(row.getAttribute('data-filter-text') || row.textContent);
      var show = !filtering || text.indexOf(q) !== -1;
      row.style.display = show ? '' : 'none';
    });
  }

  function init(root) {
    (root || document).querySelectorAll('input[data-live-filter]').forEach(function (input) {
      input.addEventListener('input', function () { apply(input); });
      if (input.value.trim()) apply(input); // re-apply a server-prefilled value
    });
    (root || document).querySelectorAll('[data-autosubmit]').forEach(function (el) {
      el.addEventListener('change', function () { if (el.form) el.form.submit(); });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { init(); });
  } else {
    init();
  }

  window.LiveFilter = { apply: apply, init: init };
})();
