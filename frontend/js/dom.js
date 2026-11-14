// Tiny DOM helper: h("div", {class:"x"}, "text", childNode). Text is always inserted as text (no HTML injection).
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v == null) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) if (c != null && c !== false) el.append(c.nodeType ? c : document.createTextNode(String(c)));
  return el;
}

export function badge(provenance, title) {
  const cls = provenance.replace(/-REPORTED|-ENTERED|-ESTIMATED/, (m) => m); // keep full name class
  return h("span", { class: `badge badge-${cls}`, title: title || provenance }, provenance);
}
