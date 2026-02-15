from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

import requests
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response

from api.shelf import apply_deletions_api, list_items, update_status

app = FastAPI(title="Mediacycler Shelf")


def _rotator_config_path() -> Path:
    configured = os.getenv("ROTATOR_CONFIG_PATH")
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[1] / "mediarotator" / ".rotator_config.json"


def _load_rotator_config() -> dict[str, Any]:
    path = _rotator_config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_rotator_config(config: dict[str, Any]) -> None:
    path = _rotator_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(config, indent=2)}\n", encoding="utf-8")


def _sync_enabled() -> bool:
    config = _load_rotator_config()
    seedbox = config.get("seedbox")
    if isinstance(seedbox, dict) and isinstance(seedbox.get("enabled"), bool):
        return bool(seedbox["enabled"])
    env = os.getenv("SEEDBOX_SYNC_ENABLED")
    if env is not None:
        return env.strip().lower() in {"1", "true", "yes", "on"}
    return True


def _html_template() -> str:
    return """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Shelf Review</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Bebas+Neue&family=Montserrat:wght@500;700;800&family=Source+Serif+4:wght@400;600&display=swap');
    :root {
      --bg: #15110c;
      --ink: #f8f0e2;
      --body-font: "Source Serif 4", "Georgia", serif;
      --title-font: "Bebas Neue", sans-serif;
      --menu-font: "Montserrat", sans-serif;
      --accent: #caa35c;
      --accent-dark: #8a6b2f;
      --muted: #c2b6a3;
      --keep: #5cb85c;
      --delete: #d9534f;
      --defer: #f0ad4e;
      --card: #231b14;
      --border: #3c2f23;
      --marquee: #6b1d1d;
      --bg-top: #140f0b;
      --bg-mid: #1d1711;
      --bg-bottom: #120e0a;
      --header-top: #2a1f18;
      --header-bottom: #1c1510;
      --surface: #1d1510;
      --button-bg: #2b221a;
      --details-bg: #fff8ee;
      --details-ink: #1c130d;
      --footer-bg: #1d1711;
      --button-ink: #f8f0e2;
      --primary-ink: #1b130d;
      --controls-bg: #201810;
      --controls-border: #3c2f23;
      --card-title-ink: #f8f0e2;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: var(--body-font);
      background:
        radial-gradient(circle at top, rgba(255, 228, 196, 0.08), transparent 55%),
        linear-gradient(180deg, var(--bg-top), var(--bg-mid) 45%, var(--bg-bottom));
      color: var(--ink);
    }
    header {
      padding: 18px 32px 24px;
      border-bottom: 1px solid var(--border);
      background: linear-gradient(180deg, var(--header-top), var(--header-bottom));
      box-shadow: inset 0 -1px 0 rgba(255, 255, 255, 0.06);
    }
    header h1 {
      margin: 0;
      font-family: var(--title-font);
      font-size: 2.4rem;
      letter-spacing: 2px;
      color: var(--accent);
      text-transform: uppercase;
    }
    header p {
      margin: 6px 0 0;
      color: var(--muted);
    }
    main {
      padding: 24px 32px 80px;
    }
    .controls {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
      margin-bottom: 18px;
      background: var(--controls-bg);
      border: 1px solid var(--controls-border);
      border-radius: 14px;
      padding: 12px;
    }
    .theme-control {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-weight: 600;
      font-family: var(--menu-font);
      text-transform: uppercase;
      letter-spacing: 0.7px;
    }
    .theme-control select {
      border: 1px solid var(--accent-dark);
      background: var(--button-bg);
      color: var(--ink);
      border-radius: 6px;
      padding: 8px 10px;
      font-weight: 600;
      font-family: var(--menu-font);
    }
    .button {
      border: 1px solid var(--accent-dark);
      background: var(--button-bg);
      padding: 10px 16px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 600;
      color: var(--button-ink);
      font-family: var(--menu-font);
      text-transform: uppercase;
      letter-spacing: 1px;
      transition: transform 120ms ease, filter 120ms ease;
    }
    .button:hover { filter: brightness(1.08); transform: translateY(-1px); }
    .button:active { transform: translateY(0); }
    .button.primary {
      background: var(--accent);
      color: var(--primary-ink);
      border-color: var(--accent);
    }
    .button.sync-on {
      border-color: var(--keep);
      color: #e6ffef;
      box-shadow: inset 0 0 0 1px rgba(92, 184, 92, 0.35);
    }
    .button.sync-off {
      border-color: var(--delete);
      color: #ffe8e8;
      box-shadow: inset 0 0 0 1px rgba(217, 83, 79, 0.35);
    }
    .stats {
      font-weight: 600;
      color: var(--muted);
      font-family: var(--menu-font);
      letter-spacing: 0.5px;
    }
    .marquee {
      display: inline-block;
      padding: 6px 12px;
      border-radius: 6px;
      background: var(--marquee);
      color: #f7e7c6;
      text-transform: uppercase;
      letter-spacing: 1.2px;
      font-weight: 700;
      font-family: var(--menu-font);
      margin-bottom: 8px;
    }
    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 280px;
      gap: 24px;
    }
    .rail {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      height: fit-content;
      box-shadow: 0 8px 20px rgba(0,0,0,0.2);
    }
    .rail h3 {
      font-family: var(--title-font);
      letter-spacing: 1px;
      margin: 0 0 12px;
      color: var(--accent);
      text-transform: uppercase;
    }
    .rail-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .rail-note {
      margin-top: 10px;
      color: var(--muted);
      font-size: 0.88rem;
      line-height: 1.35;
      border-top: 1px dashed var(--border);
      padding-top: 10px;
    }
    .rail-item {
      border-bottom: 1px dashed var(--border);
      padding-bottom: 8px;
    }
    .rail-item:last-child {
      border-bottom: none;
      padding-bottom: 0;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
    }
    .kind-columns {
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .kind-column {
      background: rgba(0, 0, 0, 0.14);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px;
    }
    .kind-column h2 {
      margin-top: 0;
    }
    .section {
      margin: 18px 0 28px;
    }
    .section h2 {
      font-family: var(--title-font);
      font-size: 1.7rem;
      letter-spacing: 1.5px;
      color: var(--accent);
      margin: 0 0 12px;
      text-transform: uppercase;
    }
    .carousel {
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: minmax(220px, 1fr);
      gap: 16px;
      overflow-x: auto;
      padding-bottom: 6px;
    }
    .carousel::-webkit-scrollbar {
      height: 8px;
    }
    .carousel::-webkit-scrollbar-thumb {
      background: var(--border);
      border-radius: 999px;
    }
    .card {
      border: 1px solid var(--border);
      background: var(--card);
      padding: 14px;
      border-radius: 14px;
      box-shadow: 0 8px 20px rgba(0,0,0,0.05);
      display: grid;
      grid-template-columns: 88px 1fr;
      gap: 12px;
      align-items: start;
    }
    .card.selected {
      outline: 2px solid var(--accent);
    }
    .poster {
      width: 88px;
      height: 132px;
      border-radius: 10px;
      background: #2c2219;
      border: 1px solid var(--border);
      object-fit: cover;
    }
    .card h3 {
      margin: 0;
      font-size: 1.05rem;
      color: var(--card-title-ink);
      font-family: var(--menu-font);
    }
    .card-content { display: flex; flex-direction: column; gap: 8px; }
    .meta { color: var(--muted); font-size: 0.9rem; }
    .status { font-weight: 600; }
    .status.keep { color: var(--keep); }
    .status.delete { color: var(--delete); }
    .status.defer { color: var(--defer); }
    .status.undecided { color: var(--muted); }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; }
    .actions button {
      border-radius: 8px;
      padding: 6px 10px;
      font-weight: 700;
      border: 1px solid var(--accent-dark);
      background: var(--button-bg);
      color: var(--button-ink);
      font-family: var(--menu-font);
      text-transform: uppercase;
      letter-spacing: 0.6px;
    }
    .details {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.4);
      display: none;
      align-items: center;
      justify-content: center;
    }
    .details.show { display: flex; }
    .details .panel {
      background: var(--details-bg);
      color: var(--details-ink);
      padding: 20px;
      border-radius: 16px;
      max-width: 520px;
      width: 92%;
      border: 1px solid var(--border);
    }
    .panel h4 { margin: 0 0 12px; }
    .panel pre { white-space: pre-wrap; font-family: inherit; }
    footer {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      background: var(--footer-bg);
      border-top: 1px solid var(--border);
      padding: 12px 24px;
      font-size: 0.9rem;
      color: var(--muted);
      font-family: var(--menu-font);
      letter-spacing: 0.4px;
    }
    body.theme-blockbuster .marquee {
      border: 2px solid #ffd84d;
      box-shadow: 0 0 0 2px #0e2f64, 0 0 16px rgba(255, 221, 85, 0.22);
      color: #fff2b0;
    }
    body.theme-blockbuster .controls {
      border-color: #31578b;
      box-shadow: inset 0 0 0 1px rgba(255, 225, 112, 0.2);
    }
    body.theme-blockbuster .section h2,
    body.theme-blockbuster .rail h3,
    body.theme-blockbuster header h1 {
      font-family: "Archivo Black", sans-serif;
      letter-spacing: 1px;
    }
    @media (max-width: 1000px) {
      .layout {
        grid-template-columns: 1fr;
      }
      .kind-columns {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <header>
    <h1>Shelf Review</h1>
    <div class=\"marquee\">Now Showing</div>
    <p>Curate your rotating library like a classic theater shelf.</p>
  </header>
  <main>
    <div class=\"controls\">
      <button class=\"button\" onclick=\"refresh()\">Rescan</button>
      <button class=\"button primary\" onclick=\"applyDeletions()\">Apply Deletions</button>
      <button class=\"button\" id=\"sync-toggle\" onclick=\"toggleSync()\">Sync: checking...</button>
      <label class=\"theme-control\" for=\"theme-select\">
        Theme
        <select id=\"theme-select\" onchange=\"onThemeChange(this.value)\">
          <option value=\"blockbuster\">Blockbuster</option>
          <option value=\"movie-theater\">Movie Theater</option>
          <option value=\"neon-drive-in\">Neon Drive-In</option>
        </select>
      </label>
      <div class=\"stats\" id=\"stats\"></div>
    </div>
    <div class=\"layout\">
      <div>
        <section class=\"section\">
          <h2>Latest Completed Downloads</h2>
          <div class=\"carousel\" id=\"featured\"></div>
        </section>
        <section class=\"section kind-columns\">
          <div class=\"kind-column\">
            <h2>Movies</h2>
            <div id=\"movies-grid\"></div>
          </div>
          <div class=\"kind-column\">
            <h2>TV</h2>
            <div id=\"tv-grid\"></div>
          </div>
        </section>
      </div>
      <aside class=\"rail\">
        <h3>Coming Attractions</h3>
        <div class=\"rail-list\" id=\"coming\"></div>
        <div class=\"rail-note\" id=\"coming-note\"></div>
      </aside>
    </div>
  </main>
  <div class=\"details\" id=\"details\" onclick=\"closeDetails()\">
    <div class=\"panel\" onclick=\"event.stopPropagation()\">
      <h4 id=\"details-title\"></h4>
      <pre id=\"details-body\"></pre>
      <button class=\"button\" onclick=\"closeDetails()\">Close</button>
    </div>
  </div>
  <footer id=\"footer\">Ready.</footer>
  <script>
    let items = [];
    let featured = [];
    let coming = [];
    let comingNote = '';
    let selected = null;
    let syncEnabled = true;
    const themeMeta = {
      blockbuster: {
        marquee: 'Be Kind. Rewind.',
        subtitle: 'Please enjoy our timeless and robust business model.'
      },
      'movie-theater': {
        marquee: 'Now Showing',
        subtitle: 'Wow, this is just like the movie theatre!'
      },
      'neon-drive-in': {
        marquee: 'Tonight at Sunset',
        subtitle: 'And this one is like a retro guy!`'
      }
    };
    const themes = {
      'movie-theater': {
        '--bg': '#15110c',
        '--ink': '#f8f0e2',
        '--body-font': '"Source Serif 4", "Georgia", serif',
        '--title-font': '"Bebas Neue", sans-serif',
        '--menu-font': '"Montserrat", sans-serif',
        '--accent': '#caa35c',
        '--accent-dark': '#8a6b2f',
        '--muted': '#c2b6a3',
        '--keep': '#5cb85c',
        '--delete': '#d9534f',
        '--defer': '#f0ad4e',
        '--card': '#231b14',
        '--border': '#3c2f23',
        '--marquee': '#6b1d1d',
        '--bg-top': '#140f0b',
        '--bg-mid': '#1d1711',
        '--bg-bottom': '#120e0a',
        '--header-top': '#2a1f18',
        '--header-bottom': '#1c1510',
        '--surface': '#1d1510',
        '--button-bg': '#2b221a',
        '--details-bg': '#fff8ee',
        '--details-ink': '#1c130d',
        '--footer-bg': '#1d1711',
        '--button-ink': '#f8f0e2',
        '--primary-ink': '#1b130d',
        '--controls-bg': '#201810',
        '--controls-border': '#3c2f23',
        '--card-title-ink': '#f8f0e2'
      },
      blockbuster: {
        '--bg': '#081730',
        '--ink': '#f0f5ff',
        '--body-font': '"Montserrat", sans-serif',
        '--title-font': '"Archivo Black", sans-serif',
        '--menu-font': '"Montserrat", sans-serif',
        '--accent': '#ffdc42',
        '--accent-dark': '#f0c11b',
        '--muted': '#9fc0e4',
        '--keep': '#54d17e',
        '--delete': '#ff6b63',
        '--defer': '#ffb14a',
        '--card': '#113a72',
        '--border': '#31578b',
        '--marquee': '#11407a',
        '--bg-top': '#071120',
        '--bg-mid': '#0e2a54',
        '--bg-bottom': '#050d1a',
        '--header-top': '#16447f',
        '--header-bottom': '#0f2e59',
        '--surface': '#0f2f5f',
        '--button-bg': '#11407a',
        '--details-bg': '#eef4ff',
        '--details-ink': '#0a1c36',
        '--footer-bg': '#0b1e39',
        '--button-ink': '#fff2a8',
        '--primary-ink': '#122243',
        '--controls-bg': '#0f2f5f',
        '--controls-border': '#31578b',
        '--card-title-ink': '#fff2a8'
      },
      'neon-drive-in': {
        '--bg': '#130924',
        '--ink': '#ffeef8',
        '--body-font': '"Montserrat", sans-serif',
        '--title-font': '"Bebas Neue", sans-serif',
        '--menu-font': '"Montserrat", sans-serif',
        '--accent': '#ff5fb5',
        '--accent-dark': '#bd2f7d',
        '--muted': '#cfb3d5',
        '--keep': '#5ce28f',
        '--delete': '#ff6f8a',
        '--defer': '#ffd36a',
        '--card': '#23103a',
        '--border': '#4d2a68',
        '--marquee': '#6a1f82',
        '--bg-top': '#120821',
        '--bg-mid': '#200f35',
        '--bg-bottom': '#0d0618',
        '--header-top': '#3f1a58',
        '--header-bottom': '#26113a',
        '--surface': '#1b0d2e',
        '--button-bg': '#3e1f5a',
        '--details-bg': '#fff0ff',
        '--details-ink': '#250f35',
        '--footer-bg': '#241137',
        '--button-ink': '#ffeef8',
        '--primary-ink': '#2a143c',
        '--controls-bg': '#1b0d2e',
        '--controls-border': '#4d2a68',
        '--card-title-ink': '#ffd8f1'
      }
    };

    function applyTheme(themeName) {
      const resolvedTheme = themes[themeName] ? themeName : 'blockbuster';
      const theme = themes[resolvedTheme];
      Object.entries(theme).forEach(([key, value]) => {
        document.documentElement.style.setProperty(key, value);
      });
      document.body.className = `theme-${resolvedTheme}`;
      const select = document.getElementById('theme-select');
      if (select && select.value !== resolvedTheme) select.value = resolvedTheme;
      const meta = themeMeta[resolvedTheme];
      if (meta) {
        const marquee = document.querySelector('.marquee');
        const subtitle = document.querySelector('header p');
        if (marquee) marquee.textContent = meta.marquee;
        if (subtitle) subtitle.textContent = meta.subtitle;
      }
      localStorage.setItem('shelf-theme', resolvedTheme);
    }

    function onThemeChange(themeName) {
      applyTheme(themeName);
      footer(`Theme set to ${themeName.replaceAll('-', ' ')}.`);
    }

    function updateSyncButton() {
      const button = document.getElementById('sync-toggle');
      if (!button) return;
      button.classList.remove('sync-on', 'sync-off');
      if (syncEnabled) {
        button.classList.add('sync-on');
        button.textContent = 'Sync: ON';
      } else {
        button.classList.add('sync-off');
        button.textContent = 'Sync: OFF';
      }
    }

    async function loadSyncState() {
      try {
        const res = await fetch('/api/sync/state');
        const data = await res.json();
        syncEnabled = !!data.enabled;
      } catch (_err) {
        syncEnabled = true;
      }
      updateSyncButton();
    }

    async function toggleSync() {
      const next = !syncEnabled;
      const res = await fetch('/api/sync/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: next })
      });
      const data = await res.json();
      syncEnabled = !!data.enabled;
      updateSyncButton();
      footer(`Seedbox sync ${syncEnabled ? 'enabled' : 'disabled'}.`);
    }

    function formatSize(bytes) {
      const units = ['B','KB','MB','GB','TB'];
      let value = bytes;
      let idx = 0;
      while (value >= 1024 && idx < units.length - 1) {
        value /= 1024; idx++;
      }
      return `${value.toFixed(1)} ${units[idx]}`;
    }

    function formatDate(tsSeconds) {
      if (!tsSeconds) return 'Unknown date';
      return new Date(tsSeconds * 1000).toISOString().slice(0, 10);
    }

    function groupByGenre(items) {
      const groups = {};
      const order = [];
      items.forEach(item => {
        const genre = (item.genres && item.genres.length > 0) ? item.genres[0] : 'Uncategorized';
        if (!groups[genre]) {
          groups[genre] = [];
          order.push(genre);
        }
        groups[genre].push(item);
      });
      return order.map((genre) => ({ genre, items: groups[genre] }));
    }

    function buildCard(item) {
      const card = document.createElement('div');
      card.className = 'card';
      card.tabIndex = 0;
      card.dataset.id = item.item_id;
      card.onclick = () => { selected = item; highlight(card); };
      card.ondblclick = () => showDetails(item);

      const poster = document.createElement('img');
      poster.className = 'poster';
      poster.alt = `${item.title} poster`;
      poster.referrerPolicy = 'no-referrer';
      if (item.poster_url) {
        poster.src = item.poster_url;
      }

      const content = document.createElement('div');
      content.className = 'card-content';

      const title = document.createElement('h3');
      title.textContent = item.title;
      const meta = document.createElement('div');
      meta.className = 'meta';
      const completedDate = formatDate(item.download_completed_at || item.last_modified);
      meta.textContent = `${item.kind.toUpperCase()} • ${formatSize(item.size_bytes)} • ${completedDate}`;
      const status = document.createElement('div');
      status.className = `status ${item.status}`;
      status.textContent = item.status.toUpperCase();

      const actions = document.createElement('div');
      actions.className = 'actions';
      actions.innerHTML = `
        <button onclick=\"setStatus('${item.item_id}','keep')\">Keep</button>
        <button onclick=\"setStatus('${item.item_id}','delete')\">Delete</button>
        <button onclick=\"setStatus('${item.item_id}','defer')\">Defer</button>
        <button onclick=\"showDetailsById('${item.item_id}')\">Details</button>
      `;

      content.appendChild(title);
      content.appendChild(meta);
      content.appendChild(status);
      content.appendChild(actions);

      card.appendChild(poster);
      card.appendChild(content);
      return card;
    }

    function renderKindColumn(containerId, kindItems) {
      const container = document.getElementById(containerId);
      container.innerHTML = '';
      const grouped = groupByGenre(kindItems);
      grouped.forEach(({ genre, items: groupedItems }) => {
        const section = document.createElement('section');
        section.className = 'section';
        const header = document.createElement('h2');
        header.textContent = genre;
        const gridInner = document.createElement('div');
        gridInner.className = 'grid';
        section.appendChild(header);
        section.appendChild(gridInner);
        groupedItems.forEach(item => gridInner.appendChild(buildCard(item)));
        container.appendChild(section);
      });
    }

    function render() {
      let total = 0;
      items.forEach(item => {
        total += item.size_bytes || 0;
      });

      renderFeatured();
      renderComing();

      const movies = items.filter(item => item.kind === 'movie');
      const tv = items.filter(item => item.kind === 'tv');
      renderKindColumn('movies-grid', movies);
      renderKindColumn('tv-grid', tv);
      document.getElementById('stats').textContent = `${items.length} items, ${formatSize(total)}`;
    }

    function highlight(card) {
      document.querySelectorAll('.card').forEach(el => el.classList.remove('selected'));
      if (card) card.classList.add('selected');
    }

    async function refresh() {
      const res = await fetch('/api/shelf/items');
      const data = await res.json();
      items = data.items || [];
      featured = data.featured || [];
      coming = data.coming_attractions || [];
      comingNote = data.coming_attractions_note || '';
      render();
      footer('Rescanned shelf.');
    }

    function renderFeatured() {
      const carousel = document.getElementById('featured');
      if (!carousel) return;
      carousel.innerHTML = '';
      if (!featured.length) {
        const empty = document.createElement('div');
        empty.className = 'meta';
        empty.textContent = 'No featured picks yet.';
        carousel.appendChild(empty);
        return;
      }
      featured.forEach(item => {
        const card = document.createElement('div');
        card.className = 'card';
        const poster = document.createElement('img');
        poster.className = 'poster';
        poster.alt = `${item.title} poster`;
        poster.referrerPolicy = 'no-referrer';
        if (item.poster_url) poster.src = item.poster_url;
        const content = document.createElement('div');
        content.className = 'card-content';
        const title = document.createElement('h3');
        title.textContent = item.title;
        const meta = document.createElement('div');
        meta.className = 'meta';
        const date = item.completed_at ? ` • ${formatDate(item.completed_at)}` : '';
        meta.textContent = `${(item.kind || 'item').toUpperCase()}${date}`;
        content.appendChild(title);
        content.appendChild(meta);
        card.appendChild(poster);
        card.appendChild(content);
        carousel.appendChild(card);
      });
    }

    function renderComing() {
      const list = document.getElementById('coming');
      const noteEl = document.getElementById('coming-note');
      if (!list) return;
      list.innerHTML = '';
      if (noteEl) noteEl.textContent = '';
      if (!coming.length) {
        const empty = document.createElement('div');
        empty.className = 'meta';
        empty.textContent = 'No items in queue.';
        list.appendChild(empty);
        if (noteEl && comingNote) noteEl.textContent = comingNote;
        return;
      }
      coming.forEach(item => {
        const row = document.createElement('div');
        row.className = 'rail-item';
        const title = document.createElement('div');
        title.textContent = item.title;
        const meta = document.createElement('div');
        meta.className = 'meta';
        const state = item.state ? item.state.toUpperCase() : 'PENDING';
        meta.textContent = `${item.kind ? item.kind.toUpperCase() : ''} • ${state}`;
        row.appendChild(title);
        row.appendChild(meta);
        list.appendChild(row);
      });
      if (noteEl && comingNote) noteEl.textContent = comingNote;
    }

    async function setStatus(itemId, status) {
      await fetch(`/api/shelf/items/${itemId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      });
      const item = items.find(i => i.item_id === itemId);
      if (item) item.status = status;
      render();
      footer(`Marked ${status}.`);
    }

    async function applyDeletions() {
      const res = await fetch('/api/shelf/apply', { method: 'POST' });
      const data = await res.json();
      footer(`Deleted ${data.deleted} item(s).`);
      refresh();
    }

    function showDetails(item) {
      document.getElementById('details-title').textContent = item.title;
      document.getElementById('details-body').textContent =
        `Kind: ${item.kind}\nSize: ${formatSize(item.size_bytes)}\nDownload Completed: ${item.download_completed_at ? new Date(item.download_completed_at * 1000).toISOString() : 'Unknown'}\nLast Modified: ${new Date(item.last_modified * 1000).toISOString()}\nStatus: ${item.status}\nPath: ${item.path}`;
      document.getElementById('details').classList.add('show');
    }

    function showDetailsById(itemId) {
      const item = items.find(i => i.item_id === itemId);
      if (item) showDetails(item);
    }

    function closeDetails() {
      document.getElementById('details').classList.remove('show');
    }

    function footer(message) {
      document.getElementById('footer').textContent = message;
    }

    const savedTheme = localStorage.getItem('shelf-theme') || 'blockbuster';
    applyTheme(savedTheme);
    loadSyncState();
    refresh();
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
@app.get("/shelf", response_class=HTMLResponse)
def shelf_page() -> HTMLResponse:
    return HTMLResponse(_html_template())


@app.get("/shelf/review", response_class=HTMLResponse)
def shelf_review() -> HTMLResponse:
    return HTMLResponse(_html_template())


@app.get("/shelf/apply", response_class=HTMLResponse)
def shelf_apply() -> HTMLResponse:
    return HTMLResponse(_html_template())


@app.get("/api/shelf/items")
def api_list_items() -> JSONResponse:
    return JSONResponse(list_items())


@app.get("/api/sync/state")
def api_sync_state() -> JSONResponse:
    return JSONResponse({"enabled": _sync_enabled()})


@app.post("/api/sync/toggle")
def api_sync_toggle(payload: dict[str, Any] = Body(default={})) -> JSONResponse:
    requested = payload.get("enabled")
    current = _sync_enabled()
    enabled = (not current) if requested is None else bool(requested)

    config = _load_rotator_config()
    seedbox = config.get("seedbox")
    if not isinstance(seedbox, dict):
        seedbox = {}
    seedbox["enabled"] = enabled
    config["seedbox"] = seedbox
    _save_rotator_config(config)
    return JSONResponse({"enabled": enabled})


@app.get("/api/poster")
def api_poster(url: str) -> Response:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Invalid poster URL")
    try:
        result = requests.get(url, timeout=12)
        result.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502, detail=f"Poster fetch failed: {exc}"
        ) from exc

    content_type = result.headers.get("content-type", "image/jpeg")
    return Response(content=result.content, media_type=content_type)


@app.patch("/api/shelf/items/{item_id}")
def api_update_status(
    item_id: str, payload: dict[str, Any] = Body(...)
) -> JSONResponse:
    status = payload.get("status")
    if status not in {"undecided", "keep", "delete", "defer", "deleted"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    return JSONResponse(update_status(item_id, status))


@app.post("/api/shelf/apply")
def api_apply(dry_run: bool = False) -> JSONResponse:
    return JSONResponse(apply_deletions_api(dry_run=dry_run))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8099)
