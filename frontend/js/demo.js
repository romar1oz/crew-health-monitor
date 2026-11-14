// Guided 30-second demo story (Mars transit, mission day 120). Each step calls the real app functions.
import { h } from "./dom.js";

export function startStory(ctx) {
  document.getElementById("story")?.remove();
  let i = -1, auto = null;
  const caption = h("div", { class: "story-text", role: "status", "aria-live": "polite" });
  const nextBtn = h("button", { class: "btn primary", onclick: () => next() }, "Next ▶");
  const autoBtn = h("button", { class: "btn", onclick: () => toggleAuto() }, "Auto-play");
  const bar = h("div", { id: "story", class: "story" }, h("span", { class: "badge badge-sim" }, "DEMO · SIMULATED DATA"), caption,
    h("div", { class: "row" }, nextBtn, autoBtn, h("button", { class: "btn", onclick: () => exit() }, "Exit demo")));
  document.body.append(bar);

  const spot = (sel) => {
    document.querySelectorAll(".spotlight").forEach((e) => e.classList.remove("spotlight"));
    const el = typeof sel === "string" ? document.querySelector(sel) : sel;
    if (el) { el.classList.add("spotlight"); el.scrollIntoView({ behavior: "smooth", block: "center" }); }
  };
  const steps = [
    { text: "1/4 · Mars transit, mission day 120. The commander slept badly 3 nights in a row and reaction time slowed. Each is ≥ 2 SD worse than the commander's OWN pre-flight baseline, 3 days in a row → Behavioral AMBER.",
      run: async () => { await ctx.loadScenario(); spot('.card[aria-label^="Behavioral"]'); } },
    { text: "2/4 · Evaluate → ACT. The AMBER card opens an action protocol (decision tree from a content file): protect critical tasks, sleep hygiene, re-test tomorrow. Each step is logged when marked done.",
      run: async () => { await ctx.openProtocol("behavioral_amber"); } },
    { text: "3/4 · A solar particle event begins → Radiation RED → 'Go to the shielded area' protocol, immediately (no waiting period for this safety rule).",
      run: async () => { ctx.closeDialogs(); await ctx.triggerSpe(); spot('.card[aria-label^="Radiation"]'); } },
    { text: "4/4 · The commander chooses what to share. The summary waits in the outbound queue: Mars is 12 light-minutes away (demo runs ×60, so ~12 s).",
      run: async () => { await ctx.queueSummary(); spot("#downlink"); } },
    { text: "Done. Works offline, every number is labelled by origin, and every threshold is traceable (currently marked ASSUMPTION until verified).",
      run: async () => { stopAuto(); nextBtn.disabled = true; } },
  ];
  async function next() {
    if (i >= steps.length - 1) return;
    i++; caption.textContent = steps[i].text; nextBtn.disabled = true;
    try { await steps[i].run(); } finally { if (i < steps.length - 1) nextBtn.disabled = false; }
  }
  function toggleAuto() { if (auto) return stopAuto(); autoBtn.textContent = "Pause"; auto = setInterval(next, 7000); next(); }
  function stopAuto() { clearInterval(auto); auto = null; autoBtn.textContent = "Auto-play"; }
  function exit() { stopAuto(); ctx.closeDialogs(); document.querySelectorAll(".spotlight").forEach((e) => e.classList.remove("spotlight")); bar.remove(); }
  next();
}
