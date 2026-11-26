// AI Legislation Tracker - Application Logic

(function() {
  'use strict';

  // ---------------------------------------------------------------------------
  // Constants
  // ---------------------------------------------------------------------------

  // Statuses that mean an instrument is law or policy now, once its date has come.
  // query_legislation.py --in-force and generate_dashboard.py use the same rule.
  const IN_FORCE_STATUSES = new Set(['enacted', 'active', 'adopted']);

  // Logical order for sorting by status: in force first, then the rest.
  const STATUS_ORDER = ['enacted', 'active', 'adopted', 'pending', 'enjoined',
                        'vetoed', 'rescinded', 'superseded', 'expired'];

  const JURISDICTION_TYPES = new Set(['all', 'federal', 'state', 'international']);

  const SORTS = {
    '': 'As published',
    'effective-asc': 'Effective date, soonest first',
    'effective-desc': 'Effective date, latest first',
    'jurisdiction': 'Jurisdiction, A to Z',
    'title': 'Name, A to Z',
    'status': 'Status'
  };

  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December'];
  const MONTHS_SHORT = MONTHS.map(m => m.slice(0, 3));

  const DEFAULT_FILTERS = { jurisdiction: 'all', status: 'all', tag: null, search: '', inForce: false };

  // A record's own dates, in the order they usually happen: the field, what to
  // call it once the date has come, and what to call it while it is still ahead.
  // The last name is for a date still to come that the record's status says
  // will not arrive, such as the expiry date of a bill that was vetoed.
  const LIFECYCLE_DATES = [
    ['date_introduced', 'Introduced', 'To be introduced', 'Introduction date in the text'],
    ['date_issued', 'Issued', 'To be issued', 'Issue date in the text'],
    ['date_adopted', 'Adopted', 'To be adopted', 'Adoption date in the text'],
    ['date_enacted', 'Enacted', 'To be enacted', 'Enactment date in the text'],
    ['date_vetoed', 'Vetoed', 'To be vetoed', 'Veto date in the text'],
    ['date_enjoined', 'Enforcement blocked by a court', 'Enforcement to be blocked by a court',
     'Injunction date in the text'],
    ['date_rescinded', 'Rescinded', 'To be rescinded', 'Rescission date in the text'],
    ['date_superseded', 'Superseded', 'To be superseded', 'Supersession date in the text'],
    ['date_expired', 'Expired', 'Expires', 'Expiry date in the text']
  ];

  // How Key Dates words a stage (an effective date, a full-application date or
  // a milestone): once it has passed, and when it is only what the text says
  // because the record's status means the stage did not, or will not, arrive.
  const PAST_TENSE = { 'Takes effect': 'Took effect', 'Applies in full': 'Applied in full' };
  const AS_WRITTEN = { 'Takes effect': 'Effective date in the text',
                       'Applies in full': 'Full application date in the text' };

  // The date a record stopped applying, by status. A stage dated before it was
  // reached, if the record also shows the law was made by then. "expired" also
  // covers a bill that died without being enacted, which reached no stage.
  // Pending and vetoed are absent: none of their stages ever arrived.
  const END_DATE_BY_STATUS = new Map([
    ['enjoined', 'date_enjoined'], ['rescinded', 'date_rescinded'],
    ['superseded', 'date_superseded'], ['expired', 'date_expired']
  ]);

  // Dates that show a record became law. Adopting a treaty does not bring it
  // into force, so date_adopted does not count for a treaty.
  const BECAME_LAW_DATES = ['date_enacted', 'date_issued', 'date_adopted'];

  // The overview lists that hold links to records. See describeLink().
  const LINK_LISTS = ['upcoming-list', 'changes-list'];

  // Today's date where the reader is, as YYYY-MM-DD. Every "in force" and
  // "coming up" judgement on the page is computed from this and the data, so
  // nothing on the page has to be updated by hand when a date passes.
  const TODAY = (function() {
    const now = new Date();
    const pad = n => String(n).padStart(2, '0');
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  })();

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  let allData = [];
  let filteredData = [];
  let activeFilters = Object.assign({}, DEFAULT_FILTERS);
  let sortKey = '';
  let expandedRow = null;
  // The timer for a search that is still being typed, or null. See scheduleSearch().
  let searchTimer = null;
  // False once the browser has refused to let the address be rewritten. The
  // address then no longer says what the filters are, so it is not read back.
  let addressWritable = true;

  // ---------------------------------------------------------------------------
  // DOM
  // ---------------------------------------------------------------------------

  const searchInput = document.getElementById('search-input');
  const tableBody = document.getElementById('table-body');
  const visibleCount = document.getElementById('visible-count');
  const totalCount = document.getElementById('total-count');
  const noResults = document.getElementById('no-results');
  const jurisdictionFilters = document.getElementById('jurisdiction-filters');
  const statusFilters = document.getElementById('status-filters');
  const tagFiltersContainer = document.getElementById('tag-filters');
  const inForceToggle = document.getElementById('in-force-toggle');
  const sortSelect = document.getElementById('sort-select');
  const resetFiltersBtn = document.getElementById('reset-filters');
  const dataCurrency = document.getElementById('data-currency');
  const statItems = document.getElementById('stat-items');
  const statJurisdictions = document.getElementById('stat-jurisdictions');
  const statVerified = document.getElementById('stat-verified');
  const upcomingList = document.getElementById('upcoming-list');
  const changesCard = document.getElementById('changes-card');
  const changesList = document.getElementById('changes-list');

  // ---------------------------------------------------------------------------
  // Loading
  // ---------------------------------------------------------------------------

  // data/*.json is the single source of truth for this project. The site reads
  // it directly rather than keeping a second hand-maintained copy, so a record
  // added to the JSON always shows up here.
  const DATA_FILES = [
    { file: 'us_federal_actions.json', jurisdiction_type: 'federal' },
    { file: 'us_state_bills.json', jurisdiction_type: 'state' },
    { file: 'international_frameworks.json', jurisdiction_type: 'international' }
  ];

  // The hand-written log of what changed and when. Optional: the page works
  // without it and simply hides the "Recently changed" card.
  const CHANGELOG_FILE = 'meta/changelog.json';

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
    return records.map((record, index) => ({
      ...record,
      jurisdiction_type: source.jurisdiction_type,
      // Federal records carry issuing_body but no jurisdiction; give every
      // record one so search and display behave the same across all three files.
      jurisdiction: record.jurisdiction || record.state ||
        (source.jurisdiction_type === 'federal' ? 'US Federal' : ''),
      _order: 0,
      _fileIndex: index
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

    // Remember the published order so "As published" can restore it after sorting.
    records.forEach((record, index) => { record._order = index; });

    return { records, failures, base };
  }

  async function loadChangelog(base) {
    try {
      const response = await fetch(`${base}/${CHANGELOG_FILE}`, { cache: 'no-cache' });
      if (!response.ok) return [];
      const entries = await response.json();
      return Array.isArray(entries) ? entries.filter(e => e && typeof e === 'object') : [];
    } catch (error) {
      return [];
    }
  }

  function showLoadError(error) {
    if (dataCurrency) dataCurrency.textContent = 'Could not load data';
    const counter = document.getElementById('results-count');
    if (counter) counter.style.display = 'none';
    if (tableBody) tableBody.innerHTML = '';
    if (upcomingList) upcomingList.innerHTML = '<li class="overview-empty">Data unavailable.</li>';
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

  // ---------------------------------------------------------------------------
  // Initialise
  // ---------------------------------------------------------------------------

  async function init() {
    let loaded;
    try {
      loaded = await loadLegislation();
    } catch (error) {
      console.error('Failed to load legislation data:', error);
      showLoadError(error);
      return;
    }

    allData = loaded.records;
    totalCount.textContent = allData.length;

    renderDataStats();
    renderPartialLoadWarning(loaded.failures);
    renderStatusCounts();
    renderTagFilters();
    renderSortOptions();
    renderUpcoming();

    readUrlState();
    syncControls();
    // The first render must not touch the address bar: the fragment naming a
    // record has not been read yet, and rewriting the URL would erase it.
    applyFilters({ keepHash: true, leaveUrl: true });

    bindEvents();
    openRowFromHash();
    // Tidy the address bar: drop parameters that were ignored as invalid.
    if (!expandedRow) writeUrlState();

    // The change log is secondary; load it without holding up the table.
    loadChangelog(loaded.base).then(renderChanges);
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
      const oldestMonth = oldest && formatMonth(oldest);
      const newestMonth = newest && formatMonth(newest);
      dataCurrency.textContent = !newest ? 'Verification date unknown'
        : oldestMonth === newestMonth ? `Data verified as of ${newestMonth}`
        : `Entries last verified ${oldestMonth} to ${newestMonth}`;
    }
  }

  // ---------------------------------------------------------------------------
  // Dates computed from the data
  // ---------------------------------------------------------------------------

  // Every dated stage of a record, oldest first: its milestones, plus the
  // effective and full-application dates when no milestone already gives them.
  function keyDates(item) {
    const dates = [];
    const seen = new Set();
    (Array.isArray(item.milestones) ? item.milestones : []).forEach(milestone => {
      if (milestone && isIsoDate(milestone.date)) {
        dates.push({ date: milestone.date, what: String(milestone.description || '') });
        seen.add(milestone.date);
      }
    });
    [['effective_date', 'Takes effect'], ['full_application_date', 'Applies in full']].forEach(([field, label]) => {
      if (isIsoDate(item[field]) && !seen.has(item[field])) {
        dates.push({ date: item[field], what: label });
        seen.add(item[field]);
      }
    });
    return dates.sort((a, b) => compareStrings(a.date, b.date));
  }

  function effectiveDateOf(item) {
    return item.effective_date || item.date_effective || item.full_application_date || '';
  }

  // In force today: an in-force status, and no effective date still to come.
  function isInForce(item) {
    if (!IN_FORCE_STATUSES.has(String(item.status || '').toLowerCase())) return false;
    const effective = item.effective_date;
    return !(isIsoDate(effective) && effective > TODAY);
  }

  function isNotYetInForce(item) {
    return IN_FORCE_STATUSES.has(String(item.status || '').toLowerCase()) &&
           isIsoDate(item.effective_date) && item.effective_date > TODAY;
  }

  // The next stage still to come, for laws already in force that apply in phases.
  function nextStage(item) {
    if (!IN_FORCE_STATUSES.has(String(item.status || '').toLowerCase())) return null;
    return keyDates(item).find(d => d.date > TODAY) || null;
  }

  // Upcoming dates across the whole dataset. Only instruments that are law or
  // policy count: a superseded or vetoed law's old dates will never arrive.
  function upcomingDates(limit) {
    const items = [];
    allData.forEach(item => {
      if (!IN_FORCE_STATUSES.has(String(item.status || '').toLowerCase())) return;
      keyDates(item).forEach(d => {
        if (d.date > TODAY) items.push({ date: d.date, what: d.what, item });
      });
    });
    items.sort((a, b) => compareStrings(a.date, b.date) || a.item._order - b.item._order);
    return items.slice(0, limit);
  }

  // ---------------------------------------------------------------------------
  // Overview cards
  // ---------------------------------------------------------------------------

  function renderUpcoming() {
    if (!upcomingList) return;
    const upcoming = upcomingDates(6);
    if (!upcoming.length) {
      upcomingList.innerHTML = '<li class="overview-empty">No upcoming dates are recorded.</li>';
      return;
    }
    upcomingList.innerHTML = upcoming.map(({ date, what, item }) => `
      <li class="timeline-item">
        <time class="timeline-date" datetime="${escapeHtml(date)}">${escapeHtml(formatDay(date))}</time>
        <span class="timeline-countdown">${escapeHtml(countdown(date))}</span>
        <span class="timeline-body">
          ${recordLink(item)}
          <span class="timeline-jurisdiction">${escapeHtml(getJurisdictionDisplay(item) || '')}</span>
          <span class="timeline-what">${escapeHtml(what)}</span>
        </span>
      </li>`).join('');
  }

  function renderChanges(entries) {
    if (!changesCard || !changesList) return;
    const byId = new Map(allData.map(item => [item.id, item]));
    const recent = entries
      .filter(entry => isIsoDate(entry.date))
      .slice(0, 4);
    if (!recent.length) return;

    const chips = (ids, kind) => {
      const known = (Array.isArray(ids) ? ids : []).filter(id => byId.has(id));
      const shown = known.slice(0, 3).map(id =>
        `<li><span class="change-kind ${kind}">${kind === 'added' ? 'Added' : 'Updated'}</span> ${recordLink(byId.get(id))}</li>`);
      if (known.length > 3) {
        shown.push(`<li class="change-more">and ${known.length - 3} more ${kind === 'added' ? 'added' : 'updated'}</li>`);
      }
      return shown.join('');
    };

    changesList.innerHTML = recent.map(entry => `
      <li class="change-entry">
        <time class="timeline-date" datetime="${escapeHtml(entry.date)}">${escapeHtml(formatDay(entry.date))}</time>
        <p class="change-summary">${escapeHtml(entry.summary || '')}</p>
        <ul class="change-records">${chips(entry.added, 'added')}${chips(entry.updated, 'updated')}</ul>
      </li>`).join('');
    changesCard.hidden = false;
  }

  // A link that opens a record in the table. Ids are permanent, so the link is too.
  function recordLink(item) {
    const title = item.title || item.name || item.id;
    return `<a class="record-link" href="#${encodeURIComponent(item.id)}">${escapeHtml(title)}</a>`;
  }

  // ---------------------------------------------------------------------------
  // Filter controls
  // ---------------------------------------------------------------------------

  // Show how many records each status has, and hide statuses no record uses.
  // A status button appears by itself once a record needs it.
  function renderStatusCounts() {
    const counts = {};
    allData.forEach(item => {
      const status = String(item.status || '').toLowerCase();
      counts[status] = (counts[status] || 0) + 1;
    });
    statusFilters.querySelectorAll('.filter-btn').forEach(btn => {
      const status = btn.dataset.filter;
      if (status === 'all') return;
      const count = counts[status] || 0;
      const label = btn.dataset.label || btn.textContent.trim();
      btn.dataset.label = label;
      btn.dataset.count = String(count);
      btn.innerHTML = `${escapeHtml(label)} <span class="filter-count">(${count})</span>`;
      btn.hidden = count === 0;
    });
  }

  // Pressed state for the status buttons, and which of them are shown: a status
  // no record uses stays hidden unless it is the one selected, for example from
  // a shared link. It hides again as soon as another status is chosen.
  function syncStatusButtons() {
    statusFilters.querySelectorAll('.filter-btn').forEach(btn => {
      const active = btn.dataset.filter === activeFilters.status;
      setPressed(btn, active);
      btn.hidden = !active && btn.dataset.count === '0';
    });
  }

  function getTagCounts() {
    const counts = {};
    allData.forEach(item => {
      (Array.isArray(item.tags) ? item.tags : []).forEach(tag => {
        counts[tag] = (counts[tag] || 0) + 1;
      });
    });
    return Object.entries(counts).sort((a, b) => b[1] - a[1] || compareStrings(a[0], b[0])).slice(0, 10);
  }

  function renderTagFilters() {
    tagFiltersContainer.innerHTML = getTagCounts().map(([tag, count]) => `
      <button type="button" class="filter-btn" data-filter="${escapeHtml(tag)}" aria-pressed="false">
        ${escapeHtml(formatTag(tag))} <span class="filter-count">(${count})</span>
      </button>
    `).join('');
  }

  function renderSortOptions() {
    if (!sortSelect) return;
    sortSelect.innerHTML = Object.entries(SORTS)
      .map(([value, label]) => `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`)
      .join('');
  }

  // Make every control show the current state, for example after reading it
  // from the address bar.
  function syncControls() {
    jurisdictionFilters.querySelectorAll('.filter-btn').forEach(btn =>
      setPressed(btn, btn.dataset.filter === activeFilters.jurisdiction));

    syncStatusButtons();

    tagFiltersContainer.querySelectorAll('.filter-btn').forEach(btn =>
      setPressed(btn, btn.dataset.filter === activeFilters.tag));

    if (inForceToggle) setPressed(inForceToggle, activeFilters.inForce);
    if (sortSelect) sortSelect.value = sortKey;
    searchInput.value = activeFilters.search;
  }

  // ---------------------------------------------------------------------------
  // Address bar: filters in the query string, the open record in the fragment.
  // A copied link reproduces exactly what the reader was looking at.
  // ---------------------------------------------------------------------------

  function readUrlState() {
    let params;
    try {
      params = new URLSearchParams(window.location.search);
    } catch (error) {
      return;
    }
    const knownStatuses = new Set(Array.from(statusFilters.querySelectorAll('.filter-btn')).map(b => b.dataset.filter));

    const jurisdiction = params.get('jurisdiction');
    if (jurisdiction && JURISDICTION_TYPES.has(jurisdiction)) activeFilters.jurisdiction = jurisdiction;

    const status = params.get('status');
    if (status && knownStatuses.has(status)) activeFilters.status = status;

    const tag = params.get('tag');
    if (tag && allData.some(item => Array.isArray(item.tags) && item.tags.includes(tag))) {
      activeFilters.tag = tag;
      ensureTagButton(tag);
    }

    const query = (params.get('q') || '').trim().slice(0, 200);
    if (query) activeFilters.search = query;

    activeFilters.inForce = params.get('in_force') === '1';

    const sort = params.get('sort');
    if (sort && Object.prototype.hasOwnProperty.call(SORTS, sort)) sortKey = sort;
  }

  // A shared link may name a tag outside the ten most common. Give it a button
  // so the reader can see the filter is on and turn it off.
  function ensureTagButton(tag) {
    const exists = Array.from(tagFiltersContainer.querySelectorAll('.filter-btn')).some(b => b.dataset.filter === tag);
    if (exists) return;
    const count = allData.filter(item => Array.isArray(item.tags) && item.tags.includes(tag)).length;
    tagFiltersContainer.insertAdjacentHTML('beforeend', `
      <button type="button" class="filter-btn" data-filter="${escapeHtml(tag)}" aria-pressed="false">
        ${escapeHtml(formatTag(tag))} <span class="filter-count">(${count})</span>
      </button>`);
  }

  function writeUrlState() {
    const params = new URLSearchParams();
    if (activeFilters.jurisdiction !== 'all') params.set('jurisdiction', activeFilters.jurisdiction);
    if (activeFilters.status !== 'all') params.set('status', activeFilters.status);
    if (activeFilters.tag) params.set('tag', activeFilters.tag);
    if (activeFilters.search) params.set('q', activeFilters.search);
    if (activeFilters.inForce) params.set('in_force', '1');
    if (sortKey) params.set('sort', sortKey);

    const query = params.toString();
    const hash = expandedRow ? `#${encodeURIComponent(expandedRow)}` : '';
    try {
      // Keep the entry's state: it remembers which link the reader left this view by.
      window.history.replaceState(window.history.state, '',
        window.location.pathname + (query ? `?${query}` : '') + hash);
    } catch (error) {
      // Some contexts (file://, sandboxed frames) refuse this. Sharing is a bonus.
      addressWritable = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Table
  // ---------------------------------------------------------------------------

  function renderTable() {
    updateSortIndicators();

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
      const rawEffectiveDate = effectiveDateOf(item);
      const effectiveDate = rawEffectiveDate || '—';
      const jurisdiction = getJurisdictionDisplay(item) || '';
      const id = escapeHtml(item.id);
      const upcoming = nextStage(item);
      const showNext = upcoming && upcoming.date !== rawEffectiveDate;

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
          <td role="cell" class="status-cell">
            <span class="status-badge ${statusClass}">
              <span class="status-dot ${statusClass}" aria-hidden="true"></span>
              ${escapeHtml(statusLabel)}
            </span>
            ${isNotYetInForce(item) ? '<span class="status-note">Not yet in force</span>' : ''}
          </td>
          <td role="cell" class="effective-cell${rawEffectiveDate ? '' : ' is-empty'}">
            ${escapeHtml(effectiveDate)}
            ${showNext ? `<span class="next-stage">Next stage ${escapeHtml(upcoming.date)}</span>` : ''}
          </td>
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

    bindRowEvents();
  }

  function updateSortIndicators() {
    const columns = { jurisdiction: 'col-jurisdiction', title: 'col-title', status: 'col-status',
                      'effective-asc': 'col-effective', 'effective-desc': 'col-effective' };
    document.querySelectorAll('.legislation-table thead th').forEach(th => th.removeAttribute('aria-sort'));
    const column = columns[sortKey];
    if (!column) return;
    const th = document.querySelector(`.legislation-table thead th.${column}`);
    if (th) th.setAttribute('aria-sort', sortKey === 'effective-desc' ? 'descending' : 'ascending');
  }

  function getJurisdictionDisplay(item) {
    if (item.jurisdiction_type === 'federal') return 'US Federal';
    if (item.jurisdiction_type === 'state') return item.state || item.jurisdiction;
    return item.jurisdiction;
  }

  function renderDetailContent(item) {
    const provisions = Array.isArray(item.key_provisions) ? item.key_provisions : [];
    const tags = Array.isArray(item.tags) ? item.tags : [];
    const summary = item.summary || 'No summary available.';
    const sourceUrl = safeUrl(item.source_url);
    const lastVerified = item.last_verified || 'Unknown';

    return `
      <div class="detail-content">
        <div class="detail-grid">
          <div class="detail-section">
            <h4>Summary</h4>
            <p>${escapeHtml(summary)}</p>
            ${renderInjunction(item)}
          </div>

          <div class="detail-section">
            <h4>Key Provisions</h4>
            <ul class="provisions-list">
              ${provisions.map(p => `<li>${escapeHtml(p)}</li>`).join('')}
            </ul>
          </div>

          ${renderKeyDates(item)}

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
            <p class="verified-date">Last verified: ${escapeHtml(lastVerified)} · Record id <code>${escapeHtml(item.id)}</code></p>
            ${renderVerificationNote(item)}
          </div>

          ${renderLineage(item)}
        </div>
      </div>
    `;
  }

  function renderInjunction(item) {
    if (!item.injunction) return '';
    return `<p class="injunction-note"><strong>Court action:</strong> ${escapeHtml(item.injunction)}</p>`;
  }

  // Whether a stage can be stated as something that happened or will happen:
  //   'live'     the record is law or policy, so its dates arrive as written
  //   'reached'  the law has since ended, but this stage came first
  //   'moot'     the date is only what the text says: the bill is pending or
  //              was vetoed, or the law ended before this stage
  // "Coming up" and "Next stage" apply the same idea by listing live records only.
  function stageStanding(item, date) {
    const status = String(item.status || '').toLowerCase();
    if (IN_FORCE_STATUSES.has(status)) return 'live';
    const endField = END_DATE_BY_STATUS.get(status);
    const ended = endField ? item[endField] : null;
    const becameLaw = BECAME_LAW_DATES.some(field =>
      isIsoDate(item[field]) && item[field] <= date && !(field === 'date_adopted' && item.type === 'treaty'));
    return becameLaw && isIsoDate(ended) && date < ended && date < TODAY ? 'reached' : 'moot';
  }

  // Whether a record's own lifecycle date (introduced, enacted, expired...)
  // is something that happened or will happen, judged from its status the
  // same way whatever the reader's date, as stageStanding does for stages:
  //   in force    every date stands
  //   enjoined    every date stands: the law still exists, only its enforcement is blocked
  //   pending     only its introduction, issue or adoption: it is not law yet
  //   ended       vetoed, rescinded, superseded or expired: the date that ended it,
  //               and dates up to it. Anything after it will not happen
  function lifecycleIsEvent(item, field, date) {
    const status = String(item.status || '').toLowerCase();
    if (IN_FORCE_STATUSES.has(status) || status === 'enjoined') return true;
    if (status === 'pending') return ['date_introduced', 'date_issued', 'date_adopted'].includes(field);
    const ownEnd = status === 'vetoed' ? 'date_vetoed' : END_DATE_BY_STATUS.get(status);
    if (field === ownEnd) return true;
    const ended = ownEnd ? item[ownEnd] : null;
    return isIsoDate(ended) ? date <= ended : date <= TODAY;
  }

  // Every date a record carries, one row per date, oldest first: its own
  // lifecycle dates, plus each stage from keyDates(). Lifecycle dates stay out
  // of keyDates() itself, which feeds "Coming up" and "Next stage".
  // `ahead` marks a date that is still expected to arrive.
  function recordDates(item) {
    const byDate = new Map();
    const add = (date, what, expected) => {
      if (!isIsoDate(date) || !what) return;
      if (!byDate.has(date)) byDate.set(date, { what: [], expected: false });
      const entry = byDate.get(date);
      if (!entry.what.includes(what)) entry.what.push(what);
      if (expected) entry.expected = true;
    };
    LIFECYCLE_DATES.forEach(([field, past, future, asWritten]) => {
      const date = item[field];
      if (lifecycleIsEvent(item, field, date)) {
        add(date, date > TODAY ? future : past, true);
      } else {
        // Neither a fact nor a countdown, before, on or after the day itself.
        add(date, asWritten, false);
      }
    });
    keyDates(item).forEach(d => {
      if (!d.what) return;
      const standing = stageStanding(item, d.date);
      if (standing === 'moot') {
        // Neither "took effect" nor a countdown: this stage is not arriving.
        add(d.date, AS_WRITTEN[d.what] || `In the text: ${d.what}`, false);
      } else {
        add(d.date, d.date >= TODAY ? d.what : (PAST_TENSE[d.what] || d.what), standing === 'live');
      }
    });
    return Array.from(byDate.keys()).sort(compareStrings).map(date => {
      const entry = byDate.get(date);
      return { date, what: entry.what, ahead: date >= TODAY && entry.expected };
    });
  }

  // Dates still to come carry a countdown. The rest are shown muted: dates that
  // have passed, and dates that will not arrive.
  function renderKeyDates(item) {
    const dates = recordDates(item);
    if (!dates.length) return '';
    return `
      <div class="detail-section">
        <h4>Key Dates</h4>
        <ol class="key-dates">
          ${dates.map(d => `<li class="${d.ahead ? 'is-future' : 'is-past'}">
              <time datetime="${escapeHtml(d.date)}">${escapeHtml(d.date)}</time>
              <span>${d.what.map(escapeHtml).join(' · ')}</span>
              ${d.ahead ? `<span class="key-date-state">${escapeHtml(countdown(d.date))}</span>` : ''}
            </li>`).join('')}
        </ol>
      </div>`;
  }

  // The full line of succession, oldest first, with this record marked. Ids are
  // permanent, so a citation to any link in the chain still resolves and shows
  // what replaced it. Amendments are listed separately.
  function supersessionChain(item) {
    const byId = new Map(allData.map(record => [record.id, record]));
    let start = item;
    const seen = new Set([item.id]);
    while (start.supersedes && byId.has(start.supersedes) && !seen.has(start.supersedes)) {
      start = byId.get(start.supersedes);
      seen.add(start.id);
    }
    const chain = [start];
    const visited = new Set([start.id]);
    let current = start;
    while (current.superseded_by && byId.has(current.superseded_by) && !visited.has(current.superseded_by)) {
      current = byId.get(current.superseded_by);
      visited.add(current.id);
      chain.push(current);
    }
    return chain;
  }

  function renderLineage(item) {
    const byId = new Map(allData.map(record => [record.id, record]));
    const parts = [];

    const chain = supersessionChain(item);
    if (chain.length > 1) {
      parts.push(`<p class="lineage-label">Line of succession, oldest first</p>
        <ol class="lineage-chain">${chain.map(link => {
          const when = link.date_superseded || link.date_rescinded || '';
          const status = capitalizeFirst(String(link.status || ''));
          const meta = escapeHtml(status) + (when ? ` ${escapeHtml(when)}` : '');
          return link.id === item.id
            ? `<li aria-current="true"><strong>${escapeHtml(link.title || link.id)}</strong> <span class="lineage-meta">${meta} · this record</span></li>`
            : `<li>${recordLink(link)} <span class="lineage-meta">${meta}</span></li>`;
        }).join('')}</ol>`);
    }

    const amendments = [];
    if (item.amends && byId.has(item.amends)) amendments.push(`Amends ${recordLink(byId.get(item.amends))}`);
    if (item.amended_by && byId.has(item.amended_by)) amendments.push(`Amended by ${recordLink(byId.get(item.amended_by))}`);
    if (amendments.length) {
      parts.push(`<ul class="provisions-list">${amendments.map(a => `<li>${a}</li>`).join('')}</ul>`);
    }

    if (!parts.length) return '';
    return `<div class="detail-section"><h4>Related</h4>${parts.join('')}</div>`;
  }

  // Be explicit about how an entry was checked. "secondary" means it was
  // confirmed against published legal analyses rather than the primary text.
  // Every record says how it was last checked, so the least-checked entries
  // never look like the best-checked ones. MAINTENANCE.md defines each level.
  function renderVerificationNote(item) {
    if (item.last_verified === 'needs_verification') {
      return '<p class="verification-note unchecked">Never checked. Treat this entry as provisional ' +
             'and confirm it against the official source.</p>';
    }
    switch (item.verification) {
      case 'primary':
        return '<p class="verification-note">Confirmed against the official text.</p>';
      case 'secondary':
        return '<p class="verification-note">Checked against secondary legal sources; ' +
               'confirm against the official source before relying on it.</p>';
      case 'unconfirmed':
        return '<p class="verification-note unconfirmed">Not yet confirmed. ' +
               'Treat this entry as provisional.</p>';
      default:
        return '<p class="verification-note unchecked">Not re-checked since it was first recorded; ' +
               'confirm against the official source before relying on it.</p>';
    }
  }

  // ---------------------------------------------------------------------------
  // Events
  // ---------------------------------------------------------------------------

  function bindEvents() {
    searchInput.addEventListener('input', scheduleSearch);

    jurisdictionFilters.addEventListener('click', (e) => {
      const btn = e.target.closest('.filter-btn');
      if (!btn) return;
      setActiveButton(jurisdictionFilters, btn);
      activeFilters.jurisdiction = btn.dataset.filter;
      applyFilters();
    });

    statusFilters.addEventListener('click', (e) => {
      const btn = e.target.closest('.filter-btn');
      if (!btn) return;
      activeFilters.status = btn.dataset.filter;
      syncStatusButtons();
      applyFilters();
    });

    tagFiltersContainer.addEventListener('click', (e) => {
      const btn = e.target.closest('.filter-btn');
      if (!btn) return;
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
    });

    if (inForceToggle) {
      inForceToggle.addEventListener('click', () => {
        activeFilters.inForce = !activeFilters.inForce;
        setPressed(inForceToggle, activeFilters.inForce);
        applyFilters();
      });
    }

    if (sortSelect) {
      sortSelect.addEventListener('change', () => {
        sortKey = Object.prototype.hasOwnProperty.call(SORTS, sortSelect.value) ? sortSelect.value : '';
        // Sorting keeps the open record open.
        applyFilters({ keepHash: true });
      });
    }

    resetFiltersBtn.addEventListener('click', resetFilters);

    // A fragment like #state-001, typed into the address bar, opens that record.
    // Record ids are permanent, so such a link works for as long as the record does.
    window.addEventListener('hashchange', () => openRowFromHash());

    // Back and Forward change the address bar without reloading the page, so
    // read the view back out of it.
    window.addEventListener('popstate', (e) => {
      // Before anything is rebuilt: what had keyboard focus.
      const focusedBefore = document.activeElement;
      // Text still being typed belonged to the view that was just left.
      cancelSearch();
      // Where the address could not be kept in step, only its fragment means
      // anything, and the filters stay as they are.
      if (addressWritable) {
        const before = viewKey();
        activeFilters = Object.assign({}, DEFAULT_FILTERS);
        sortKey = '';
        readUrlState();
        syncControls();
        // Rebuild the table only when the step changes what is listed.
        // Rebuilding destroys the control that has keyboard focus, so a step
        // that only opens or closes a record is carried out in place.
        if (viewKey() !== before) {
          if (!hashId()) expandedRow = null;
          applyFilters({ keepHash: true, leaveUrl: true });
        }
      } else {
        syncControls();
      }
      focusAfterHistoryStep(e.state, syncOpenRecord(), focusedBefore);
    });

    // Links to records are followed here, not by the browser, so that a search
    // still being typed is applied first and the way back is remembered.
    document.addEventListener('click', (e) => {
      const link = e.target.closest('a.record-link');
      if (!link) return;
      // A click that opens a new tab or window is the browser's to handle.
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      followRecordLink(link);
    });
  }

  // Bind row click events (called after render). A keyboard press on the title
  // button fires a click that bubbles up to the row, so this one handler serves both.
  function bindRowEvents() {
    tableBody.querySelectorAll('.data-row').forEach(row => {
      row.addEventListener('click', () => {
        const id = row.dataset.id;
        const wasOpen = expandedRow === id;
        if (!settleSearch()) {
          toggleRowExpansion(row);
          return;
        }
        // A search that was still being typed has just been applied, which
        // rebuilt the table with every record closed. Open the record that was
        // clicked, if the search still lists it.
        const current = findRow(id);
        if (current && !wasOpen) {
          toggleRowExpansion(current);
          current.scrollIntoView({ block: 'nearest' });
        }
      });
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

  function toggleRowExpansion(row) {
    const id = row.dataset.id;

    if (expandedRow === id) {
      setExpanded(id, false);
      expandedRow = null;
      writeUrlState();
      return;
    }

    if (expandedRow) setExpanded(expandedRow, false);
    setExpanded(id, true);
    expandedRow = id;
    writeUrlState();
  }

  function decodeFragment(text) {
    try {
      return decodeURIComponent(text);
    } catch (error) {
      return '';
    }
  }

  // The record id named by the URL fragment, or '' when there is none.
  function hashId() {
    return decodeFragment(window.location.hash.slice(1));
  }

  // Make the open record the one the address names. Returns that record's row,
  // or null when the address names none. Moves neither focus nor the page.
  function syncOpenRecord() {
    const id = hashId();
    if (!id || !allData.some(item => item.id === id)) {
      // No record is named: the fragment is gone, for example after Back, or it
      // names nothing that exists. Close what was open.
      if (expandedRow) {
        setExpanded(expandedRow, false);
        expandedRow = null;
      }
      // A fragment that names no record is dropped, as it is when the page
      // loads, so the address never claims a view the page is not showing.
      if (window.location.hash) writeUrlState();
      return null;
    }

    let row = findRow(id);
    if (!row) {
      // The record exists but the current filters hide it.
      resetFilters();
      row = findRow(id);
    }
    if (!row) return null;

    if (expandedRow !== id) toggleRowExpansion(row);
    return row;
  }

  // Open the record named by the URL fragment, bring it to the middle of the
  // window and put focus on its title. A record that is already open is left
  // where it is unless `always` is set, so handling the same address twice
  // (browsers report some changes through two events) moves nothing.
  function openRowFromHash(options) {
    const alreadyOpen = Boolean(expandedRow) && expandedRow === hashId();
    const row = syncOpenRecord();
    if (!row || (alreadyOpen && !(options && options.always))) return;
    row.scrollIntoView({ block: 'center' });
    const toggle = row.querySelector('.row-toggle');
    if (toggle) toggle.focus({ preventScroll: true });
  }

  // Follow a link to a record: a new step in the browser's history, with the
  // record open. Done here so the address the step is added to is complete.
  function followRecordLink(link) {
    const id = decodeFragment((link.getAttribute('href') || '').slice(1));
    if (!id) return;
    const from = describeLink(link);
    // A search still being typed is part of the view being left. Apply it now,
    // or the step back would return to a view without it. Keep the open record
    // open if the search still lists it: the link may be inside it.
    settleSearch({ keepHash: true });

    if (id === hashId()) {
      // Already the record in the address, so there is no step to add.
      openRowFromHash({ always: true });
      return;
    }

    const fragment = `#${encodeURIComponent(id)}`;
    try {
      // Note on the view being left which link was used, then add the step.
      // Neither call fires an event, so the record is opened directly below.
      window.history.replaceState({ returnTo: from }, '');
      window.history.pushState(null, '', window.location.pathname + window.location.search + fragment);
    } catch (error) {
      // Some contexts (file://, sandboxed frames) refuse this. Setting the
      // fragment still works there, and its hashchange opens the record.
      window.location.hash = fragment;
      return;
    }
    openRowFromHash();
  }

  // Where a record link sits, in words that survive the table being rebuilt:
  // the record whose details hold it, or the overview list it is in, and which
  // of the links there to the same record it is.
  function describeLink(link) {
    const detail = link.closest('.detail-row');
    const list = detail ? null
      : LINK_LISTS.map(id => document.getElementById(id)).find(el => el && el.contains(link));
    const scope = detail || list;
    if (!scope) return null;
    const href = link.getAttribute('href');
    const same = Array.from(scope.querySelectorAll('a.record-link')).filter(a => a.getAttribute('href') === href);
    return { record: detail ? detail.dataset.detailFor : '', list: list ? list.id : '', href, nth: same.indexOf(link) };
  }

  // The link a description points at, if it is on the page and can be seen.
  // The description comes back from the browser's history, so check its shape.
  function findLink(where) {
    if (!where || typeof where !== 'object' || typeof where.href !== 'string' || !Number.isInteger(where.nth)) {
      return null;
    }
    let scope = null;
    if (typeof where.record === 'string' && where.record) {
      scope = findDetail(where.record);
    } else if (LINK_LISTS.includes(where.list)) {
      scope = document.getElementById(where.list);
    }
    if (!scope) return null;
    const same = Array.from(scope.querySelectorAll('a.record-link')).filter(a => a.getAttribute('href') === where.href);
    const link = same[where.nth] || null;
    return link && link.getClientRects().length ? link : null;
  }

  // Put focus on a control, and move the page only if it could not be seen.
  function focusInView(control) {
    control.focus({ preventScroll: true });
    const box = control.getBoundingClientRect();
    if (box.top < 0 || box.bottom > window.innerHeight) control.scrollIntoView({ block: 'center' });
  }

  // Where keyboard focus goes after Back or Forward. A view the reader left by
  // a record link gets focus back on that link, the way closing a dialog
  // returns focus to the button that opened it. Otherwise focus goes to the
  // open record, if there is one. The browser restores the scroll position
  // when the popstate handler returns, so this waits for that and then moves
  // the page only if the control would be out of sight.
  function focusAfterHistoryStep(state, row, focusedBefore) {
    const id = row ? row.dataset.id : null;
    window.setTimeout(() => {
      const openRow = id ? findRow(id) : null;
      const target = findLink(state && state.returnTo) || (openRow && openRow.querySelector('.row-toggle'));
      if (target) {
        focusInView(target);
        return;
      }
      keepFocusInSight(focusedBefore);
      // Browsers restore the scroll position at different moments, sometimes
      // only after this has run, so look again once the page moves.
      const again = () => {
        window.removeEventListener('scroll', again);
        keepFocusInSight(focusedBefore);
      };
      window.addEventListener('scroll', again, { passive: true });
      window.setTimeout(() => window.removeEventListener('scroll', again), 500);
    }, 0);
  }

  // Nothing to return to after Back or Forward. Do not leave focus on a
  // control the restored scroll position has moved out of sight, or let it
  // fall to the page because rebuilding the table removed the control that had
  // it: the next Tab would jump the page away from what the reader is looking
  // at. Blurring is not enough, because browsers start the next Tab from where
  // focus was. A reader whose focus was already on the page is left alone.
  function keepFocusInSight(focusedBefore) {
    const active = document.activeElement;
    const lost = active === document.body && focusedBefore && focusedBefore !== document.body &&
      !focusedBefore.isConnected;
    if (lost || (active && active !== document.body && !isPartlyInView(active))) {
      const visible = firstPlaceInView();
      if (visible) visible.focus({ preventScroll: true });
    }
  }

  function isPartlyInView(element) {
    const box = element.getBoundingClientRect();
    return box.height > 0 && box.bottom > 0 && box.top < window.innerHeight;
  }

  function isWhollyInView(element) {
    const box = element.getBoundingClientRect();
    return box.height > 0 && box.top >= 0 && box.bottom <= window.innerHeight;
  }

  // Somewhere on screen to put focus without surprising the reader: a link,
  // where Space still scrolls and letters do nothing, or else a record's row,
  // a heading, a label or a paragraph, made focusable for this once. Never a
  // button, which Space would press, or the search box, where the next keys
  // would type and filter the table.
  function firstPlaceInView() {
    const link = Array.from(document.querySelectorAll('a[href]')).find(isWhollyInView);
    if (link) return link;
    const place = Array.from(document.querySelectorAll('.data-row, h1, h2, h3, h4, p, li, .filter-label'))
      .find(el => isWhollyInView(el) && !el.closest('a, button, input, select, textarea'));
    if (!place) return null;
    if (!place.hasAttribute('tabindex')) {
      place.setAttribute('tabindex', '-1');
      place.addEventListener('blur', () => place.removeAttribute('tabindex'), { once: true });
    }
    return place;
  }

  // ---------------------------------------------------------------------------
  // Search box
  //
  // The box is applied 300 ms after the last key, so the table is not rebuilt on
  // every keystroke. Anything else that changes or leaves the view in that gap
  // first applies the pending text (settleSearch, applyFilters) or drops it
  // (cancelSearch), so nothing ever works from a half-applied view.
  // ---------------------------------------------------------------------------

  function searchBoxText() {
    return searchInput.value.trim().slice(0, 200);
  }

  function scheduleSearch() {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(applySearchBox, 300);
  }

  function cancelSearch() {
    window.clearTimeout(searchTimer);
    searchTimer = null;
  }

  // Apply the text in the search box. Returns true if that rebuilt the table.
  // Text that is already applied changes nothing, so a late timer can never
  // close the open record for no reason.
  function applySearchBox(options) {
    cancelSearch();
    const text = searchBoxText();
    if (text === activeFilters.search) return false;
    activeFilters.search = text;
    applyFilters(options);
    return true;
  }

  // Apply a search that is still being typed, if there is one. Options are
  // passed on to applyFilters.
  function settleSearch(options) {
    return searchTimer !== null && applySearchBox(options);
  }

  // The visual state and the accessible state of a filter button always change together.
  function setPressed(btn, pressed) {
    btn.classList.toggle('active', pressed);
    btn.setAttribute('aria-pressed', String(pressed));
  }

  function setActiveButton(container, activeBtn) {
    container.querySelectorAll('.filter-btn').forEach(btn => setPressed(btn, btn === activeBtn));
  }

  // ---------------------------------------------------------------------------
  // Filtering and sorting
  // ---------------------------------------------------------------------------

  function matchesFilters(item) {
    if (activeFilters.jurisdiction !== 'all' && item.jurisdiction_type !== activeFilters.jurisdiction) {
      return false;
    }

    if (activeFilters.status !== 'all' &&
        String(item.status || '').toLowerCase() !== activeFilters.status.toLowerCase()) {
      return false;
    }

    if (activeFilters.tag && !(Array.isArray(item.tags) && item.tags.includes(activeFilters.tag))) {
      return false;
    }

    if (activeFilters.inForce && !isInForce(item)) {
      return false;
    }

    if (activeFilters.search) {
      // Keep this list, and its order, in step with searchable_text() in
      // src/query_legislation.py. A query such as "Colorado SB 24-205" spans two
      // fields, so it matches only where they are joined next to each other.
      // tests/test_scripts.py compares the two lists.
      const tags = Array.isArray(item.tags) ? item.tags : [];
      const searchableText = [
        item.title, item.name, item.summary, item.state, item.jurisdiction,
        item.issuing_body, item.bill_number, item.id, item.type, item.verification,
        item.injunction,
        ...(Array.isArray(item.key_provisions) ? item.key_provisions : []),
        ...tags,
        // Also as displayed, so "frontier ai" finds the tag frontier_ai.
        ...tags.concat(item.type || []).map(t => String(t).replace(/_/g, ' ')),
        ...(Array.isArray(item.milestones) ? item.milestones.map(m => m && m.description) : [])
      ].filter(Boolean).join(' ').toLowerCase();

      if (!searchableText.includes(activeFilters.search.toLowerCase())) {
        return false;
      }
    }

    return true;
  }

  function sortRecords(records) {
    const byOrder = (a, b) => a._order - b._order;
    const sorted = records.slice();
    switch (sortKey) {
      case 'jurisdiction':
        return sorted.sort((a, b) =>
          compareStrings(String(getJurisdictionDisplay(a) || '').toLowerCase(), String(getJurisdictionDisplay(b) || '').toLowerCase()) ||
          compareStrings(String(a.title || '').toLowerCase(), String(b.title || '').toLowerCase()) || byOrder(a, b));
      case 'title':
        return sorted.sort((a, b) =>
          compareStrings(String(a.title || '').toLowerCase(), String(b.title || '').toLowerCase()) || byOrder(a, b));
      case 'status': {
        const rank = item => {
          const index = STATUS_ORDER.indexOf(String(item.status || '').toLowerCase());
          return index === -1 ? STATUS_ORDER.length : index;
        };
        return sorted.sort((a, b) => rank(a) - rank(b) || byOrder(a, b));
      }
      case 'effective-asc':
      case 'effective-desc': {
        const direction = sortKey === 'effective-asc' ? 1 : -1;
        // Records without a date go last in either direction.
        return sorted.sort((a, b) => {
          const da = effectiveDateOf(a), db = effectiveDateOf(b);
          if (!da && !db) return byOrder(a, b);
          if (!da) return 1;
          if (!db) return -1;
          return direction * compareStrings(da, db) || byOrder(a, b);
        });
      }
      default:
        return sorted.sort(byOrder);
    }
  }

  // The filters and sort as one value, to tell whether two views list the same records.
  function viewKey() {
    return JSON.stringify([activeFilters.jurisdiction, activeFilters.status, activeFilters.tag,
                           activeFilters.search, activeFilters.inForce, sortKey]);
  }

  // The record whose title button has keyboard focus, or null.
  function focusedRowId() {
    const active = document.activeElement;
    const row = active && active.classList && active.classList.contains('row-toggle')
      ? active.closest('.data-row') : null;
    return row ? row.dataset.id : null;
  }

  // Apply filters and sort, render, and keep the address bar in step.
  // Changing a filter closes the open record unless keepHash is set.
  function applyFilters(options) {
    const keepHash = options && options.keepHash;
    const leaveUrl = options && options.leaveUrl;
    // A search still being typed is part of the view the reader is asking for.
    if (searchTimer !== null) {
      cancelSearch();
      activeFilters.search = searchBoxText();
    }
    if (!keepHash) expandedRow = null;

    filteredData = sortRecords(allData.filter(matchesFilters));
    if (expandedRow && !filteredData.some(item => item.id === expandedRow)) expandedRow = null;

    // Rebuilding the table destroys the button that has focus. Put focus back
    // on the same record's new button, if the record is still listed.
    const focused = focusedRowId();
    renderTable();
    if (expandedRow) setExpanded(expandedRow, true);
    if (focused) {
      const row = findRow(focused);
      const toggle = row && row.querySelector('.row-toggle');
      if (toggle) toggle.focus({ preventScroll: true });
    }
    if (!leaveUrl) writeUrlState();
  }

  function resetFilters() {
    cancelSearch();
    activeFilters = Object.assign({}, DEFAULT_FILTERS);
    syncControls();
    applyFilters();
  }

  // ---------------------------------------------------------------------------
  // Utilities
  // ---------------------------------------------------------------------------

  // Escape text for safe use as HTML content or inside a quoted attribute.
  // (Setting textContent and reading innerHTML escapes < > & but NOT quotes,
  // which is not enough once the value lands inside an attribute.)
  function escapeHtml(value) {
    return String(value === null || value === undefined ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Reduce a value to something safe to use as a CSS class name.
  function cssToken(value) {
    return String(value === null || value === undefined ? '' : value)
      .toLowerCase().replace(/[^a-z0-9_-]/g, '');
  }

  // Only http(s) links are ever rendered as a link target. A "javascript:" URL
  // in a data file would otherwise run when clicked.
  function safeUrl(value) {
    return typeof value === 'string' && /^https?:\/\//i.test(value.trim()) ? value.trim() : '#';
  }

  // A zero-padded calendar date, "2026-09-17".
  function isIsoDate(value) {
    return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value);
  }

  function compareStrings(a, b) {
    return a < b ? -1 : a > b ? 1 : 0;
  }

  function formatTag(tag) {
    return String(tag)
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  }

  // "2026-09-17" -> "September 2026"
  function formatMonth(iso) {
    const parts = String(iso).split('-');
    const month = MONTHS[parseInt(parts[1], 10) - 1];
    return month ? `${month} ${parts[0]}` : iso;
  }

  // "2026-12-02" -> "2 Dec 2026"
  function formatDay(iso) {
    const parts = String(iso).split('-');
    const month = MONTHS_SHORT[parseInt(parts[1], 10) - 1];
    return month ? `${parseInt(parts[2], 10)} ${month} ${parts[0]}` : iso;
  }

  // Whole days from today to a date, counted on the calendar.
  function daysUntil(iso) {
    const [y, m, d] = String(iso).split('-').map(Number);
    const [ty, tm, td] = TODAY.split('-').map(Number);
    return Math.round((Date.UTC(y, m - 1, d) - Date.UTC(ty, tm - 1, td)) / 86400000);
  }

  function countdown(iso) {
    const days = daysUntil(iso);
    if (days === 0) return 'Today';
    if (days === 1) return 'Tomorrow';
    if (days < 60) return `In ${days} days`;
    const months = Math.round(days / 30.44);
    if (months < 24) return `In ${months} months`;
    return `In ${Math.round(days / 365.25)} years`;
  }

  function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  document.addEventListener('DOMContentLoaded', init);
})();
