// Psychomotor Vigilance Test (PVT) style reaction test.
// All timing is client-side with performance.now(); nothing touches the network during the test.
export function runPVT(container, cfg, onDone) {
  const { durationS, lapseMs, minValidMs, minIntervalMs, maxIntervalMs } = cfg;
  const area = document.createElement("div");
  area.className = "pvt-area";
  area.tabIndex = 0;
  area.setAttribute("role", "button");
  area.setAttribute("aria-label", "Reaction test area. Press Space or tap when the number appears.");
  const big = document.createElement("div"); big.className = "pvt-big"; big.textContent = "Ready";
  const sub = document.createElement("div"); sub.className = "muted";
  sub.textContent = "Press Space or tap here to start";
  area.append(big, sub);
  const stats = document.createElement("div"); stats.className = "pvt-stats";
  container.replaceChildren(area, stats);
  area.focus();

  let state = "idle";          // idle | waiting | stimulus | done
  let startedAt = 0, stimAt = 0, timer = null, tick = null;
  const rts = []; let lapses = 0, falseStarts = 0;

  const showStats = () => {
    const left = Math.max(0, durationS - (performance.now() - startedAt) / 1000);
    stats.textContent = `Time left: ${Math.ceil(left)} s · Responses: ${rts.length} · Lapses: ${lapses} · False starts: ${falseStarts}`;
  };

  function scheduleStimulus() {
    state = "waiting";
    big.textContent = "…"; sub.textContent = "Wait for the number. Do not press yet.";
    area.classList.remove("go");
    const wait = minIntervalMs + Math.random() * (maxIntervalMs - minIntervalMs);
    timer = setTimeout(showStimulus, wait);
  }
  function showStimulus() {
    state = "stimulus";
    area.classList.add("go");
    sub.textContent = "PRESS NOW";
    big.textContent = "0";
    requestAnimationFrame(() => {            // start the clock when the frame is actually painted
      stimAt = performance.now();
      const upd = () => { if (state === "stimulus") { big.textContent = String(Math.round(performance.now() - stimAt)); requestAnimationFrame(upd); } };
      upd();
    });
  }
  function respond() {
    const now = performance.now();
    if (state === "idle") { startedAt = now; tick = setInterval(showStats, 250); showStats(); return scheduleStimulus(); }
    if (state === "waiting") {                // pressed too early
      falseStarts++; clearTimeout(timer); big.textContent = "Too early!"; sub.textContent = "Wait for the number";
      timer = setTimeout(scheduleStimulus, 1000); state = "penalty"; return showStats();
    }
    if (state === "stimulus") {
      const rt = now - stimAt;
      if (rt < minValidMs) falseStarts++;
      else { rts.push(rt); if (rt > lapseMs) lapses++; }
      big.textContent = `${Math.round(rt)} ms`; area.classList.remove("go"); showStats();
      if ((now - startedAt) / 1000 >= durationS) return finish();
      state = "pause"; timer = setTimeout(scheduleStimulus, 700);
    }
  }
  function finish() {
    state = "done"; clearTimeout(timer); clearInterval(tick); cleanup();
    const mean = rts.length ? rts.reduce((a, b) => a + b, 0) / rts.length : null;
    onDone({ mean_rt: mean && Math.round(mean), lapses, false_starts: falseStarts, n: rts.length, duration_s: durationS,
             median_rt: rts.length ? Math.round([...rts].sort((a, b) => a - b)[Math.floor(rts.length / 2)]) : null });
  }
  // Time-up check between trials (the current trial is always finished).
  const watchdog = setInterval(() => {
    if (state === "waiting" && (performance.now() - startedAt) / 1000 >= durationS) finish();
  }, 200);

  const onKey = (e) => { if (e.code === "Space") { e.preventDefault(); if (!e.repeat) respond(); } };
  const onPointer = (e) => { e.preventDefault(); respond(); };
  document.addEventListener("keydown", onKey);
  area.addEventListener("pointerdown", onPointer);
  function cleanup() { document.removeEventListener("keydown", onKey); clearInterval(watchdog); clearInterval(tick); clearTimeout(timer); }
  return { abort: () => { state = "done"; cleanup(); } };
}
