import { getCurrentWindow } from '@tauri-apps/api/window';
import './styles.css';

const API_URL = 'http://127.0.0.1:8000/api/time';
const app = document.querySelector('#app');

app.innerHTML = `
  <section class="widget-shell">
    <header class="widget-header" data-tauri-drag-region>
      <div class="brand"><span class="signal"></span><span>ISS SCALE</span></div>
      <div class="header-actions">
        <span id="status" class="status">CONNECTING</span>
        <button id="close" class="close" aria-label="Close widget">×</button>
      </div>
    </header>
    <div class="hero">
      <span class="eyebrow">INTERPLANETARY STARDATE SYNCROMETER</span>
      <strong id="iss">ISS --.-- --:--:--.---</strong>
      <span id="ns" class="raw">-- ns since 2000 epoch</span>
    </div>
    <div class="time-grid">
      <div><small>EPOCH</small><span id="epoch">--</span></div>
      <div><small>STANDARD</small><span id="standard">--</span></div>
      <div><small>JULIAN</small><span id="julian">--</span></div>
    </div>
    <footer><span id="frame">SOLAR-SYSTEM BARYCENTRIC</span><span id="hash">ANCHOR --</span></footer>
  </section>
`;

const $ = (id) => document.querySelector(`#${id}`);

function setStatus(online) {
  $('status').textContent = online ? 'LIVE' : 'OFFLINE';
  $('status').classList.toggle('offline', !online);
}

function render(data) {
  $('iss').textContent = data.human_iss_precise || data.iss || 'ISS unavailable';
  $('ns').textContent = `${Number(data.iss_time_ns).toLocaleString()} ns since epoch`;
  $('epoch').textContent = Number(data.epoch).toLocaleString();
  $('standard').textContent = data.standard || '--';
  $('julian').textContent = data.julian || '--';
  $('frame').textContent = (data.reference_frame || 'solar-system-barycentric').toUpperCase();
  $('hash').textContent = `ANCHOR ${(data.anchor_hash || '').slice(0, 10) || '--'}`;
  setStatus(true);
}

async function refresh() {
  try {
    const response = await fetch(`${API_URL}?t=${Date.now()}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    render(await response.json());
  } catch {
    setStatus(false);
    $('ns').textContent = 'Start the ISS service on port 8000';
  }
}

$('close').addEventListener('click', () => getCurrentWindow().close());
refresh();
setInterval(refresh, 250);
