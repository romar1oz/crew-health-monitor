import { api, postJson } from "./api.js";
import { h } from "./dom.js";

const SRC = { live: "LIVE · NASA DONKI", cache: "CACHED · NASA DONKI", bundled_sample: "BUNDLED SAMPLE · offline, not real events" };

export function renderRadiation(el, r, sw, { onChange, onProtocol }) {
  const pct = (x) => Math.min(100, (x / r.limit_msv) * 100);
  const events = sw?.events || [];
  // Bar colour reflects the DOSE only; an active solar event is shown separately.
  const doseCls = r.cumulative_dose_msv >= r.red_at_msv ? "RED" : r.cumulative_dose_msv >= r.amber_at_msv ? "AMBER" : "GREEN";
  const bar = h("div", { class: "bar", role: "img", "aria-label": `${r.cumulative_dose_msv} of ${r.limit_msv} millisievert` },
    h("div", { class: `fill ${doseCls}`, style: `width:${pct(r.cumulative_dose_msv)}%` }),
    h("div", { class: "mark", style: `left:${pct(r.amber_at_msv)}%` }, h("span", {}, "AMBER")),
    h("div", { class: "mark", style: `left:${pct(r.red_at_msv)}%` }, h("span", {}, "RED")));
  const feed = h("div", {},
    h("h3", {}, "Solar activity (NASA DONKI) ", sw ? h("span", { class: `src ${sw.source}` }, SRC[sw.source] + (sw.stale ? " (stale)" : "")) : "loading…"),
    sw?.failed_endpoints?.length ? h("p", { class: "hint" }, `Feed unavailable right now: ${sw.failed_endpoints.join(", ")}.`) : null,
    events.length ? h("ul", { class: "feed" }, events.slice(0, 12).map((e) => h("li", {},
      h("b", {}, e.kind), ` ${e.time || ""} · ${e.label}`, e.detail ? ` · ${e.detail}` : "", e.sample ? " (sample, not real)" : ""))) :
      h("p", { class: "muted" }, `No flare or particle events reported${sw?.lookback_days ? ` in the last ${sw.lookback_days} days` : ""}.`),
    h("button", { class: "btn", onclick: async () => { await onChange({ refreshSpace: true }); } }, "Refresh feed"));
  const spe = h("div", { class: "row" },
    r.spe_active ? h("button", { class: "btn", onclick: async () => { await postJson("/api/radiation/spe", { active: false }); onChange({}); } }, "End simulated event")
      : h("button", { class: "btn danger", onclick: async () => { await postJson("/api/radiation/spe", { active: true }); onChange({}); } }, "Simulate solar particle event (demo)"),
    r.protocol_id ? h("button", { class: "btn", onclick: () => onProtocol(r.protocol_id) }, "Open radiation protocol") : null);
  el.replaceChildren(h("div", { class: "rad-grid" },
    h("div", {},
      h("h3", {}, `Cumulative dose: ${r.cumulative_dose_msv} mSv of ${r.limit_msv} mSv career limit (${Math.round(r.fraction * 100)}%)`),
      bar, h("div", { style: "height:22px" }),
      h("p", {}, r.days_to_limit != null ? `At ${r.daily_dose_msv} mSv/day this mission profile reaches the limit in about ${r.days_to_limit} days.` : ""),
      h("p", { class: "hint", title: r.formula }, "How this is calculated: ", h("span", { class: "formula" }, r.formula)),
      h("p", { class: "hint" }, "Modelled from the mission profile, not measured. Limit and rates are unverified ASSUMPTIONS (see SOURCES.md)."),
      spe),
    feed));
}
