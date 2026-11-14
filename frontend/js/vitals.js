import { checkBackend, isOffline } from "./api.js";
import { h, badge } from "./dom.js";

const NAMES = { resting_hr: ["Heart rate", "bpm"], hrv_rmssd: ["HRV (RMSSD)", "ms"], systolic_bp: ["Systolic BP", "mmHg"], spo2: ["SpO2", "%"] };
let source, chart, offlineTimer;

export function startVitals(crewId, crew) {
  stopVitals();
  const tiles = document.getElementById("vital-tiles");
  const base = Object.fromEntries((crew.baselines || []).map((b) => [b.metric, b]));
  const els = {};
  tiles.replaceChildren(...Object.entries(NAMES).map(([k, [label, unit]]) => {
    const val = h("div", { class: "val" }, "–");
    els[k] = val;
    const b = base[k];
    return h("div", { class: "tile" }, h("div", { class: "lbl" }, `${label} (${unit})`), val,
      h("div", { class: "base" }, b ? `baseline ${b.mean} ± ${b.sd}` : ""), badge("MEASURED"));
  }));
  const ctx = document.getElementById("vitals-chart");
  if (window.Chart) {
    chart = new Chart(ctx, { type: "line",
      data: { labels: [], datasets: [{ label: "Heart rate (bpm)", data: [], borderColor: "#5ab0ff", tension: 0.3, pointRadius: 0 }] },
      options: { animation: false, responsive: true, maintainAspectRatio: false,
        scales: { x: { display: false }, y: { ticks: { color: "#9bacc7" }, grid: { color: "#2a3a56" } } },
        plugins: { legend: { labels: { color: "#e9eff9" } } } } });
  }
  const onData = (d) => {
    for (const k of Object.keys(NAMES)) if (els[k] && d[k] != null) els[k].textContent = d[k];
    if (chart) {
      const ds = chart.data.datasets[0];
      chart.data.labels.push(d.n); ds.data.push(d.resting_hr);
      if (ds.data.length > 60) { chart.data.labels.shift(); ds.data.shift(); }
      chart.update();
    }
  };
  if (isOffline()) return simulateOffline(base, onData);
  source = new EventSource(`/api/vitals/stream/${crewId}`);
  source.onmessage = (e) => onData(JSON.parse(e.data));
  source.onerror = async () => { if (!isOffline()) await checkBackend(); if (isOffline()) { source.close(); simulateOffline(base, onData); } };
}

// Offline: same idea as the backend simulator, values around the crew member's own baseline.
function simulateOffline(base, onData) {
  clearInterval(offlineTimer);
  const gauss = () => Math.sqrt(-2 * Math.log(1 - Math.random())) * Math.cos(2 * Math.PI * Math.random());
  let n = 0;
  offlineTimer = setInterval(() => {
    const d = { n: n++, simulated: true };
    for (const k of Object.keys(NAMES)) if (base[k]) d[k] = Math.round((base[k].mean + gauss() * base[k].sd * 0.6) * 10) / 10;
    if (d.spo2 > 100) d.spo2 = 100;
    onData(d);
  }, 1000);
}
export function stopVitals() { source?.close(); clearInterval(offlineTimer); chart?.destroy(); chart = null; }
