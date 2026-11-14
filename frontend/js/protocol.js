import { api, postJson } from "./api.js";
import { h } from "./dom.js";

// Walks a decision-tree protocol (loaded from the backend YAML). Each completed action is logged.
export async function openProtocol({ crewId, protocolId, onDownlink, modal = true }) {
  const dlg = document.getElementById("protocol-dialog");
  const [p, logged] = await Promise.all([api(`/api/protocols/${protocolId}`), api(`/api/actions/${crewId}`)]);
  const doneBefore = new Set(logged.filter((a) => a.protocol_id === protocolId).map((a) => a.step_id));
  let cur = p.start; const trail = [];

  function render() {
    const n = p.nodes[cur];
    const body = [h("h2", { id: "pr-title" }, p.title),
      h("p", { class: "hint" }, h("span", { class: "badge badge-ASSUMPTION" }, "DRAFT"), " Team-written content, not yet medically reviewed. In a real mission, follow your flight surgeon's procedures."),
      ...trail.map((t) => h("div", { class: "node-done" }, `✓ ${t}`)),
      h("div", { class: "node-now", role: "status" }, n.text)];
    if (n.type === "question") body.push(h("div", { class: "row" }, n.options.map((o) =>
      h("button", { class: "btn primary", onclick: () => { trail.push(`${n.text} → ${o.label}`); cur = o.next; render(); } }, o.label))));
    if (n.type === "action") {
      const done = async () => {
        try { await postJson("/api/actions", { crew_id: crewId, protocol_id: protocolId, step_id: cur }); } catch (e) { /* offline: keep going */ }
        trail.push(n.text); cur = n.next; render();
      };
      body.push(h("div", { class: "row" },
        h("button", { class: "btn primary", onclick: done }, doneBefore.has(cur) ? "Mark done again" : "Mark done"),
        n.ui === "downlink" ? h("button", { class: "btn", onclick: () => { dlg.close(); onDownlink?.(); } }, "Open downlink to Earth") : null));
    }
    if (n.type === "end") body.push(h("div", { class: "row" }, h("button", { class: "btn primary", onclick: () => dlg.close() }, "Close")));
    body.push(h("div", { class: "nav" }, h("button", { class: "btn", onclick: () => dlg.close() }, "Close")));
    dlg.replaceChildren(...body);
    dlg.querySelector(".node-now + .row button, .nav button")?.focus();
  }
  if (dlg.open) dlg.close();
  render(); modal ? dlg.showModal() : dlg.show();  // non-modal in demo mode so the story bar stays clickable
}
