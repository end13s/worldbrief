const DOMAIN_COLORS = {
  politics: '#c084fc',
  tech:     '#60a5fa',
  science:  '#34d399',
  economy:  '#fbbf24',
  crime:    '#f87171',
  history:  '#d4b896',
  other:    '#9ca3af',
};

let allArticles = [];
let map, timelineVis, markersLayer;

// ── Bootstrap ────────────────────────────────────────────────────────────────

async function init() {
  await loadSources();
  await loadArticles();
  initMap();
  initTimeline();
  renderArticles(allArticles);
  updateStats();
}

// ── Data ─────────────────────────────────────────────────────────────────────

async function loadSources() {
  const res = await fetch('/sources');
  const sources = await res.json();
  const sel = document.getElementById('filter-source');
  sel.innerHTML = '<option value="">All sources</option>' +
    sources.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
}

async function loadArticles() {
  const res = await fetch('/articles?limit=500');
  allArticles = await res.json();
}

// ── Map ───────────────────────────────────────────────────────────────────────

function initMap() {
  map = L.map('map', {
    zoomControl: true,
    worldCopyJump: false,
    maxBounds: [[-90, -180], [90, 180]],
    maxBoundsViscosity: 1.0,
  }).setView([20, 10], 2);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '© OpenStreetMap © CARTO',
    maxZoom: 18,
    noWrap: true,
  }).addTo(map);

  markersLayer = L.layerGroup().addTo(map);
}

function renderMapMarkers(articles) {
  markersLayer.clearLayers();
  articles
    .filter(a => a.lat && a.lng && !(a.lat === 0 && a.lng === 0))
    .forEach(a => {
      const color = DOMAIN_COLORS[a.domain] || DOMAIN_COLORS.other;
      const marker = L.circleMarker([a.lat, a.lng], {
        radius: 5 + (a.importance_score || 0.5) * 5,
        fillColor: color,
        color: color,
        weight: 1,
        opacity: 0.9,
        fillOpacity: 0.7,
      });
      marker.on('click', () => openModal(a));
      marker.bindTooltip(a.title, { direction: 'top', opacity: 0.9 });
      markersLayer.addLayer(marker);
    });
}

// ── Timeline ──────────────────────────────────────────────────────────────────

function initTimeline() {
  const container = document.getElementById('timeline');
  const dataset = new vis.DataSet([]);
  timelineVis = new vis.Timeline(container, dataset, {
    height: '120px',
    zoomable: true,
    moveable: true,
    stack: false,
    showMajorLabels: true,
    showMinorLabels: true,
    orientation: 'top',
  });

  timelineVis.on('select', ({ items }) => {
    if (items.length) {
      const article = allArticles.find(a => a.id === items[0]);
      if (article) openModal(article);
    }
  });
}

function renderTimeline(articles) {
  const items = articles
    .filter(a => a.published_at)
    .map(a => ({
      id: a.id,
      content: '',
      start: new Date(a.published_at),
      title: a.title,
      style: `background-color: ${DOMAIN_COLORS[a.domain] || DOMAIN_COLORS.other}; border-color: transparent; border-radius: 3px;`,
    }));

  timelineVis.setItems(new vis.DataSet(items));
  if (items.length) timelineVis.fit();
}

// ── Articles list ─────────────────────────────────────────────────────────────

function renderArticles(articles) {
  const list = document.getElementById('articles-list');
  if (!articles.length) {
    list.innerHTML = '<p style="color:#666;padding:2rem">No articles found.</p>';
    return;
  }

  list.innerHTML = articles.map(a => `
    <div class="article-card ${a.importance_score >= 0.8 ? 'important' : ''}" data-id="${a.id}">
      <div class="card-header">
        <span class="domain-badge domain-${a.domain || 'other'}">${a.domain || 'other'}</span>
        <span class="score">${a.importance_score ? (a.importance_score * 10).toFixed(1) + '/10' : ''}</span>
      </div>
      <h3>${a.title || 'No title'}</h3>
      <div class="card-meta">${a.location ? '📍 ' + a.location + ' · ' : ''}${formatDate(a.published_at)}</div>
    </div>
  `).join('');

  list.querySelectorAll('.article-card').forEach(card => {
    card.addEventListener('click', () => {
      const article = allArticles.find(a => a.id === +card.dataset.id);
      if (article) openModal(article);
    });
  });

  renderMapMarkers(articles);
  renderTimeline(articles);
}

// ── Modal ─────────────────────────────────────────────────────────────────────

function openModal(article) {
  document.getElementById('modal-domain-badge').textContent = article.domain || 'other';
  document.getElementById('modal-domain-badge').className = `domain-badge domain-${article.domain || 'other'}`;
  document.getElementById('modal-title').textContent = article.title || '';
  document.getElementById('modal-meta').textContent =
    [article.location, formatDate(article.published_at)].filter(Boolean).join(' · ');

  const raw = article.summary || '';
  const tmp = document.createElement('div');
  tmp.innerHTML = raw;
  document.getElementById('modal-summary').textContent = tmp.textContent || '';

  document.getElementById('modal-link').href = article.url;
  document.getElementById('modal-mark').dataset.id = article.id;

  document.getElementById('modal').classList.remove('hidden');
  document.getElementById('modal-overlay').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('modal').classList.add('hidden');
  document.getElementById('modal-overlay').classList.add('hidden');
}

document.getElementById('modal-close').addEventListener('click', closeModal);
document.getElementById('modal-overlay').addEventListener('click', closeModal);

document.getElementById('modal-mark').addEventListener('click', async (e) => {
  const id = e.target.dataset.id;
  await fetch(`/articles/${id}/mark-important`, { method: 'POST' });
  e.target.textContent = '★ Marked!';
  e.target.disabled = true;
});

// ── Filters ───────────────────────────────────────────────────────────────────

function getFiltered() {
  const domain   = document.getElementById('filter-domain').value;
  const sourceId = document.getElementById('filter-source').value;
  const time     = document.getElementById('filter-time').value;
  const search   = document.getElementById('search').value.toLowerCase();

  const now = new Date();
  const cutoffs = {
    day:   new Date(now - 86400000),
    week:  new Date(now - 7 * 86400000),
    month: new Date(now - 30 * 86400000),
    all:   null,
  };
  const cutoff = cutoffs[time];

  return allArticles.filter(a => {
    if (domain && a.domain !== domain) return false;
    if (sourceId && a.source_id !== +sourceId) return false;
    if (cutoff && a.published_at && new Date(a.published_at) < cutoff) return false;
    if (search && !a.title?.toLowerCase().includes(search) && !a.summary?.toLowerCase().includes(search)) return false;
    return true;
  });
}

['filter-domain', 'filter-source', 'filter-time'].forEach(id => {
  document.getElementById(id).addEventListener('change', () => {
    renderArticles(getFiltered());
    updateStats();
  });
});

document.getElementById('search').addEventListener('input', () => {
  renderArticles(getFiltered());
  updateStats();
});

// ── Stats ─────────────────────────────────────────────────────────────────────

function updateStats() {
  const filtered = getFiltered();
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayCount = filtered.filter(a => a.published_at && new Date(a.published_at) >= today).length;

  document.getElementById('stat-total').textContent = `${filtered.length} articles`;
  document.getElementById('stat-today').textContent = `${todayCount} today`;
}

// ── Utils ─────────────────────────────────────────────────────────────────────

function formatDate(str) {
  if (!str) return '';
  return new Date(str).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

init();
