import { api, checkBackend, isOffline, onOffline, postJson } from "./api.js";
import { startStory } from "./demo.js";
import { renderCards } from "./cards.js";
import { openCheckin } from "./checkin.js";
import { renderDownlink } from "./downlink.js";
import { openProtocol } from "./protocol.js";
import { renderRadiation } from "./radiation.js";
import { startVitals } from "./vitals.js";

const $ = (id) => document.getElementById(id);
let crewList = [], thr, crewId, spaceWeather = null;

const showProtocol = (id, modal = true) => openProtocol({ crewId, protocolId: id, modal, onDownlink: () => $("downlink").scrollIntoView({ behavior: "smooth" }) });

async function refreshAssessment(a) {
  a = a || (await api(`/api/assessment/${crewId}`));
  $("mission-info").textContent = `Mission day ${a.mission_day}`;
  renderCards($("cards"), a, thr, { onProtocol: showProtocol });
  const rad = a.domains.find((d) => d.domain === "radiation");
  const spe = rad.metrics.find((m) => m.metric === "spe_active");
  const alertEl = $("alert");
  if (spe && spe.status === "RED") {
    alertEl.hidden = false;
    alertEl.replaceChildren("SOLAR PARTICLE EVENT: GO TO THE SHIELDED AREA NOW ");
    const b = document.createElement("button"); b.className = "btn"; b.textContent = "Open shelter protocol";
    b.onclick = () => showProtocol("radiation_red"); alertEl.append(b);
  } else alertEl.hidden = true;
}
async function refreshRadiation() { renderRadiation($("radiation"), await api(`/api/radiation/${crewId}`), spaceWeather, { onChange: onRadiationChange, onProtocol: showProtocol }); }
async function refreshDownlink() { renderDownlink($("downlink"), await api("/api/downlink"), crewId, { onSent: refreshDownlink }); }
async function loadSpace(refresh = false) {
  try { spaceWeather = await api(`/api/space-weather${refresh ? "?refresh=true" : ""}`); } catch { spaceWeather = null; }
  await refreshRadiation();
}
async function onRadiationChange({ refreshSpace } = {}) {
  if (refreshSpace) return loadSpace(true);
  await Promise.all([refreshAssessment(), refreshRadiation()]);
}
async function refreshAll() { await Promise.all([refreshAssessment(), refreshRadiation(), refreshDownlink()]); }

async function selectCrew(id) {
  crewId = id;
  await refreshAll();
  startVitals(id, crewList.find((c) => c.id === id));
}

function showOfflineBanner() {
  $("banner").hidden = false;
  $("banner").textContent = "FALLBACK DEMO MODE: backend unreachable. Showing the bundled Mars day-120 scenario (SIMULATED). Actions are simulated in this browser and not saved.";
}

const story = {
  loadScenario: async () => {
    await postJson("/api/scenario/mars_day120", {});
    $("crew-select").value = "c1"; crewId = "c1";
    await refreshAll();
  },
  openProtocol: (id) => showProtocol(id, false),
  closeDialogs: () => document.querySelectorAll("dialog[open]").forEach((d) => d.close()),
  triggerSpe: async () => { await postJson("/api/radiation/spe", { active: true }); await Promise.all([refreshAssessment(), refreshRadiation()]); },
  queueSummary: async () => {
    await postJson("/api/downlink", { crew_id: "c1", domains: ["behavioral", "radiation"], include_metrics: true, include_actions: true,
      note: "Demo: poor sleep 3 nights; sheltered during SPE." });
    await refreshDownlink();
  },
};

async function init() {
  onOffline(showOfflineBanner);
  await checkBackend();
  let mission;
  [crewList, thr, mission] = await Promise.all([api("/api/crew"), api("/api/thresholds"), api("/api/mission")]);
  $("btn-demo").addEventListener("click", () => startStory(story));
  const g = thr.global;
  $("persistence-note").textContent =
    `How flags work: your readings are compared with YOUR OWN 14-day pre-flight baseline. A flag only appears when a reading stays ≥ ${g.z_amber.value} SD worse than your normal for ${g.persistence_days.value} days in a row, so one bad night does not raise a false alarm. Safety limits (e.g. very low SpO2) act immediately.`;
  const sel = $("crew-select");
  crewList.forEach((c) => sel.append(new Option(`${c.name} (${c.role})`, c.id)));
  sel.addEventListener("change", () => selectCrew(sel.value));
  const ps = $("profile-select");
  mission.profiles.forEach((p) => ps.append(new Option(p.label, p.id)));
  ps.value = mission.profile;
  ps.addEventListener("change", async () => { await postJson("/api/mission-profile", { profile: ps.value }); await refreshAll(); });
  $("btn-checkin").addEventListener("click", () => openCheckin({ crewId, onSubmitted: (a) => refreshAssessment(a) }));
  await selectCrew(crewList[0].id);
  loadSpace(); // slow network call: do not block the first paint
}
init();
