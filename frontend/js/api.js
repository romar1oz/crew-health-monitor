// Fetch wrapper with FALLBACK DEMO MODE.
// If the backend is unreachable, every call is answered from bundled JSON in /demo-data
// (the Mars day-120 scenario), and actions are simulated in memory, so the demo never breaks.
class HttpError extends Error { constructor(path, status) { super(`${path}: HTTP ${status}`); this.status = status; } }

let offline = false;
const listeners = [];
export const isOffline = () => offline;
export const onOffline = (fn) => listeners.push(fn);
function goOffline(reason) {
  if (offline) return;
  offline = true;
  console.warn("CrewCheck: switching to FALLBACK DEMO MODE:", reason);
  listeners.forEach((fn) => fn(reason));
}

export async function checkBackend() {
  try {
    const r = await fetch("/api/health", { cache: "no-store" });
    const j = r.ok ? await r.json() : null;
    if (!j || j.status !== "ok") goOffline("health check failed");
  } catch (e) { goOffline(e.message); }
  return !offline;
}

export async function api(path, options = {}) {
  if (!offline) {
    let res;
    try { res = await fetch(path, options); }
    catch (e) { goOffline(e.message); return fallback(path, options); }
    if (res.status >= 500) { goOffline(`HTTP ${res.status}`); return fallback(path, options); }
    if (!res.ok) throw new HttpError(path, res.status);
    return res.json();
  }
  return fallback(path, options);
}
export const postJson = (path, body) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

// ---------------- offline simulation ----------------
const cache = {};
const file = async (name) => (cache[name] ??= await (await fetch(`demo-data/${name}.json`)).json());
const sim = { spe: false, queue: [], nextId: 1, actions: [] };

async function buildSummary(body) {
  const a = await file(sim.spe ? "assessment_spe" : "assessment");
  const crew = (await file("crew")).find((c) => c.id === body.crew_id) || { name: body.crew_id };
  const s = { crew_id: body.crew_id, crew_name: crew.name, mission_day: a.mission_day, mission_profile: a.mission_profile,
    simulated_data: true, domains: a.domains.filter((d) => (body.domains || []).includes(d.domain)).map((d) => ({
      domain: d.domain, title: d.title, status: d.status,
      ...(body.include_metrics ? { details: d.triggers.map((t) => ({ label: t.label, value: t.value, unit: t.unit, provenance: t.provenance, reason: t.reason })) } : {}) })) };
  if (body.include_actions) s.actions_completed = sim.actions;
  if (body.note?.trim()) s.crew_note = body.note.trim();
  return s;
}
function queueView(base) {
  const now = Date.now();
  return { ...base, items: sim.queue.slice().reverse().map((it) => {
    const left = Math.max(0, (new Date(it.deliver_at) - now) / 1000);
    return { ...it, seconds_remaining: left, status: left > 0 ? "queued" : "delivered" };
  }) };
}

async function fallback(path, { method = "GET", body } = {}) {
  const b = body ? JSON.parse(body) : {};
  const p = path.split("?")[0];
  let m;
  if (method === "GET") {
    if (p === "/api/health") return { status: "offline-demo" };
    if (p === "/api/crew") return file("crew");
    if (p === "/api/thresholds") return file("thresholds");
    if (p === "/api/mission") return file("mission");
    if (p === "/api/symptoms") return file("symptoms");
    if (p === "/api/space-weather") return file("space_weather");
    if (p.startsWith("/api/assessment/")) return file(sim.spe ? "assessment_spe" : "assessment");
    if (p.startsWith("/api/radiation/")) return file(sim.spe ? "radiation_spe" : "radiation");
    if ((m = p.match(/^\/api\/protocols\/([a-z_]+)$/))) return file(`protocols/${m[1]}`);
    if (p.startsWith("/api/actions/")) return sim.actions;
    if (p === "/api/downlink") return queueView(await file("downlink"));
  }
  if (method === "POST") {
    if (p === "/api/radiation/spe") { sim.spe = !!b.active; return { spe_active: sim.spe }; }
    if (p === "/api/actions") { sim.actions.push({ ...b, done_at: new Date().toISOString() }); return b; }
    if (p === "/api/checkins") return file(sim.spe ? "assessment_spe" : "assessment");
    if (p.startsWith("/api/scenario/")) { Object.assign(sim, { spe: false, queue: [], actions: [] }); return { loaded: "offline" }; }
    if (p === "/api/mission-profile") return file("mission");
    if (p === "/api/downlink/preview") return { summary: await buildSummary(b), meta: await file("downlink") };
    if (p === "/api/downlink") {
      const meta = await file("downlink");
      if (!b.domains?.length && !b.note?.trim() && !b.include_actions) throw new HttpError(p, 422);
      const now = Date.now();
      const it = { id: sim.nextId++, crew_id: b.crew_id, created_at: new Date(now).toISOString(),
        deliver_at: new Date(now + meta.demo_delay_s * 1000).toISOString(),
        meta: { profile: meta.profile, real_one_way_delay_s: meta.real_one_way_delay_s, demo_acceleration: meta.demo_acceleration, demo_delay_s: meta.demo_delay_s },
        summary: await buildSummary(b) };
      sim.queue.push(it); return it;
    }
  }
  if (method === "DELETE" && (m = p.match(/^\/api\/downlink\/(\d+)$/))) {
    sim.queue = sim.queue.filter((it) => it.id !== Number(m[1])); return { cancelled: Number(m[1]) };
  }
  throw new HttpError(path + " (offline)", 404);
}
