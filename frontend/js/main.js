import { api, postJson } from "./api.js";
import { renderCards } from "./cards.js";
import { openCheckin } from "./checkin.js";
import { renderDownlink } from "./downlink.js";
import { openProtocol } from "./protocol.js";
import { renderRadiation } from "./radiation.js";
import { startVitals } from "./vitals.js";

const $ = (id) => document.getElementById(id);
let crewList = [], thr, crewId, spaceWeather = null;

const showProtocol = (id) => openProtocol({ crewId, protocolId: id, onDownlink: () => $("downlink").scrollIntoView({ behavior: "smooth" }) });

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

async function init() {
  let mission;
  try { [crewList, thr, mission] = await Promise.all([api("/api/crew"), api("/api/thresholds"), api("/api/mission")]); }
  catch (e) {
    $("banner").hidden = false;
    $("banner").textContent = "Backend unreachable. (Offline fallback demo mode arrives in a later phase.) " + e.message;
    return;
  }
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
