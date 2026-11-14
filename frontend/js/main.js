// CrewCheck frontend entry point (vanilla ES module, no build step).
const el = document.getElementById("health");
try {
  const r = await fetch("/api/health");
  const data = await r.json();
  el.textContent = data.status === "ok" ? "backend OK ✓" : "backend error";
} catch {
  el.textContent = "backend unreachable (fallback demo mode will be used)";
}
