import { h, badge } from "./dom.js";

const fmt = (x) => (x == null ? "–" : Math.abs(x) >= 100 ? Math.round(x) : Math.round(x * 10) / 10);

function spark(m) {
  const vals = (m.history || []).map((x) => (x == null ? null : x));
  const pts = vals.filter((x) => x != null);
  if (pts.length < 2) return null;
  const W = 220, H = 40, lo = Math.min(...pts, m.baseline_mean ?? Infinity), hi = Math.max(...pts, m.baseline_mean ?? -Infinity);
  const y = (v) => H - 4 - ((v - lo) / (hi - lo || 1)) * (H - 8), x = (i) => 4 + (i / (vals.length - 1)) * (W - 8);
  const ns = "http://www.w3.org/2000/svg", svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("width", W); svg.setAttribute("class", "spark");
  svg.setAttribute("role", "img"); svg.setAttribute("aria-label", `Last ${vals.length} days of ${m.label}`);
  if (m.baseline_mean != null) {
    const base = document.createElementNS(ns, "rect"), a = y(m.baseline_mean + m.baseline_sd), b = y(m.baseline_mean - m.baseline_sd);
    Object.entries({ x: 0, y: Math.min(a, b), width: W, height: Math.abs(b - a), fill: "#5ab0ff", "fill-opacity": 0.15 }).forEach(([k, v]) => base.setAttribute(k, v));
    svg.append(base);
  }
  const line = document.createElementNS(ns, "polyline");
  line.setAttribute("points", vals.map((v, i) => (v == null ? null : `${x(i)},${y(v)}`)).filter(Boolean).join(" "));
  line.setAttribute("fill", "none"); line.setAttribute("stroke", "#e9eff9"); line.setAttribute("stroke-width", 2);
  svg.append(line);
  return svg;
}

function metricWhy(m, thr) {
  const prov = badge(m.provenance, m.extra?.formula ? `Formula: ${m.extra.formula}` : m.provenance);
  const cfg = thr.metrics[m.metric];
  const kids = [h("p", {}, h("b", {}, m.label), " ", prov, " ", h("b", { class: `status ${m.status}` }, m.status)),
    h("p", {}, m.reason), spark(m)];
  if (m.baseline_mean != null) kids.push(h("p", {}, `Your pre-flight baseline: ${fmt(m.baseline_mean)} ± ${fmt(m.baseline_sd)} ${m.unit} · z-score today: ${m.z}`));
  if (m.rule) kids.push(h("p", {}, h("b", {}, "Rule: "), m.rule));
  if (m.extra?.formula) kids.push(h("p", {}, h("b", {}, "Formula: "), h("span", { class: "formula" }, m.extra.formula)),
    h("p", {}, "Inputs: " + JSON.stringify(m.extra.inputs || {})));
  if (cfg) kids.push(h("p", {}, h("b", {}, "Threshold source: "), cfg.sim_mean.source_title || "not yet sourced", " ", h("span", { class: `badge badge-${cfg.sim_mean.status}` }, cfg.sim_mean.status)));
  return h("div", { class: "why-metric" }, ...kids);
}

export function renderCards(container, assessment, thr, { onProtocol } = {}) {
  container.replaceChildren(...assessment.domains.map((d) => {
    const flagged = d.triggers.filter((t) => t.status === "AMBER" || t.status === "RED" || t.watch);
    const card = h("article", { class: `card ${d.status}`, "aria-label": `${d.title}: ${d.status}` },
      h("div", { class: "card-head" }, h("h3", {}, d.title), h("span", { class: `status ${d.status}` }, d.status)),
      h("p", { class: "muted", style: "margin:2px 0" }, ""),
      h("p", { class: "meaning" }, d.meaning || ""),
      flagged.length ? h("ul", { class: "triggers" }, flagged.map((t) => h("li", {},
        `${t.label}: ${fmt(t.value)} ${t.unit} `, badge(t.provenance), " ", t.watch ? h("em", {}, `(watching: ${t.days_persisting}/${t.persistence_needed} days)`) : "", h("br"), h("span", { class: "muted" }, t.reason)))) : null,
      d.protocol_id ? h("div", { class: "act" }, h("strong", {}, "What to do now"),
        h("button", { class: "btn", onclick: () => onProtocol?.(d.protocol_id, d) }, "Open action protocol")) : null,
      h("details", { class: "why" }, h("summary", {}, "Why?"),
        h("div", { class: "why-body" }, h("p", {}, h("b", {}, "Domain rule: "), d.rule),
          h("p", {}, "Status is the worst of all metrics below."), ...d.metrics.map((m) => metricWhy(m, thr)))));
    return card;
  }));
}
