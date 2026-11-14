import { api } from "./api.js";
import { renderCards } from "./cards.js";
import { openCheckin } from "./checkin.js";
import { startVitals } from "./vitals.js";

const $ = (id) => document.getElementById(id);
let crewList = [], thr, crewId;

async function refresh(assessment) {
  const a = assessment || (await api(`/api/assessment/${crewId}`));
  $("mission-info").textContent = `Mission day ${a.mission_day} · ${thr.missions[a.mission_profile].label}`;
  renderCards($("cards"), a, thr, { onProtocol: (id) => alert(`Protocol ${id}: coming in the next phase`) });
}

async function selectCrew(id) {
  crewId = id;
  await refresh();
  startVitals(id, crewList.find((c) => c.id === id));
}

async function init() {
  try {
    [crewList, thr] = await Promise.all([api("/api/crew"), api("/api/thresholds")]);
  } catch (e) {
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
  $("btn-checkin").addEventListener("click", () => openCheckin({ crewId, onSubmitted: (a) => refresh(a) }));
  await selectCrew(crewList[0].id);
}
init();
