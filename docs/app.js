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

  function dataBaseUrl() {
    const host = location.hostname;

    // Served from the repository root (local preview): data/ is one level up.
    if (!host.endsWith('github.io')) return '../data';

    // On GitHub Pages this site is served out of docs/, which cannot reach
    // ../data. Read the canonical JSON from the repository instead. Owner and
    // repo are derived from the URL so a fork reads its own data, not ours.
    const owner = host.split('.')[0];
    const repo = location.pathname.split('/').filter(Boolean)[0] || 'ai-legislation-tracker';
    return `https://raw.githubusercontent.com/${owner}/${repo}/main/data`;
  }

  async function loadLegislation() {
    const base = dataBaseUrl();

    const groups = await Promise.all(DATA_FILES.map(async source => {
      const response = await fetch(`${base}/${source.file}`, { cache: 'no-cache' });
      if (!response.ok) {
        throw new Error(`${source.file}: HTTP ${response.status}`);
      }
      const records = await response.json();
      if (!Array.isArray(records)) {
        throw new Error(`${source.file}: expected an array of records`);
      }
      // jurisdiction_type is derived from which file a record came from; it is
      // what the jurisdiction filter and the badge styling key on.
      return records.map(record => ({
        ...record,
        jurisdiction_type: source.jurisdiction_type,
        // Federal records carry issuing_body but no jurisdiction; give every
        // record one so search and display behave the same across all three files.
        jurisdiction: record.jurisdiction || record.state ||
          (source.jurisdiction_type === 'federal' ? 'US Federal' : '')
      }));
    }));

    return groups.flat();
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
    try {
      allData = await loadLegislation();
    } catch (error) {
      console.error('Failed to load legislation data:', error);
      showLoadError(error);
      return;
    }

    filteredData = [...allData];

    totalCount.textContent = allData.length;

    renderDataStats();
    renderTagFilters();
    renderTable();
    bindEvents();
  }

  // Derive the header/footer stats from the data itself, so they can never
  // drift out of date the way the old hardcoded values did.
  function renderDataStats() {
    const jurisdictions = new Set(allData.map(getJurisdictionDisplay).filter(Boolean));

    const verifiedDates = allData.map(item => item.last_verified).filter(Boolean).sort();
    const oldest = verifiedDates[0];
    const newest = verifiedDates[verifiedDates.length - 1];

    if (statItems) statItems.textContent = allData.length;
    if (statJurisdictions) statJurisdictions.textContent = jurisdictions.size;

    if (statVerified) {
      statVerified.textContent = !newest ? 'unknown'
        : oldest === newest ? newest
        : `${oldest} to ${newest}`;
    }

    if (dataCurrency) {
      dataCurrency.textContent = newest
        ? `Data verified as of ${formatVerifiedDate(newest)}`
        : 'Verification date unknown';
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
      <button class="filter-btn" data-filter="${tag}">
        ${formatTag(tag)} <span style="opacity: 0.7">(${count})</span>
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
      const title = item.title || item.name;
      // State bills show a bill number; federal and international records fall
      // back to their type, which needs prettifying ("executive_order" -> "Executive Order").
      const billNumber = item.bill_number || (item.type ? formatTag(item.type) : '');
      const effectiveDate = item.effective_date || item.date_effective || item.full_application_date || '—';
      const jurisdictionType = item.jurisdiction_type;
      const jurisdiction = getJurisdictionDisplay(item);

      const status = item.status || 'unknown';

      return `
        <tr data-id="${item.id}" class="data-row">
          <td>
            <span class="jurisdiction-badge ${jurisdictionType}">${jurisdiction}</span>
          </td>
          <td class="title-cell">
            ${escapeHtml(title)}
            ${billNumber ? `<span class="bill-number">${escapeHtml(billNumber)}</span>` : ''}
          </td>
          <td>
            <span class="status-badge ${status}">
              <span class="status-dot ${status}"></span>
              ${capitalizeFirst(status)}
            </span>
          </td>
          <td>${effectiveDate}</td>
          <td>
            <svg class="expand-icon" viewBox="0 0 20 20" width="20" height="20">
              <path fill="currentColor" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"/>
            </svg>
          </td>
        </tr>
        <tr class="detail-row" data-detail-for="${item.id}">
          <td colspan="5">
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
    const sourceUrl = item.source_url || '#';
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
            <a href="${escapeHtml(sourceUrl)}" class="source-link" target="_blank" rel="noopener">
              <svg viewBox="0 0 20 20" width="16" height="16">
                <path fill="currentColor" d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z"/>
                <path fill="currentColor" d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z"/>
              </svg>
              View official source
            </a>
            <p class="verified-date">Last verified: ${escapeHtml(lastVerified)}</p>
            ${renderVerificationNote(item)}
          </div>
        </div>
      </div>
    `;
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
        // Remove active from all tag buttons
        tagFiltersContainer.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));

        if (isActive) {
          activeFilters.tag = null;
        } else {
          btn.classList.add('active');
          activeFilters.tag = btn.dataset.filter;
        }
        applyFilters();
      }
    });

    // Reset filters
    resetFiltersBtn.addEventListener('click', resetFilters);
  }

  // Bind row click events (called after render)
  function bindRowEvents() {
    tableBody.querySelectorAll('.data-row').forEach(row => {
      row.addEventListener('click', () => toggleRowExpansion(row));
    });
  }

  // Toggle row expansion
  function toggleRowExpansion(row) {
    const id = row.dataset.id;
    const detailRow = document.querySelector(`[data-detail-for="${id}"]`);

    // If clicking the same row, collapse it
    if (expandedRow === id) {
      row.classList.remove('expanded');
      detailRow.classList.remove('visible');
      expandedRow = null;
      return;
    }

    // Collapse any previously expanded row
    if (expandedRow) {
      const prevRow = document.querySelector(`[data-id="${expandedRow}"]`);
      const prevDetail = document.querySelector(`[data-detail-for="${expandedRow}"]`);
      if (prevRow) prevRow.classList.remove('expanded');
      if (prevDetail) prevDetail.classList.remove('visible');
    }

    // Expand the clicked row
    row.classList.add('expanded');
    detailRow.classList.add('visible');
    expandedRow = id;
  }

  // Handle search input
  function handleSearch(e) {
    activeFilters.search = e.target.value.toLowerCase().trim();
    applyFilters();
  }

  // Set active button in a filter group
  function setActiveButton(container, activeBtn) {
    container.querySelectorAll('.filter-btn').forEach(btn => {
      btn.classList.remove('active');
    });
    activeBtn.classList.add('active');
  }

  // Apply all active filters
  function applyFilters() {
    expandedRow = null;

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
          item.type || '',
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
        btn.classList.toggle('active', index === 0);
      });
    });

    tagFiltersContainer.querySelectorAll('.filter-btn').forEach(btn => {
      btn.classList.remove('active');
    });

    applyFilters();
  }

  // Utility: Escape HTML
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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
