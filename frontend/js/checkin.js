import { api, postJson } from "./api.js";
import { h } from "./dom.js";
import { runPVT } from "./pvt.js";

const SCALE = (name, labels) => ({ name, labels });

export async function openCheckin({ crewId, onSubmitted }) {
  const dlg = document.getElementById("checkin-dialog");
  const [symptoms, thr] = await Promise.all([api("/api/symptoms"), api("/api/thresholds")]);
  const pvtCfg = thr.pvt;
  const data = { sleep_hours: 7, sleep_quality: 3, mood: 3, fatigue: 3, symptoms: [], exercise_minutes: 60, pvt: null };
  let step = 0, pvtHandle = null, mode = "demo";

  const scale = (key, low, high) => {
    const fs = h("fieldset", { class: "field" });
    const row = h("div", { class: "scale" });
    for (let i = 1; i <= 5; i++) {
      const id = `${key}-${i}`;
      row.append(h("input", { type: "radio", name: key, id, value: i, checked: data[key] === i,
        onchange: () => (data[key] = i) }), h("label", { for: id }, String(i)));
    }
    fs.append(row, h("div", { class: "hint" }, `1 = ${low} · 5 = ${high}`));
    return fs;
  };
  const num = (key, label, min, max, step_ = 0.5, hint = "") => h("div", { class: "field" },
    h("label", { for: key }, label),
    h("input", { type: "number", id: key, min, max, step: step_, value: data[key],
      oninput: (e) => (data[key] = Number(e.target.value)) }), hint && h("div", { class: "hint" }, hint));

  const steps = [
    { title: "Sleep", body: () => [
      num("sleep_hours", "Hours slept last night", 0, 24, 0.5),
      h("div", { class: "field" }, h("label", {}, "Sleep quality"), scale("sleep_quality", "very poor", "very good"))] },
    { title: "Mood & fatigue", body: () => [
      h("div", { class: "field" }, h("label", {}, "Mood right now"), scale("mood", "very low", "very good")),
      h("div", { class: "field" }, h("label", {}, "Fatigue right now"), scale("fatigue", "not tired", "exhausted"))] },
    { title: "Symptoms", body: () => [h("fieldset", { class: "field" }, h("legend", {}, "Any of these today? (tick all that apply)"),
      h("div", { class: "checks" }, symptoms.map((s) => h("label", {},
        h("input", { type: "checkbox", value: s.id, checked: data.symptoms.includes(s.id),
          onchange: (e) => { data.symptoms = e.target.checked ? [...data.symptoms, s.id] : data.symptoms.filter((x) => x !== s.id); } }),
        s.label))))] },
    { title: "Exercise", body: () => [num("exercise_minutes", "Exercise yesterday/today (minutes)", 0, 600, 5,
      "Resistance + aerobic countermeasure exercise.")] },
    { title: "Reaction test", body: (c) => pvtStep(c), custom: true },
    { title: "Review & submit", body: () => review() },
  ];

  function pvtStep(c) {
    const area = h("div"); const modeSel = h("div", { class: "field" },
      h("label", { for: "pvt-mode" }, "Test length"),
      h("select", { id: "pvt-mode", onchange: (e) => { mode = e.target.value; } },
        h("option", { value: "demo", selected: mode === "demo" }, `Demo (${pvtCfg.demo_duration_s.value} s)`),
        h("option", { value: "standard", selected: mode === "standard" }, `Standard (${pvtCfg.standard_duration_s.value / 60} min)`)),
      h("div", { class: "hint" }, "A number counts up when it appears. Press Space (or tap) as fast as you can. Pressing before it appears is a false start. Responses slower than " + pvtCfg.lapse_ms.value + " ms count as lapses. Timing runs in your browser; no network is used."));
    const startBtn = h("button", { class: "btn primary", onclick: () => {
      modeSel.hidden = true; startBtn.hidden = true; nextBtn(false);
      pvtHandle = runPVT(area, { durationS: pvtCfg[mode + "_duration_s"].value, lapseMs: pvtCfg.lapse_ms.value,
        minValidMs: pvtCfg.min_valid_rt_ms.value, minIntervalMs: pvtCfg.min_interval_ms.value, maxIntervalMs: pvtCfg.max_interval_ms.value },
        (res) => { data.pvt = res; pvtHandle = null; render(); });
    } }, "Start reaction test");
    if (data.pvt) return [pvtSummary()];
    return [modeSel, startBtn, area];
  }
  const pvtSummary = () => h("div", { class: "field" }, h("strong", {}, "Reaction test complete"),
    h("div", { class: "result-row" }, h("span", {}, "Mean reaction time"), h("b", {}, data.pvt.mean_rt == null ? "no valid response" : `${data.pvt.mean_rt} ms`)),
    h("div", { class: "result-row" }, h("span", {}, `Lapses (> ${pvtCfg.lapse_ms.value} ms)`), h("b", {}, String(data.pvt.lapses))),
    h("div", { class: "result-row" }, h("span", {}, "False starts"), h("b", {}, String(data.pvt.false_starts))),
    h("button", { class: "btn", onclick: () => { data.pvt = null; render(); } }, "Redo test"));

  function review() {
    const row = (k, val) => h("div", { class: "result-row" }, h("span", {}, k), h("b", {}, String(val)));
    return [row("Sleep", `${data.sleep_hours} h, quality ${data.sleep_quality}/5`), row("Mood / fatigue", `${data.mood}/5 · ${data.fatigue}/5`),
      row("Symptoms", data.symptoms.length || "none"), row("Exercise", `${data.exercise_minutes} min`),
      row("Reaction test", data.pvt ? `${data.pvt.mean_rt} ms, ${data.pvt.lapses} lapses` : "skipped"),
      h("p", { class: "hint" }, "Stays on this device. Nothing is sent to Earth until you choose it in the downlink queue.")];
  }

  let nextBtnEl;
  const nextBtn = (enabled) => { if (nextBtnEl) nextBtnEl.disabled = !enabled; };

  function render() {
    const s = steps[step], last = step === steps.length - 1;
    nextBtnEl = h("button", { class: "btn primary", onclick: submitOrNext, disabled: s.custom && !data.pvt ? true : false },
      last ? "Submit check-in" : "Next");
    dlg.replaceChildren(
      h("h2", { id: "ci-title" }, `Daily check-in · ${s.title}`),
      h("div", { class: "steps" }, `Step ${step + 1} of ${steps.length}`),
      ...[].concat(s.body()),
      h("div", { class: "nav" },
        h("button", { class: "btn", onclick: () => { pvtHandle?.abort(); step === 0 ? dlg.close() : (step--, render()); } }, step === 0 ? "Cancel" : "Back"),
        s.custom && !data.pvt ? h("button", { class: "btn", onclick: () => { step++; render(); } }, "Skip test") : "",
        nextBtnEl));
    dlg.querySelector("input,select,button")?.focus();
  }
  async function submitOrNext() {
    if (step < steps.length - 1) { step++; return render(); }
    nextBtnEl.disabled = true; nextBtnEl.textContent = "Submitting…";
    const body = { crew_id: crewId, sleep_hours: data.sleep_hours, sleep_quality: data.sleep_quality, mood: data.mood,
      fatigue: data.fatigue, symptoms: data.symptoms, exercise_minutes: data.exercise_minutes };
    if (data.pvt && data.pvt.mean_rt != null) Object.assign(body, { pvt_mean_rt: data.pvt.mean_rt, pvt_lapses: data.pvt.lapses,
      pvt_false_starts: data.pvt.false_starts, pvt_duration_s: data.pvt.duration_s });
    try { const a = await postJson("/api/checkins", body); dlg.close(); onSubmitted(a); }
    catch (e) { nextBtnEl.disabled = false; nextBtnEl.textContent = "Retry submit"; dlg.append(h("p", { class: "banner" }, "Could not save: " + e.message)); }
  }
  dlg.addEventListener("close", () => pvtHandle?.abort(), { once: true });
  render(); dlg.showModal();
}
