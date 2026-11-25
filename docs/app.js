// AI Legislation Tracker - Application Logic

(function() {
  'use strict';

  // State
  let allData = [];
  let filteredData = [];
  let activeFilters = {
    jurisdiction: 'all',
    status: 'all',
    tag: null,
    search: ''
  };
  let expandedRow = null;

  // DOM Elements
  const searchInput = document.getElementById('search-input');
  const tableBody = document.getElementById('table-body');
  const visibleCount = document.getElementById('visible-count');
  const totalCount = document.getElementById('total-count');
  const noResults = document.getElementById('no-results');
  const tagFiltersContainer = document.getElementById('tag-filters');
  const resetFiltersBtn = document.getElementById('reset-filters');
  const dataCurrency = document.getElementById('data-currency');
  const statItems = document.getElementById('stat-items');
  const statJurisdictions = document.getElementById('stat-jurisdictions');
  const statVerified = document.getElementById('stat-verified');

  // data/*.json is the single source of truth for this project. The site reads
  // it directly rather than keeping a second hand-maintained copy, so a record
  // added to the JSON always shows up here.
  const DATA_FILES = [
    { file: 'us_federal_actions.json', jurisdiction_type: 'federal' },
    { file: 'us_state_bills.json', jurisdiction_type: 'state' },
    { file: 'international_frameworks.json', jurisdiction_type: 'international' }
  ];

  // Where data/*.json can be reached from. Order matters: a same-origin copy is
  // preferred, and the repository is the fallback.
  //
  // Do NOT infer this from the hostname. This site is reachable at a
  // github.io address, at a custom domain, and from a local server, and the
  // correct answer differs in each case. GitHub Pages serves docs/ as the web
  // root, so ../data is unreachable there but works when the repository root is
  // served. Probe instead of guessing.
  const DATA_BASES = [
    '../data',
    'https://raw.githubusercontent.com/delschlangen/ai-legislation-tracker/main/data'
  ];

  // A 200 is not enough to trust a location. This site lives at
  // delschlangen.com/ai-legislation-tracker/, so the relative candidate
  // resolves to delschlangen.com/data/ — which belongs to a different
  // repository and could serve something unrelated. Require the response to
  // actually look like this dataset before accepting it.
  function looksLikeLegislation(value) {
    return Array.isArray(value) && value.length > 0 &&
           value.every(record => record && typeof record === 'object' && 'id' in record && 'status' in record);
  }

  let resolvedSource = null;

  async function resolveDataSource() {
    if (resolvedSource) return resolvedSource;

    const first = DATA_FILES[0];
    const attempts = [];

    for (const base of DATA_BASES) {
      try {
        const response = await fetch(`${base}/${first.file}`, { cache: 'no-cache' });
        if (!response.ok) {
          attempts.push(`${base} -> HTTP ${response.status}`);
          continue;
        }

        const payload = await response.json();
        if (!looksLikeLegislation(payload)) {
          attempts.push(`${base} -> responded but is not this dataset`);
          continue;
        }

        // Keep the payload so the first file is not downloaded twice.
        resolvedSource = { base, first: payload };
        return resolvedSource;
      } catch (error) {
        attempts.push(`${base} -> ${error.message || error}`);
      }
    }

    throw new Error(`Could not reach the data from any known location (${attempts.join('; ')})`);
  }

  // jurisdiction_type is derived from which file a record came from; it is what
  // the jurisdiction filter and the badge styling key on.
  function tagRecords(records, source) {
    return records.map(record => ({
      ...record,
      jurisdiction_type: source.jurisdiction_type,
      // Federal records carry issuing_body but no jurisdiction; give every
      // record one so search and display behave the same across all three files.
      jurisdiction: record.jurisdiction || record.state ||
        (source.jurisdiction_type === 'federal' ? 'US Federal' : '')
    }));
  }

  async function loadOneFile(source, base) {
    const response = await fetch(`${base}/${source.file}`, { cache: 'no-cache' });
    if (!response.ok) {
      throw new Error(`${source.file}: HTTP ${response.status}`);
    }
    const records = await response.json();
    if (!Array.isArray(records)) {
      throw new Error(`${source.file}: expected an array of records`);
    }
    return tagRecords(records, source);
  }

  // Load each file independently. One malformed file degrades to a warning and
  // the rest of the dataset still renders, rather than blanking the whole page.
  async function loadLegislation() {
    const { base, first } = await resolveDataSource();

    const settled = await Promise.allSettled(
      DATA_FILES.map((source, index) =>
        // The first file was already fetched and validated while resolving the
        // source; reuse it instead of downloading it a second time.
        index === 0
          ? Promise.resolve(tagRecords(first, source))
          : loadOneFile(source, base)
      )
    );

    const records = [];
    const failures = [];

    settled.forEach((outcome, index) => {
      if (outcome.status === 'fulfilled') {
        records.push(...outcome.value);
      } else {
        failures.push(`${DATA_FILES[index].file}: ${outcome.reason.message || outcome.reason}`);
      }
    });

    if (!records.length) {
      throw new Error(failures.join('; ') || 'No records loaded');
    }

    return { records, failures };
  }

  function getTagCounts() {
    const counts = {};
    allData.forEach(item => {
      (item.tags || []).forEach(tag => {
        counts[tag] = (counts[tag] || 0) + 1;
      });
    });
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 10);
  }

  function showLoadError(error) {
    if (dataCurrency) dataCurrency.textContent = 'Could not load data';
    const counter = document.getElementById('results-count');
    if (counter) counter.style.display = 'none';
    if (tableBody) tableBody.innerHTML = '';
    if (noResults) {
      noResults.style.display = 'block';
      noResults.innerHTML = `
        <p><strong>Could not load the legislation data.</strong></p>
        <p>${escapeHtml(error.message || String(error))}</p>
        <p>The dataset is still available directly on
          <a href="https://github.com/delschlangen/ai-legislation-tracker/tree/main/data"
             target="_blank" rel="noopener">GitHub</a>.</p>`;
    }
  }

  // Initialize
  async function init() {
    let failures = [];
    try {
      const loaded = await loadLegislation();
      allData = loaded.records;
      failures = loaded.failures;
    } catch (error) {
      console.error('Failed to load legislation data:', error);
      showLoadError(error);
      return;
    }

    filteredData = [...allData];

    totalCount.textContent = allData.length;

    renderDataStats();
    renderPartialLoadWarning(failures);
    renderTagFilters();
    renderTable();
    bindEvents();
    openRowFromHash();
  }

  // Surface a partial load rather than quietly showing an incomplete dataset.
  function renderPartialLoadWarning(failures) {
    if (!failures || !failures.length) return;
    const banner = document.createElement('p');
    banner.className = 'partial-load-warning';
    banner.textContent =
      `Some data could not be loaded, so this list is incomplete: ${failures.join('; ')}`;
    const results = document.getElementById('results-count');
    if (results && results.parentNode) {
      results.parentNode.insertBefore(banner, results);
    }
  }

  // Derive the header/footer stats from the data itself, so they can never
  // drift out of date the way the old hardcoded values did.
  function renderDataStats() {
    const jurisdictions = new Set(allData.map(getJurisdictionDisplay).filter(Boolean));

    // Only real dates count. The "needs_verification" sentinel would otherwise
    // sort after every date and be shown as the newest one.
    const verifiedDates = allData.map(item => item.last_verified).filter(isIsoDate).sort();
    const oldest = verifiedDates[0];
    const newest = verifiedDates[verifiedDates.length - 1];

    if (statItems) statItems.textContent = allData.length;
    if (statJurisdictions) statJurisdictions.textContent = jurisdictions.size;

    if (statVerified) {
      statVerified.textContent = !newest ? 'unknown'
        : oldest === newest ? newest
        : `${oldest} to ${newest}`;
    }

    // Show the span, not just the newest date. A few recently updated entries
    // must not make the whole dataset look as fresh as they are.
    if (dataCurrency) {
      const oldestMonth = oldest && formatVerifiedDate(oldest);
      const newestMonth = newest && formatVerifiedDate(newest);
      dataCurrency.textContent = !newest ? 'Verification date unknown'
        : oldestMonth === newestMonth ? `Data verified as of ${newestMonth}`
        : `Entries last verified ${oldestMonth} to ${newestMonth}`;
    }
  }

  // "2026-09-17" -> "September 2026"
  function formatVerifiedDate(iso) {
    const parts = String(iso).split('-');
    if (parts.length < 2) return iso;
    const months = ['January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December'];
    const month = months[parseInt(parts[1], 10) - 1];
    return month ? `${month} ${parts[0]}` : iso;
  }

  // Render tag filter buttons
  function renderTagFilters() {
    const topTags = getTagCounts();

    tagFiltersContainer.innerHTML = topTags.map(([tag, count]) => `
      <button type="button" class="filter-btn" data-filter="${escapeHtml(tag)}" aria-pressed="false">
        ${escapeHtml(formatTag(tag))} <span style="opacity: 0.7">(${count})</span>
      </button>
    `).join('');
  }

  // Format tag for display
  function formatTag(tag) {
    return tag
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  }

  // Render the table
  function renderTable() {
    if (filteredData.length === 0) {
      tableBody.innerHTML = '';
      noResults.style.display = 'block';
      visibleCount.textContent = '0';
      return;
    }

    noResults.style.display = 'none';
    visibleCount.textContent = filteredData.length;

    tableBody.innerHTML = filteredData.map(item => {
      const title = item.title || item.name || 'Untitled';
      // State bills show a bill number; federal and international records fall
      // back to their type, which needs prettifying ("executive_order" -> "Executive Order").
      const billNumber = item.bill_number || (item.type ? formatTag(item.type) : '');
      const rawEffectiveDate = item.effective_date || item.date_effective || item.full_application_date;
      const effectiveDate = rawEffectiveDate || '—';
      const jurisdiction = getJurisdictionDisplay(item) || '';
      const id = escapeHtml(item.id);

      // Every value that comes from the data is escaped before it is placed in
      // markup, so a record can never inject HTML. Values used as CSS classes
      // are reduced to a safe token instead.
      const statusClass = cssToken(item.status || 'unknown');
      const statusLabel = capitalizeFirst(String(item.status || 'unknown'));

      // The title is a real <button> so the row can be opened from the keyboard
      // and announced as expandable. Clicking anywhere on the row still works.
      return `
        <tr data-id="${id}" class="data-row" role="row">
          <td role="cell">
            <span class="jurisdiction-badge ${cssToken(item.jurisdiction_type)}">${escapeHtml(jurisdiction)}</span>
          </td>
          <td class="title-cell" role="cell">
            <button type="button" class="row-toggle" aria-expanded="false" aria-controls="detail-${id}">
              ${escapeHtml(title)}
              ${billNumber ? `<span class="bill-number">${escapeHtml(billNumber)}</span>` : ''}
            </button>
          </td>
          <td role="cell">
            <span class="status-badge ${statusClass}">
              <span class="status-dot ${statusClass}" aria-hidden="true"></span>
              ${escapeHtml(statusLabel)}
            </span>
          </td>
          <td role="cell" class="effective-cell${rawEffectiveDate ? '' : ' is-empty'}">${escapeHtml(effectiveDate)}</td>
          <td role="cell">
            <svg class="expand-icon" viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false">
              <path fill="currentColor" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"/>
            </svg>
          </td>
        </tr>
        <tr class="detail-row" id="detail-${id}" data-detail-for="${id}" role="row">
          <td colspan="5" role="cell">
            ${renderDetailContent(item)}
          </td>
        </tr>
      `;
    }).join('');

    // Re-bind row click events
    bindRowEvents();
  }

  // Get jurisdiction display name
  function getJurisdictionDisplay(item) {
    if (item.jurisdiction_type === 'federal') {
      return 'US Federal';
    } else if (item.jurisdiction_type === 'state') {
      return item.state || item.jurisdiction;
    } else {
      return item.jurisdiction;
    }
  }

  // Render detail content for expanded row
  function renderDetailContent(item) {
    const provisions = item.key_provisions || [];
    const tags = item.tags || [];
    const summary = item.summary || 'No summary available.';
    const sourceUrl = safeUrl(item.source_url);
    const lastVerified = item.last_verified || 'Unknown';

    return `
      <div class="detail-content">
        <div class="detail-grid">
          <div class="detail-section">
            <h4>Summary</h4>
            <p>${escapeHtml(summary)}</p>
          </div>

          <div class="detail-section">
            <h4>Key Provisions</h4>
            <ul class="provisions-list">
              ${provisions.map(p => `<li>${escapeHtml(p)}</li>`).join('')}
            </ul>
          </div>

          <div class="detail-section">
            <h4>Tags</h4>
            <div class="detail-tags">
              ${tags.map(t => `<span class="detail-tag">${escapeHtml(formatTag(t))}</span>`).join('')}
            </div>
          </div>

          <div class="detail-section">
            <h4>Official Source</h4>
            <a href="${escapeHtml(sourceUrl)}" class="source-link" target="_blank" rel="noopener noreferrer">
              <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" focusable="false">
                <path fill="currentColor" d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z"/>
                <path fill="currentColor" d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z"/>
              </svg>
              View official source
            </a>
            <p class="verified-date">Last verified: ${escapeHtml(lastVerified)}</p>
            ${renderVerificationNote(item)}
          </div>

          <div class="detail-section">
            ${renderLineage(item)}
          </div>
        </div>
      </div>
    `;
  }

  // What replaced this, or what it replaced. Tracking supersession is the thing
  // a static PDF tracker cannot do: ids are permanent, so a citation stays
  // resolvable even after the law behind it is repealed.
  function renderLineage(item) {
    const links = [];
    const label = id => {
      const target = allData.find(r => r.id === id);
      return target ? (target.title || target.name || id) : id;
    };

    if (item.superseded_by) links.push(`Superseded by <strong>${escapeHtml(label(item.superseded_by))}</strong>`);
    if (item.supersedes) links.push(`Replaces <strong>${escapeHtml(label(item.supersedes))}</strong>`);
    if (item.amended_by) links.push(`Amended by <strong>${escapeHtml(label(item.amended_by))}</strong>`);
    if (item.amends) links.push(`Amends <strong>${escapeHtml(label(item.amends))}</strong>`);

    if (!links.length) return '';
    return `<h4>Related</h4><ul class="provisions-list">${
      links.map(l => `<li>${l}</li>`).join('')}</ul>`;
  }

  // Be explicit about how an entry was checked. "secondary" means it was
  // confirmed against published legal analyses rather than the primary text.
  function renderVerificationNote(item) {
    if (item.verification === 'secondary') {
      return '<p class="verification-note">Checked against secondary legal sources; ' +
             'confirm against the official source before relying on it.</p>';
    }
    if (item.verification === 'unconfirmed') {
      return '<p class="verification-note unconfirmed">Not yet confirmed. ' +
             'Treat this entry as provisional.</p>';
    }
    return '';
  }

  // Bind event listeners
  function bindEvents() {
    // Search input
    searchInput.addEventListener('input', debounce(handleSearch, 300));

    // Jurisdiction filters
    document.getElementById('jurisdiction-filters').addEventListener('click', (e) => {
      if (e.target.classList.contains('filter-btn')) {
        setActiveButton(e.target.parentElement, e.target);
        activeFilters.jurisdiction = e.target.dataset.filter;
        applyFilters();
      }
    });

    // Status filters
    document.getElementById('status-filters').addEventListener('click', (e) => {
      if (e.target.classList.contains('filter-btn')) {
        setActiveButton(e.target.parentElement, e.target);
        activeFilters.status = e.target.dataset.filter;
        applyFilters();
      }
    });

    // Tag filters
    tagFiltersContainer.addEventListener('click', (e) => {
      const btn = e.target.closest('.filter-btn');
      if (btn) {
        const isActive = btn.classList.contains('active');
        // Only one tag can be active at a time.
        tagFiltersContainer.querySelectorAll('.filter-btn').forEach(b => setPressed(b, false));

        if (isActive) {
          activeFilters.tag = null;
        } else {
          setPressed(btn, true);
          activeFilters.tag = btn.dataset.filter;
        }
        applyFilters();
      }
    });

    // Reset filters
    resetFiltersBtn.addEventListener('click', resetFilters);

    // A link like #state-001 opens that record. Record ids are permanent, so
    // this link keeps working for as long as the record does.
    window.addEventListener('hashchange', openRowFromHash);
  }

  // Bind row click events (called after render). A keyboard press on the title
  // button fires a click that bubbles up to the row, so this one handler serves both.
  function bindRowEvents() {
    tableBody.querySelectorAll('.data-row').forEach(row => {
      row.addEventListener('click', () => toggleRowExpansion(row));
    });
  }

  function findRow(id) {
    return Array.from(tableBody.querySelectorAll('.data-row')).find(r => r.dataset.id === id) || null;
  }

  function findDetail(id) {
    return Array.from(tableBody.querySelectorAll('.detail-row')).find(r => r.dataset.detailFor === id) || null;
  }

  // Open or close one row, keeping the CSS state and the accessibility state together.
  function setExpanded(id, expanded) {
    const row = findRow(id);
    const detail = findDetail(id);
    if (!row || !detail) return;
    row.classList.toggle('expanded', expanded);
    detail.classList.toggle('visible', expanded);
    const toggle = row.querySelector('.row-toggle');
    if (toggle) toggle.setAttribute('aria-expanded', String(expanded));
  }

  // Toggle row expansion
  function toggleRowExpansion(row) {
    const id = row.dataset.id;

    // If clicking the same row, collapse it
    if (expandedRow === id) {
      setExpanded(id, false);
      expandedRow = null;
      updateHash(null);
      return;
    }

    // Collapse any previously expanded row, then expand this one
    if (expandedRow) setExpanded(expandedRow, false);
    setExpanded(id, true);
    expandedRow = id;
    updateHash(id);
  }

  // Keep the address bar pointing at the open record so it can be shared.
  function updateHash(id) {
    try {
      const url = id
        ? `#${encodeURIComponent(id)}`
        : window.location.pathname + window.location.search;
      window.history.replaceState(null, '', url);
    } catch (error) {
      // Some contexts (file://, sandboxed frames) refuse this. Sharing is a bonus.
    }
  }

  // Open the record named by the URL fragment, if there is one.
  function openRowFromHash() {
    let id = '';
    try {
      id = decodeURIComponent(window.location.hash.slice(1));
    } catch (error) {
      return;
    }
    if (!id || !allData.some(item => item.id === id)) return;

    let row = findRow(id);
    if (!row) {
      // The record exists but the current filters hide it.
      resetFilters();
      row = findRow(id);
    }
    if (!row) return;

    if (expandedRow !== id) toggleRowExpansion(row);
    row.scrollIntoView({ block: 'center' });
    const toggle = row.querySelector('.row-toggle');
    if (toggle) toggle.focus({ preventScroll: true });
  }

  // Handle search input
  function handleSearch(e) {
    activeFilters.search = e.target.value.toLowerCase().trim();
    applyFilters();
  }

  // The visual state and the accessible state of a filter button always change together.
  function setPressed(btn, pressed) {
    btn.classList.toggle('active', pressed);
    btn.setAttribute('aria-pressed', String(pressed));
  }

  // Set active button in a filter group
  function setActiveButton(container, activeBtn) {
    container.querySelectorAll('.filter-btn').forEach(btn => {
      setPressed(btn, btn === activeBtn);
    });
  }

  // Apply all active filters
  function applyFilters() {
    expandedRow = null;
    if (window.location.hash) updateHash(null);

    filteredData = allData.filter(item => {
      // Jurisdiction filter
      if (activeFilters.jurisdiction !== 'all') {
        if (item.jurisdiction_type !== activeFilters.jurisdiction) {
          return false;
        }
      }

      // Status filter — every status now has its own button, so match exactly
      if (activeFilters.status !== 'all') {
        if ((item.status || '').toLowerCase() !== activeFilters.status.toLowerCase()) {
          return false;
        }
      }

      // Tag filter
      if (activeFilters.tag) {
        if (!item.tags || !item.tags.includes(activeFilters.tag)) {
          return false;
        }
      }

      // Search filter
      if (activeFilters.search) {
        const searchTerms = activeFilters.search;
        const searchableText = [
          item.title || '',
          item.name || '',
          item.summary || '',
          item.state || '',
          item.jurisdiction || '',
          item.issuing_body || '',
          item.bill_number || '',
          item.id || '',
          item.type || '',
          item.verification || '',
          ...(item.key_provisions || []),
          ...(item.tags || [])
        ].join(' ').toLowerCase();

        if (!searchableText.includes(searchTerms)) {
          return false;
        }
      }

      return true;
    });

    renderTable();
  }

  // Reset all filters
  function resetFilters() {
    activeFilters = {
      jurisdiction: 'all',
      status: 'all',
      tag: null,
      search: ''
    };

    // Reset UI
    searchInput.value = '';

    document.querySelectorAll('.filter-buttons').forEach(group => {
      group.querySelectorAll('.filter-btn').forEach((btn, index) => {
        setPressed(btn, index === 0);
      });
    });

    tagFiltersContainer.querySelectorAll('.filter-btn').forEach(btn => {
      setPressed(btn, false);
    });

    applyFilters();
  }

  // Utility: Escape text for safe use as HTML content or inside a quoted
  // attribute. (Setting textContent and reading innerHTML escapes < > & but NOT
  // quotes, which is not enough once the value lands inside an attribute.)
  function escapeHtml(value) {
    return String(value === null || value === undefined ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Utility: Reduce a value to something safe to use as a CSS class name.
  function cssToken(value) {
    return String(value === null || value === undefined ? '' : value)
      .toLowerCase().replace(/[^a-z0-9_-]/g, '');
  }

  // Utility: Only http(s) links are ever rendered as a link target. A
  // "javascript:" URL in a data file would otherwise run when clicked.
  function safeUrl(value) {
    return typeof value === 'string' && /^https?:\/\//i.test(value.trim()) ? value.trim() : '#';
  }

  // Utility: a zero-padded calendar date, "2026-09-17"
  function isIsoDate(value) {
    return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value);
  }

  // Utility: Capitalize first letter
  function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  // Utility: Debounce function
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // Start the app
  document.addEventListener('DOMContentLoaded', init);
})();
