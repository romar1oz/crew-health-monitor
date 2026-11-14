import { api, postJson } from "./api.js";
import { h } from "./dom.js";

const LABELS = { cardiovascular: "Cardiovascular", bone: "Bone & Muscle", immune: "Immune", behavioral: "Behavioral & Cognitive", radiation: "Radiation" };
let ticker, items = [];

export function renderDownlink(el, q, crewId, { onSent } = {}) {
  clearInterval(ticker);
  items = q.items;
  const delayTxt = q.real_one_way_delay_s >= 60 ? `${(q.real_one_way_delay_s / 60).toFixed(0)} min` : `${q.real_one_way_delay_s} s`;
  const checks = {}, opts = { include_metrics: false, include_actions: false, note: "" };
  const preview = h("pre", { class: "preview", hidden: true });
  const body = () => ({ crew_id: crewId, domains: Object.keys(checks).filter((k) => checks[k].checked), ...opts });

  const domainBoxes = Object.entries(LABELS).map(([k, label]) => {
    const cb = h("input", { type: "checkbox", id: `dl-${k}`, checked: true }); checks[k] = cb;
    return h("label", {}, cb, label);
  });
  const metricsCb = h("input", { type: "checkbox", id: "dl-metrics", onchange: (e) => (opts.include_metrics = e.target.checked) });
  const actionsCb = h("input", { type: "checkbox", id: "dl-actions", onchange: (e) => (opts.include_actions = e.target.checked) });
  const note = h("textarea", { rows: 2, maxlength: 500, placeholder: "Optional note to the flight surgeon", "aria-label": "Optional note", oninput: (e) => (opts.note = e.target.value) });
  const msg = h("p", { class: "hint", role: "status" });

  const queueEl = h("div", {});
  const form = h("div", {},
    h("p", {}, h("b", {}, "You decide what Earth receives. "), "Nothing leaves the spacecraft until you queue it. ",
      "Everything works offline; the summary is sent when the link is available."),
    h("p", { class: "hint" }, `Mission profile: ${q.profile_label} · one-way delay ${delayTxt} (real). Demo speed ×${q.demo_acceleration}: the countdown below runs ${q.demo_delay_s < 1 ? "almost instantly" : `${q.demo_delay_s.toFixed(1)} s`}.`),
    h("fieldset", {}, h("legend", {}, "Include in summary"), h("div", { class: "checks" }, domainBoxes,
      h("label", {}, metricsCb, "Metric values and reasons (more detail)"), h("label", {}, actionsCb, "Actions I completed"))),
    note,
    h("div", { class: "row" },
      h("button", { class: "btn", onclick: async () => { const r = await postJson("/api/downlink/preview", body()); preview.hidden = false; preview.textContent = JSON.stringify(r.summary, null, 2); } }, "Preview what Earth will see"),
      h("button", { class: "btn primary", onclick: async () => {
        try { await postJson("/api/downlink", body()); preview.hidden = true; msg.textContent = ""; onSent?.(); }
        catch (e) { msg.textContent = "Could not queue: tick at least one item."; } } }, "Queue for Earth")),
    msg, preview);

  function drawQueue() {
    queueEl.replaceChildren(h("h3", {}, "Outbound queue"), ...(items.length ? [] : [h("p", { class: "muted" }, "Nothing queued.")]),
      ...items.map((it) => {
        const cd = h("span", { class: "countdown", "data-deliver": it.deliver_at }, "");
        return h("div", { class: "qitem", "data-id": it.id },
          h("div", {}, h("b", {}, `${it.summary.crew_name}, mission day ${it.summary.mission_day}`), h("br"),
            h("span", { class: "muted" }, `${it.summary.domains.map((d) => `${d.title}: ${d.status}`).join(" · ") || "note only"}`)),
          h("div", {}, cd, " ", it.status === "queued" ? h("button", { class: "btn", onclick: async () => { await api(`/api/downlink/${it.id}`, { method: "DELETE" }); onSent?.(); } }, "Withdraw") : null));
      }));
    tick();
  }
  function tick() {
    for (const cd of queueEl.querySelectorAll(".countdown")) {
      const left = (new Date(cd.dataset.deliver) - Date.now()) / 1000;
      if (left > 0) { cd.className = "countdown"; cd.textContent = `Arrives at Earth in ${left.toFixed(0)} s (demo time)`; }
      else { cd.className = "delivered"; cd.textContent = `✓ Delivered to Earth`; cd.parentElement.querySelector("button")?.remove(); }
    }
  }
  el.replaceChildren(form, queueEl);
  drawQueue();
  ticker = setInterval(tick, 500);
}
