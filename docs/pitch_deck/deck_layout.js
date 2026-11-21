// AmCraX pitch deck layout (pptxgenjs). Called by build_deck.py:
//   <node> deck_layout.js build/deck_data.json AmCraX_Pitch_Deck.pptx build/layout_log.txt
// Every number arrives pre-formatted from build_deck.py (which records its source); this file only lays out.
"use strict";
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const [, , dataPath, outPath, logPath] = process.argv;
const D = JSON.parse(fs.readFileSync(dataPath, "utf8"));
const K = D.colors; // hex without '#'
const LOG = [];
const log = (m) => LOG.push(m);

const FONT = "Segoe UI";
const FONT_SB = "Segoe UI Semibold";
// ASPY = value computed by an AmCraX Python module from an Aspen Plus V15 result (LCOH, carbon intensity, pinch targets)
const SRC_COL = { ASPEN: K.primary, PYTHON: K.python, ASPY: K.cold, LIT: K.ok, ASSUMPTION: K.warn, COMPUTED: K.muted, CODE: K.n2 };
const SRC_TXT = { ASPEN: "ASPEN PLUS V15", PYTHON: "PYTHON MODEL", ASPY: "ASPEN PLUS V15 + PYTHON", LIT: "LITERATURE", ASSUMPTION: "ASSUMPTION", COMPUTED: "COMPUTED", CODE: "CODEBASE" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.title = "AmCraX pitch deck";
pres.subject = "Ammonia Cracking Simulation and Optimisation Platform";
pres.author = "AmCraX team";
pres.company = "AmCraX";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
pres.defineSlideMaster({
  title: "AMCRAX",
  background: { color: K.bg },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.5, w: 12.1, h: 0.85, fontFace: FONT_SB, fontSize: 28, bold: true, color: K.text, align: "left", valign: "middle", margin: 0 }, text: "" } },
  ],
});

let uid = 0;
const nm = (p) => `${p}${++uid}`;
const col = (k) => K[k] || k;

// ------------------------------------------------------------------ primitives
function text(s, t, o) {
  s.addText(t, Object.assign({ isTextBox: true, fontFace: FONT, color: K.text, margin: 0, valign: "top", objectName: nm("txt_") }, o));
}
function box(s, x, y, w, h, fill, o = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, Object.assign({ x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill, width: 0 }, objectName: nm("card_") }, o));
}
function pillW(tag) {
  return Math.max(0.9, 0.075 * (SRC_TXT[tag] || tag).length + 0.3);
}
// pill right-aligned at xRight
function pillR(s, xRight, y, tag, w) {
  return pill(s, xRight - Math.max(w || 0, pillW(tag)), y, tag, w);
}
function pill(s, x, y, tag, w) {
  const c = SRC_COL[tag] || K.muted;
  const label = SRC_TXT[tag] || tag;
  const ww = Math.max(w || 0, pillW(tag)); // never narrower than the label needs
  s.addText(label, { isTextBox: true, x, y, w: ww, h: 0.24, fontFace: FONT_SB, fontSize: 8.5, bold: true, color: c, align: "center", valign: "middle", margin: 0,
    shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.12, line: { color: c, width: 0.75 }, fill: { color: K.surface }, objectName: nm("pill_") });
  return ww;
}
function frame(s, d) {
  if (d.section) text(s, d.section.toUpperCase(), { x: 0.6, y: 0.2, w: 9, h: 0.3, fontSize: 12, bold: true, color: K.primary, charSpacing: 2, objectName: nm("tag_") });
  s.addText(d.title, { placeholder: "title", align: "left" });
  footer(s, d);
}
function footer(s, d) {
  text(s, d.source, { x: 0.6, y: 6.66, w: 12.1, h: 0.44, fontSize: 10.5, color: K.muted, valign: "bottom", objectName: nm("src_") });
  text(s, "AmCraX", { x: 0.6, y: 7.16, w: 3, h: 0.22, fontSize: 9, bold: true, color: K.muted, objectName: nm("foot_") });
  text(s, `${d.n} / ${D.total}`, { x: 11.7, y: 7.16, w: 1.0, h: 0.22, fontSize: 9, color: K.muted, align: "right", objectName: nm("foot_") });
  s.addNotes(d.notes);
}
function numCard(s, x, y, w, h, c) {
  box(s, x, y, w, h, K.surface);
  const accent = col(c.c || "text");
  text(s, c.v, { x: x + 0.2, y: y + 0.14, w: w - 0.4, h: 0.55, fontSize: h > 1.3 ? 28 : 26, bold: true, fontFace: FONT_SB, color: accent, valign: "middle", objectName: nm("num_") });
  text(s, c.l, { x: x + 0.2, y: y + 0.72, w: w - 0.4, h: h - 0.95, fontSize: 13, color: K.text2 });
  if (c.tag) pill(s, x + 0.2, y + h - 0.32, c.tag);
}
function chip(s, x, y, w, h, label, c, sub) {
  box(s, x, y, w, h, K.surface2);
  s.addShape(pres.shapes.OVAL, { x: x + 0.18, y: y + h / 2 - 0.08, w: 0.16, h: 0.16, fill: { color: col(c) }, line: { color: col(c), width: 0 }, objectName: nm("dot_") });
  if (sub) {
    text(s, label, { x: x + 0.45, y: y + 0.1, w: w - 0.55, h: 0.32, fontSize: 15, bold: true, color: col(c) });
    text(s, sub, { x: x + 0.45, y: y + 0.42, w: w - 0.55, h: h - 0.5, fontSize: 13, color: K.text });
  } else {
    text(s, label, { x: x + 0.45, y, w: w - 0.55, h, fontSize: 16, bold: true, color: K.text, valign: "middle" });
  }
}
function pending(s, x, y, w, h, what, file) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: K.surface }, line: { color: K.accent, width: 1.5, dashType: "dash" }, objectName: nm("pending_") });
  text(s, [
    { text: "RESULT PENDING", options: { fontSize: 22, bold: true, color: K.accent, breakLine: true } },
    { text: what, options: { fontSize: 14, color: K.text, breakLine: true } },
    { text: file, options: { fontSize: 12, color: K.muted } },
  ], { x: x + 0.3, y, w: w - 0.6, h, valign: "middle", align: "center", paraSpaceAfter: 6 });
  log(`pending marker on slide: ${what}`);
}
function leadLines(s, items, o, leadCol) {
  const runs = [];
  items.forEach(([lead, body], i) => {
    runs.push({ text: lead + "  ", options: { bold: true, color: col(leadCol || "primary") } });
    runs.push({ text: body, options: { color: K.text, breakLine: i < items.length - 1 } });
  });
  text(s, runs, Object.assign({ paraSpaceAfter: 8 }, o));
}
function image(s, info, x, y, w, h, name) {
  const r = info.px_w / info.px_h;
  let iw = w, ih = w / r;
  if (ih > h) { ih = h; iw = h * r; }
  s.addImage({ path: info.path, x: x + (w - iw) / 2, y: y + (h - ih) / 2, w: iw, h: ih, objectName: nm(name || "img_"), altText: name || "image" });
  return { x: x + (w - iw) / 2, y: y + (h - ih) / 2, w: iw, h: ih };
}
function chartBase(extra) {
  return Object.assign({
    chartArea: { fill: { color: K.bg } }, plotArea: { fill: { color: K.bg } },
    catAxisLabelColor: K.text2, valAxisLabelColor: K.text2, catAxisLabelFontSize: 12, valAxisLabelFontSize: 12,
    catAxisLabelFontFace: FONT, valAxisLabelFontFace: FONT, dataLabelFontFace: FONT, dataLabelFontSize: 12, dataLabelColor: K.text,
    titleFontFace: FONT, titleFontSize: 13, titleColor: K.text2, showTitle: true,
    valGridLine: { color: "26304D", size: 0.75 }, catGridLine: { style: "none" },
    catAxisLineShow: false, valAxisLineShow: false, showLegend: false,
    legendFontFace: FONT, legendFontSize: 12, legendColor: K.text2,
  }, extra);
}

// ------------------------------------------------------------------ slides
const R = {};

R.title = (s, d) => {
  // molecule glyph (native shapes): N with three H, one bond cut by the X
  const cx = 10.55, cy = 2.35;
  const H = [[-1.25, 0.95], [1.25, 0.95], [0, -1.35]];
  H.forEach(([dx, dy], i) => {
    s.addShape(pres.shapes.LINE, { x: Math.min(cx, cx + dx), y: Math.min(cy, cy + dy), w: Math.abs(dx), h: Math.abs(dy), flipH: dx < 0 && dy > 0 || dx > 0 && dy < 0, line: { color: i === 2 ? K.accent : K.border, width: 3, dashType: i === 2 ? "dash" : "solid" }, objectName: nm("glyph_") });
  });
  s.addShape(pres.shapes.OVAL, { x: cx - 0.6, y: cy - 0.6, w: 1.2, h: 1.2, fill: { color: K.surface2 }, line: { color: K.n2, width: 2.5 }, objectName: nm("glyph_") });
  text(s, "N", { x: cx - 0.6, y: cy - 0.6, w: 1.2, h: 1.2, fontSize: 34, bold: true, color: K.n2, align: "center", valign: "middle", objectName: nm("glyph_") });
  H.forEach(([dx, dy]) => {
    s.addShape(pres.shapes.OVAL, { x: cx + dx - 0.36, y: cy + dy - 0.36, w: 0.72, h: 0.72, fill: { color: K.surface2 }, line: { color: K.h2, width: 2.5 }, objectName: nm("glyph_") });
    text(s, "H", { x: cx + dx - 0.36, y: cy + dy - 0.36, w: 0.72, h: 0.72, fontSize: 22, bold: true, color: K.h2, align: "center", valign: "middle", objectName: nm("glyph_") });
  });
  text(s, "X", { x: cx - 0.32, y: cy - 1.05, w: 0.6, h: 0.5, fontSize: 26, bold: true, color: K.accent, align: "center", valign: "middle", objectName: nm("glyph_") });

  text(s, "AMMONIA CRACKING  ·  HYDROGEN SUPPLY", { x: 0.6, y: 0.75, w: 8, h: 0.35, fontSize: 14, bold: true, color: K.primary, charSpacing: 3, objectName: nm("tag_") });
  s.addText([
    { text: "Am", options: { color: K.text } }, { text: "Cra", options: { color: K.primary } }, { text: "X", options: { color: K.accent } },
  ], { isTextBox: true, x: 0.6, y: 1.2, w: 7.5, h: 1.25, fontSize: 72, bold: true, fontFace: FONT_SB, valign: "middle", margin: 0, objectName: "title_wordmark" });
  text(s, d.subtitle, { x: 0.6, y: 2.5, w: 8.2, h: 0.45, fontSize: 21, color: K.text2 });
  text(s, d.value, { x: 0.6, y: 3.15, w: 7.9, h: 1.05, fontSize: 16, color: K.text, lineSpacingMultiple: 1.1 });
  const pc = ["primary", "python", "n2", "nh3"];
  d.pillars.forEach((p, i) => {
    const x = 0.6 + i * 3.07;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 4.45, w: 2.9, h: 0.5, rectRadius: 0.25, fill: { color: K.surface }, line: { color: col(pc[i]), width: 1 }, objectName: nm("card_") });
    text(s, p, { x, y: 4.45, w: 2.9, h: 0.5, fontSize: 13, bold: true, color: col(pc[i]), align: "center", valign: "middle" });
  });
  box(s, 0.35, 5.3, 12.63, 1.3, K.surface);
  d.stats.forEach((st, i) => {
    const x = 0.6 + i * 3.12;
    text(s, st.v, { x, y: 5.4, w: 2.9, h: 0.5, fontSize: 24, bold: true, fontFace: FONT_SB, color: i === 0 ? K.nh3 : K.text, objectName: nm("num_") });
    text(s, st.l, { x, y: 5.88, w: 2.9, h: 0.42, fontSize: 12, color: K.text2 });
    pill(s, x, 6.3, st.tag);
  });
  footer(s, d); // footer() also adds the speaker notes
};

R.challenge = (s, d) => {
  frame(s, d);
  d.cards.forEach((c, i) => numCard(s, 0.6 + i * 3.05, 1.65, 2.9, 1.75, c));
  leadLines(s, d.bullets, { x: 0.6, y: 3.8, w: 12.1, h: 2.6, fontSize: 20, paraSpaceAfter: 12 });
};

R.ammonia = (s, d) => {
  frame(s, d);
  d.kpis.forEach((c, i) => numCard(s, 0.6, 1.6 + i * 1.67, 3.7, 1.55, c));
  s.addChart(pres.charts.BAR, [
    { name: "Hydrogen", labels: ["Mass share in NH3 (%)"], values: [d.chart.h] },
    { name: "Nitrogen", labels: ["Mass share in NH3 (%)"], values: [d.chart.n] },
  ], chartBase({ x: 4.7, y: 1.6, w: 8.0, h: 2.3, barDir: "bar", barGrouping: "stacked", chartColors: [K.h2, K.n2],
    showValue: true, dataLabelPosition: "ctr", dataLabelColor: K.bg, dataLabelFontSize: 14, dataLabelFontBold: true, dataLabelFormatCode: '0.0"%"',
    title: "Where the mass of an ammonia molecule sits (%)", showLegend: true, legendPos: "b", valAxisMaxVal: 100, valAxisHidden: true, catAxisHidden: true, valGridLine: { style: "none" }, barGapWidthPct: 40, objectName: nm("chart_") }));
  leadLines(s, d.takeaway, { x: 4.7, y: 4.25, w: 8.0, h: 2.2, fontSize: 18, paraSpaceAfter: 14 }, "nh3");
};

R.cracking = (s, d) => {
  frame(s, d);
  box(s, 0.6, 1.6, 5.95, 4.95, K.surface);
  text(s, d.left.head, { x: 0.85, y: 1.8, w: 5.5, h: 0.4, fontSize: 21, bold: true, color: K.nh3 });
  text(s, [
    { text: "NH", options: { color: K.nh3 } }, { text: "3", options: { color: K.nh3, subscript: true } },
    { text: "  →  ½ ", options: { color: K.text } }, { text: "N", options: { color: K.n2 } }, { text: "2", options: { color: K.n2, subscript: true } },
    { text: "  +  1.5 ", options: { color: K.text } }, { text: "H", options: { color: K.h2 } }, { text: "2", options: { color: K.h2, subscript: true } },
  ], { x: 0.85, y: 2.4, w: 5.5, h: 0.7, fontSize: 28, bold: true, objectName: nm("eq_") });
  leadLines(s, d.left.items, { x: 0.85, y: 3.4, w: 5.5, h: 3.0, fontSize: 17, paraSpaceAfter: 14 }, "nh3");
  box(s, 6.75, 1.6, 5.95, 4.95, K.surface);
  text(s, d.right_head, { x: 7.0, y: 1.8, w: 5.5, h: 0.4, fontSize: 21, bold: true, color: K.accent });
  s.addChart(pres.charts.BAR, [{ name: "kJ per mol H2", labels: d.chart.labels, values: d.chart.values }], chartBase({
    x: 7.0, y: 2.35, w: 5.45, h: 2.75, barDir: "bar", chartColors: [K.accent, K.muted], invertedColors: [K.accent, K.muted],
    chartArea: { fill: { color: K.surface } }, plotArea: { fill: { color: K.surface } },
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0##", title: d.chart.title, valAxisHidden: true, valGridLine: { style: "none" }, barGapWidthPct: 45, catAxisOrientation: "maxMin", objectName: nm("chart_") }));
  text(s, d.takeaway, { x: 7.0, y: 5.3, w: 5.45, h: 1.0, fontSize: 16, color: K.text });
};

R.intro = (s, d) => {
  frame(s, d);
  d.chips.forEach(([label, c], i) => {
    const x = 0.6 + i * 3.05;
    s.addText(label, { isTextBox: true, x, y: 1.65, w: 2.9, h: 0.7, shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.1, fill: { color: col(c) }, line: { color: col(c), width: 0 },
      fontFace: FONT_SB, fontSize: 18, bold: true, color: K.bg, align: "center", valign: "middle", margin: 0, objectName: nm("chipf_") });
    if (i < 3) text(s, "›", { x: x + 2.9, y: 1.65, w: 0.15, h: 0.7, fontSize: 22, bold: true, color: K.muted, align: "center", valign: "middle", objectName: nm("pfd_") });
  });
  d.cards.forEach(([head, body, tag], i) => {
    const x = 0.6 + i * 3.05;
    box(s, x, 2.65, 2.9, 2.85, K.surface);
    pill(s, x + 0.2, 2.85, tag);
    text(s, head, { x: x + 0.2, y: 3.25, w: 2.5, h: 0.75, fontSize: 18, bold: true, color: K.text });
    text(s, body, { x: x + 0.2, y: 4.05, w: 2.5, h: 1.35, fontSize: 14, color: K.text2 });
  });
  if (d.pending_note) pending(s, 0.6, 5.75, 12.1, 0.8, d.note, "python -m pytest tests -q --collect-only");
  else text(s, [{ text: "Proof it runs  ", options: { bold: true, color: K.ok } }, { text: d.note, options: { color: K.text } }], { x: 0.6, y: 5.85, w: 12.1, h: 0.5, fontSize: 18 });
};

function drawPFD(s, fsj, X0, Y0, W, H) {
  box(s, X0, Y0, W, H, K.surface);
  const ax = X0 + 0.15, ay = Y0 + 0.35, aw = W - 0.3, ah = H - 0.75;
  const bw = 0.98, bh = 0.62;
  const blocks = {};
  const secCol = { feed: K.nh3, reaction: K.accent, recovery: K.primary, purification: K.h2, combustion: K.heat };
  fsj.blocks.forEach((b) => {
    const cx = ax + (b.pfd.x - 20) / 1360 * aw;
    const cy = ay + (b.pfd.y - 180) / 540 * ah;
    blocks[b.id] = { cx, cy, l: cx - bw / 2, r: cx + bw / 2, t: cy - bh / 2, b: cy + bh / 2, sec: b.section, type: b.aspen_type };
  });
  const scol = (st) => {
    if (["FEED", "S1", "S2", "S3", "S4"].includes(st.id)) return K.nh3;
    if (["S5", "S6", "S7", "H2PROD"].includes(st.id)) return K.h2;
    if (st.id === "TAILGAS") return K.n2;
    if (["FLUE", "STACK"].includes(st.id)) return K.heat;
    return K.muted;
  };
  function seg(x1, y1, x2, y2, c, arrow, wd) {
    const dx = x2 - x1, dy = y2 - y1;
    const o = { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.max(Math.abs(dx), 0.001), h: Math.max(Math.abs(dy), 0.001), line: { color: c, width: wd || 2 }, objectName: nm("pfd_") };
    if (dx < 0) o.flipH = true;
    if (dy < 0) o.flipV = true;
    if (arrow) o.line.endArrowType = "triangle";
    s.addShape(pres.shapes.LINE, o);
  }
  function route(st) {
    const f = blocks[st.from], t = blocks[st.to];
    const edgeR = ax + aw;
    switch (st.id) {
      case "FEED": return [[X0 + 0.12, t.cy], [t.l, t.cy]];
      case "S5": { const my = (f.b + blocks.COOLER.t) / 2; return [[f.cx, f.b], [f.cx, my], [t.cx + 0.25, my], [t.cx + 0.25, t.b]]; }
      case "S6": return [[f.cx - 0.25, f.b], [f.cx - 0.25, t.t]];
      case "H2PROD": return [[f.r, f.cy], [edgeR - 0.05, f.cy]];
      case "TAILGAS": return [[f.cx, f.b], [f.cx, t.cy], [t.l, t.cy]];
      case "AIR": return [[t.cx, Y0 + H - 0.08], [t.cx, t.b]];
      case "STACK": return [[f.r, f.cy], [Math.min(f.r + 0.6, X0 + W - 0.08), f.cy]];
      default:
        if (!f || !t) return null;
        if (Math.abs(f.cy - t.cy) < 0.01) return f.cx < t.cx ? [[f.r, f.cy], [t.l, t.cy]] : [[f.l, f.cy], [t.r, t.cy]];
        return [[f.cx, f.cy < t.cy ? f.b : f.t], [f.cx, t.cy], [f.cx < t.cx ? t.l : t.r, t.cy]];
    }
  }
  const labelPos = { FEED: "a", S1: "a", S2: "a", S3: "a", S4: "a", S5: "b", S6: "l", S7: "a", H2PROD: "a", TAILGAS: "l", AIR: "r", FLUE: "a", STACK: "a" };
  fsj.streams.forEach((st) => {
    if (st.requires && !blocks[st.requires]) return;
    const pts = route(st);
    if (!pts) { log(`PFD: no route for ${st.id}`); return; }
    const c = scol(st);
    for (let i = 0; i < pts.length - 1; i++) seg(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], c, i === pts.length - 2, st.id === "H2PROD" ? 3 : 2);
    // label on longest segment
    let best = 0, bl = -1;
    for (let i = 0; i < pts.length - 1; i++) { const l = Math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]); if (l > bl) { bl = l; best = i; } }
    const mx = (pts[best][0] + pts[best + 1][0]) / 2, my = (pts[best][1] + pts[best + 1][1]) / 2;
    const pos = labelPos[st.id] || "a";
    const lab = st.id === "H2PROD" ? "H2 product" : st.id;
    const lw = 0.11 * lab.length + 0.2;
    const lx = pos === "l" ? mx - lw - 0.05 : pos === "r" ? mx + 0.07 : mx - lw / 2;
    const shortSeg = bl < 0.7 && Math.abs(pts[best][1] - pts[best + 1][1]) < 0.01;
    const ly = pos === "a" ? (shortSeg ? my - bh / 2 - 0.28 : my - 0.3) : pos === "b" ? my + 0.03 : my - 0.13;
    text(s, lab, { x: lx, y: ly, w: lw, h: 0.26, fontSize: 11, bold: st.id === "H2PROD", color: c, align: pos === "l" ? "right" : pos === "r" ? "left" : "center", valign: "middle", objectName: nm("pfd_") });
  });
  Object.entries(blocks).forEach(([id, b]) => {
    const c = secCol[b.sec] || K.text2;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: b.l, y: b.t, w: bw, h: bh, rectRadius: 0.08, fill: { color: K.surface2 }, line: { color: c, width: 1.5, dashType: id === "PSA" ? "dash" : "solid" }, objectName: nm("pfd_") });
    text(s, [{ text: id, options: { fontSize: 12, bold: true, color: K.text, breakLine: true } }, { text: b.type, options: { fontSize: 10, color: K.text2 } }],
      { x: b.l, y: b.t, w: bw, h: bh, align: "center", valign: "middle", objectName: nm("pfd_") });
  });
  // legend
  const lg = [["NH3 feed", K.nh3], ["H2-rich gas", K.h2], ["N2-rich tail gas", K.n2], ["Flue gas", K.heat]];
  lg.forEach(([l, c], i) => {
    const x = X0 + 0.25 + i * 1.75;
    s.addShape(pres.shapes.LINE, { x, y: Y0 + 0.2, w: 0.35, h: 0.001, line: { color: c, width: 3 }, objectName: nm("pfd_") });
    text(s, l, { x: x + 0.42, y: Y0 + 0.08, w: 1.3, h: 0.25, fontSize: 11, color: K.text2, valign: "middle", objectName: nm("pfd_") });
  });
  text(s, "dashed = reduced-order", { x: X0 + W - 2.3, y: Y0 + 0.08, w: 2.1, h: 0.25, fontSize: 11, color: K.text2, align: "right", valign: "middle", objectName: nm("pfd_") });
}

R.pfd = (s, d) => {
  frame(s, d);
  if (d.screenshot) image(s, d.screenshot, 0.6, 1.5, 8.9, 4.9, "dashboard_pfd");
  else drawPFD(s, d.flowsheet, 0.6, 1.5, 8.9, 4.9);
  text(s, d.caption, { x: 0.6, y: 6.43, w: 8.9, h: 0.28, fontSize: 11, italic: true, color: K.text2, objectName: nm("cap_") });
  d.chips.forEach(([h, v, c], i) => chip(s, 9.75, 1.5 + i * 1.22, 2.95, 1.08, h, c, v));
};

R.aspen = (s, d) => {
  frame(s, d);
  const r = image(s, d.screenshot, 0.6, 1.5, 8.3, 4.9, "aspen_flowsheet_screenshot");
  s.addShape(pres.shapes.RECTANGLE, { x: r.x, y: r.y, w: r.w, h: r.h, fill: { type: "none" }, line: { color: K.border, width: 1 }, objectName: nm("frame_") });
  text(s, d.caption, { x: 0.6, y: 6.43, w: 8.3, h: 0.28, fontSize: 11, italic: true, color: K.text2, objectName: nm("cap_") });
  d.chips.forEach(([label, c], i) => chip(s, 9.15, 1.5 + i * 0.98, 3.55, 0.82, label, c));
};

R.reactor = (s, d) => {
  frame(s, d);
  d.kpis.forEach((c, i) => numCard(s, 0.6, 1.6 + i * 1.67, 3.7, 1.55, c));
  text(s, d.fig_title, { x: 4.6, y: 1.55, w: 8.1, h: 0.3, fontSize: 13, color: K.text2 });
  s.addImage({ path: d.figure.path, x: 4.6, y: 1.9, w: d.figure.w, h: d.figure.h, objectName: nm("img_"), altText: "Equilibrium conversion versus temperature, Python curves and Aspen points" });
  const ty = 1.9 + d.figure.h + 0.15;
  leadLines(s, d.pending ? d.takeaway.slice(0, 2) : d.takeaway, { x: 4.6, y: ty, w: 8.1, h: 0.95, fontSize: 15, paraSpaceAfter: 3 }, "primary");
  if (d.pending) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.6, y: 6.17, w: 8.1, h: 0.42, rectRadius: 0.06, fill: { color: K.surface }, line: { color: K.accent, width: 1.25, dashType: "dash" }, objectName: nm("pending_") });
    text(s, [{ text: "RESULT PENDING  ", options: { bold: true, color: K.accent } }, { text: d.pending, options: { color: K.text2 } }], { x: 4.75, y: 6.17, w: 7.8, h: 0.42, fontSize: 12, valign: "middle" });
    log("pending marker on slide: kinetic PFR");
  }
};

R.dashboard = (s, d) => {
  frame(s, d);
  if (d.screenshot) {
    const r = image(s, d.screenshot, 0.6, 1.5, 8.3, 4.9, "dashboard_screenshot");
    s.addShape(pres.shapes.RECTANGLE, { x: r.x, y: r.y, w: r.w, h: r.h, fill: { type: "none" }, line: { color: K.border, width: 1 }, objectName: nm("frame_") });
    text(s, d.caption, { x: 0.6, y: 6.43, w: 8.3, h: 0.28, fontSize: 11, italic: true, color: K.text2, objectName: nm("cap_") });
  } else pending(s, 0.6, 1.5, 8.3, 4.9, "Actual AmCraX dashboard screenshot", "docs/screenshots/dashboard_*.png");
  d.chips.forEach(([label, c], i) => chip(s, 9.15, 1.5 + i * 0.86, 3.55, 0.74, label, c));
  text(s, d.footnote, { x: 9.15, y: 5.9, w: 3.55, h: 0.6, fontSize: 13, color: K.text2 });
};

R.sensitivity = (s, d) => {
  frame(s, d);
  const LW = 6.3;
  if (d.tp) {
    // Aspen T-P conversion map, native dark chart: one line per pressure
    const pc = [K.nh3, K.primary, K.python, K.h2, K.accent];
    s.addChart(pres.charts.LINE, d.tp.series.map((sr) => ({ name: sr.name, labels: d.tp.labels, values: sr.values })), chartBase({
      x: 0.6, y: 1.55, w: LW, h: 4.15, chartColors: pc.slice(0, d.tp.series.length), lineSize: 2.5, lineDataSymbol: "circle", lineDataSymbolSize: 6,
      title: "T-P map: NH3 conversion (%)", showCatAxisTitle: true, catAxisTitle: "Reactor temperature (°C)", catAxisTitleColor: K.text2, catAxisTitleFontSize: 12,
      valAxisLabelFormatCode: "0", valAxisMaxVal: 100, showLegend: true, legendPos: "b", objectName: nm("chart_"),
    }));
    pillR(s, 0.6 + LW - 0.05, 1.6, "ASPEN");
  } else {
    s.addChart(pres.charts.LINE, [{ name: "H2 product", labels: d.chart.labels, values: d.chart.values }], chartBase({
      x: 0.6, y: 1.55, w: LW, h: 4.15, chartColors: [K.primary], lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 7,
      title: d.chart.title, showCatAxisTitle: true, catAxisTitle: "Reactor temperature (°C)", catAxisTitleColor: K.text2, catAxisTitleFontSize: 12,
      catAxisLabelFrequency: 2, valAxisLabelFormatCode: "0", objectName: nm("chart_"),
    }));
  }
  const X = 7.15, Y = 1.55, W = 5.55, Hh = 4.15;
  const o = d.opt;
  if (!o) pending(s, X, Y, W, Hh, "Minimum-LCOH optimum and its Aspen re-solve", "results/optimisation/single_objective.json, aspen_verification.json");
  else {
    box(s, X, Y, W, Hh, K.surface);
    text(s, "Minimum-LCOH design point", { x: X + 0.25, y: Y + 0.15, w: W - 0.5 - pillW("PYTHON"), h: 0.4, fontSize: 18, bold: true, color: K.accent });
    pillR(s, X + W - 0.2, Y + 0.22, "PYTHON");
    o.rows.forEach(([lab, v], i) => {
      const cx = X + 0.25 + (i % 2) * 2.6, cy = Y + 0.65 + Math.floor(i / 2) * 0.62;
      text(s, v, { x: cx, y: cy, w: 1.25, h: 0.5, fontSize: 19, bold: true, fontFace: FONT_SB, color: K.text, valign: "middle", objectName: nm("num_") });
      text(s, lab, { x: cx + 1.25, y: cy, w: 1.3, h: 0.5, fontSize: 12, color: K.text2, valign: "middle" });
    });
    text(s, o.lcoh, { x: X + 0.25, y: Y + 1.95, w: W - 0.5, h: 0.42, fontSize: 18, bold: true, fontFace: FONT_SB, color: K.nh3, valign: "middle", objectName: nm("num_") });
    text(s, o.lcoh_l, { x: X + 0.25, y: Y + 2.37, w: W - 0.5, h: 0.3, fontSize: 12, color: K.text2 });
    pill(s, X + 0.25, Y + 2.78, "ASPY");
    if (o.aspen) text(s, o.aspen, { x: X + 0.25, y: Y + 3.08, w: W - 0.5, h: 0.5, fontSize: 12, color: K.text });
    else text(s, [{ text: "RESULT PENDING  ", options: { bold: true, color: K.accent } }, { text: o.aspen_pending, options: { color: K.text2 } }], { x: X + 0.25, y: Y + 3.08, w: W - 0.5, h: 0.5, fontSize: 12 });
    text(s, o.honest, { x: X + 0.25, y: Y + 3.6, w: W - 0.5, h: 0.5, fontSize: 11, italic: true, color: K.warn });
  }
  text(s, d.takeaway, { x: 0.6, y: 5.9, w: 12.1, h: 0.6, fontSize: 16, color: K.text, valign: "middle" });
};

R.heat = (s, d) => {
  frame(s, d);
  d.cards.forEach((c, i) => numCard(s, 0.6 + i * 3.05, 1.55, 2.9, 1.65, c));
  s.addChart(pres.charts.BAR, [{ name: "External heating (kW)", labels: d.chart.labels, values: d.chart.values }], chartBase({
    x: 0.6, y: 3.4, w: 7.5, h: 3.2, barDir: "bar", chartColors: [K.muted, K.primary, K.accent, K.h2],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "#,##0", title: d.chart.title, valAxisHidden: true, valGridLine: { style: "none" },
    catAxisOrientation: "maxMin", barGapWidthPct: 45, objectName: nm("chart_") }));
  leadLines(s, d.bullets, { x: 8.4, y: 3.5, w: 4.3, h: 3.0, fontSize: 16, paraSpaceAfter: 14 }, "primary");
};

// framed picture (thin border) so dark screenshots separate from the slide background
function framedImage(s, info, x, y, w, h, name) {
  const r = image(s, info, x, y, w, h, name);
  s.addShape(pres.shapes.RECTANGLE, { x: r.x, y: r.y, w: r.w, h: r.h, fill: { type: "none" }, line: { color: K.border, width: 1 }, objectName: nm("frame_") });
  return r;
}

R.website = (s, d) => {
  frame(s, d);
  const Y = 1.5, H = 4.0, DW = 7.05;
  // desktop picture anchored top-left; phone picture right next to it (both keep their aspect ratio)
  let px = 0.6 + DW + 0.2, bottom = Y + H;
  if (d.desk) {
    const r = d.desk.px_w / d.desk.px_h;
    const w = Math.min(DW, H * r), h = w / r;
    framedImage(s, d.desk, 0.6, Y, w, h, "site_desktop_screenshot");
    px = 0.6 + w + 0.2;
    bottom = Y + h;
  } else pending(s, 0.6, Y, DW, H, "Public website screenshot (desktop)", "docs/screenshots/site_home_desktop.png");
  if (d.mob) {
    const r = d.mob.px_w / d.mob.px_h;
    const pr = framedImage(s, d.mob, px, Y, Math.min(1.95, H * r), H, "site_phone_screenshot");
    bottom = Math.max(bottom, pr.y + pr.h);
  } else pending(s, px, Y, 1.95, H, "Phone view", "docs/screenshots/site_home_mobile.png");
  text(s, "Actual screenshots of the public site: desktop and phone", { x: 0.6, y: Math.min(bottom + 0.06, 5.56), w: 8.9, h: 0.26, fontSize: 11, italic: true, color: K.text2, objectName: nm("cap_") });
  d.chips.forEach(([label, c], i) => chip(s, 9.85, Y + i * 0.83, 2.85, 0.68, label, c));
  const runs = [];
  d.links.forEach(([lab, url], i) => {
    runs.push({ text: lab + "  ", options: { bold: true, color: K.text2 } });
    runs.push({ text: url || "address pending", options: { bold: true, color: K.primary } });
    if (i < d.links.length - 1) runs.push({ text: "      ", options: {} });
  });
  text(s, runs, { x: 0.6, y: 5.88, w: 12.1, h: 0.36, fontSize: 16, valign: "middle", objectName: nm("link_") });
  text(s, d.boundary, { x: 0.6, y: 6.27, w: 12.1, h: 0.3, fontSize: 13, italic: true, color: K.warn, valign: "middle" });
};

R.results = (s, d) => {
  frame(s, d);
  d.cards.forEach((c, i) => numCard(s, 0.6 + (i % 2) * 3.0, 1.55 + Math.floor(i / 2) * 1.62, 2.85, 1.5, c));
  // purity note: an input consequence, not a prediction (fact sheet F4)
  box(s, 0.6, 4.85, 5.85, 0.98, K.surface);
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 4.85, w: 0.07, h: 0.98, fill: { color: K.warn }, line: { color: K.warn, width: 0 }, objectName: nm("bar_") });
  text(s, d.purity, { x: 0.85, y: 4.85, w: 4.0, h: 0.98, fontSize: 14, color: K.text, valign: "middle" });
  pillR(s, 6.3, 5.22, "ASSUMPTION");
  const X = 6.75, W = 5.95;
  if (d.tp) {
    const pc = [K.nh3, K.primary, K.python, K.h2, K.accent];
    s.addChart(pres.charts.LINE, d.tp.series.map((sr) => ({ name: sr.name, labels: d.tp.labels, values: sr.values })), chartBase({
      x: X, y: 1.45, w: W, h: 4.4, chartColors: pc.slice(0, d.tp.series.length), lineSize: 2.5, lineDataSymbol: "circle", lineDataSymbolSize: 6,
      title: "Aspen T-P map: NH3 conversion (%)", showCatAxisTitle: true, catAxisTitle: "Reactor temperature (°C)", catAxisTitleColor: K.text2, catAxisTitleFontSize: 12,
      valAxisLabelFormatCode: "0", valAxisMaxVal: 100, showLegend: true, legendPos: "b", objectName: nm("chart_"),
    }));
    pillR(s, X + W - 0.05, 1.5, "ASPEN");
  } else {
    s.addChart(pres.charts.LINE, [{ name: "NH3 conversion", labels: d.chart.labels, values: d.chart.values }], chartBase({
      x: X, y: 1.45, w: W, h: 4.4, chartColors: [K.primary], lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 7,
      title: d.chart.title, catAxisLabelFrequency: 2, valAxisLabelFormatCode: "0", objectName: nm("chart_") }));
  }
  text(s, d.takeaway, { x: 0.6, y: 6.0, w: 12.1, h: 0.5, fontSize: 16, color: K.text, valign: "middle" });
};

R.optim = (s, d) => {
  frame(s, d);
  const o = d.opt;
  if (!o) { pending(s, 0.6, 1.55, 12.1, 4.3, "Minimum-LCOH optimum and its Aspen re-solve", "results/optimisation/single_objective.json, aspen_verification.json"); return; }
  const X = 0.6, Y = 1.55, W = 5.3, Hh = 4.25;
  box(s, X, Y, W, Hh, K.surface);
  text(s, "Minimum-LCOH design point", { x: X + 0.25, y: Y + 0.18, w: W - 0.5 - pillW("PYTHON"), h: 0.4, fontSize: 18, bold: true, color: K.accent });
  pillR(s, X + W - 0.2, Y + 0.26, "PYTHON");
  o.rows.forEach(([lab, v], i) => {
    const cx = X + 0.25 + (i % 2) * 2.5, cy = Y + 0.8 + Math.floor(i / 2) * 0.95;
    text(s, v, { x: cx, y: cy, w: 2.35, h: 0.45, fontSize: 22, bold: true, fontFace: FONT_SB, color: K.text, valign: "middle", objectName: nm("num_") });
    text(s, lab, { x: cx, y: cy + 0.45, w: 2.35, h: 0.3, fontSize: 12, color: K.text2 });
  });
  text(s, o.lcoh, { x: X + 0.25, y: Y + 2.8, w: W - 0.5, h: 0.45, fontSize: 20, bold: true, fontFace: FONT_SB, color: K.nh3, valign: "middle", objectName: nm("num_") });
  text(s, o.lcoh_l, { x: X + 0.25, y: Y + 3.27, w: W - 0.5, h: 0.3, fontSize: 12, color: K.text2 });
  if (o.lcoh_aspen) {
    text(s, [{ text: "Re-solved in Aspen:  ", options: { color: K.text2 } }, { text: o.lcoh_aspen, options: { bold: true, color: K.text } }],
      { x: X + 0.25, y: Y + 3.55, w: W - 0.5, h: 0.32, fontSize: 14, valign: "middle" });
    pill(s, X + 0.25, Y + 3.9, "ASPY");
  }
  const CX = 6.15, CW = 6.55;
  pill(s, CX + 0.1, 1.5, "ASPY");
  text(s, `Bar axis ends at the ${o.tol}% pass limit`, { x: CX + 0.2 + pillW("ASPY"), y: 1.49, w: CW - 0.3 - pillW("ASPY"), h: 0.26, fontSize: 12, color: K.text2, valign: "middle" });
  if (o.bars && o.bars.length) {
    s.addChart(pres.charts.BAR, [{ name: "max primary-metric deviation (%)", labels: o.bars.map((b) => b[0]), values: o.bars.map((b) => b[1]) }], chartBase({
      x: CX, y: 1.8, w: CW, h: 3.5, barDir: "bar", chartColors: [K.cold], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0.00"%"',
      title: "Aspen vs Python: largest primary-metric gap per design (%)", valAxisMinVal: 0, valAxisMaxVal: o.tol || 2,
      valAxisHidden: true, valGridLine: { style: "none" }, catAxisOrientation: "maxMin", barGapWidthPct: 35, catAxisLabelFontSize: 12, objectName: nm("chart_") }));
  } else pending(s, CX, 1.8, CW, 3.5, "Aspen re-solve of the candidates", "results/optimisation/aspen_verification.json");
  if (o.aspen) text(s, o.aspen, { x: CX, y: 5.32, w: CW, h: 0.5, fontSize: 15, bold: true, color: K.text, valign: "middle" });
  box(s, 0.6, 5.97, 12.1, 0.55, K.surface);
  text(s, o.honest, { x: 0.85, y: 5.97, w: 11.7, h: 0.55, fontSize: 13, italic: true, color: K.warn, valign: "middle" });
};

// number card with an optional detail line: number, caption, detail, pill at the bottom
function numCardR(s, x, y, w, h, c) {
  box(s, x, y, w, h, K.surface);
  text(s, c.v, { x: x + 0.2, y: y + 0.12, w: w - 0.4, h: 0.55, fontSize: c.fs || 26, bold: true, fontFace: FONT_SB, color: col(c.c || "text"), valign: "middle", objectName: nm("num_") });
  text(s, c.l, { x: x + 0.2, y: y + 0.7, w: w - 0.4, h: 0.3, fontSize: 13, color: K.text2 });
  if (c.d) text(s, c.d, { x: x + 0.2, y: y + 1.02, w: w - 0.4, h: h - 1.42, fontSize: 12, color: K.text });
  if (c.tag) pill(s, x + 0.2, y + h - 0.34, c.tag);
}

R.economics = (s, d) => {
  frame(s, d);
  const e = d.eco;
  if (!e) { pending(s, 0.6, 1.55, 8.1, 4.4, "AmCraX LCOH and price sensitivity", "results/simulations/economics_baseline.json"); }
  else {
    const bd = e.bd || {};
    const f2 = (v) => (v === undefined ? "" : v.toFixed(2));
    numCardR(s, 0.6, 1.55, 3.7, 2.1, { v: `${e.lcoh} USD/kg`, l: `LCOH at ${Math.round(e.price)} USD/t NH3`, tag: "ASPY", c: "accent",
      d: `feed ${f2(bd.ammonia_feed)} · CAPEX ${f2(bd.capex)} · heat ${f2(bd.imported_heat)} · fixed OPEX ${f2(bd.fixed_opex)}` });
    if (e.feed_share) numCardR(s, 0.6, 3.8, 3.7, 2.15, { v: e.feed_share, l: "of the LCOH is the ammonia feed", tag: "ASPY", c: "nh3",
      d: e.nh3_kg ? `${e.nh3_kg} kg NH3/kg H2 (stoichiometric floor ${e.nh3_floor})` : "" });
    if (e.curve) {
      const lab = e.curve.map((p) => String(Math.round(p[0])));
      s.addChart(pres.charts.LINE, [{ name: "LCOH (USD/kg H2)", labels: lab, values: e.curve.map((p) => +p[1].toFixed(3)) }], chartBase({
        x: 4.5, y: 1.45, w: 4.25, h: 3.75, chartColors: [K.accent], lineSize: 3, lineDataSymbol: "none",
        title: "LCOH (USD/kg) vs ammonia price", showCatAxisTitle: true, catAxisTitle: "Ammonia price (USD/t)", catAxisTitleColor: K.text2, catAxisTitleFontSize: 12,
        catAxisLabelFrequency: 8, valAxisMinVal: 0, valAxisLabelFormatCode: "0", objectName: nm("chart_") }));
    }
    const cap = [];
    if (e.slope) cap.push({ text: `${e.slope} per 100 USD/t NH3`, options: { bold: true, color: K.text, breakLine: true } });
    if (e.range) cap.push({ text: `${e.range}`, options: { color: K.text2 } });
    if (cap.length) text(s, cap, { x: 4.5, y: 5.25, w: 4.25, h: 0.7, fontSize: 12 });
  }
  // literature context, explicitly separated
  const X = 8.95, W = 3.75;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X, y: 1.55, w: W, h: 2.6, rectRadius: 0.08, fill: { color: K.surface }, line: { color: K.ok, width: 1, dashType: "dash" }, objectName: nm("card_") });
  pill(s, X + 0.2, 1.72, "LIT");
  text(s, "Context, not an AmCraX result", { x: X + 0.2, y: 2.03, w: W - 0.4, h: 0.32, fontSize: 13, bold: true, color: K.ok });
  if (e && e.lit) {
    text(s, `${e.lit.v} USD/kg`, { x: X + 0.2, y: 2.38, w: W - 0.4, h: 0.55, fontSize: 26, bold: true, fontFace: FONT_SB, color: K.text, valign: "middle", objectName: nm("num_") });
    text(s, `published LCOH at ${e.lit.p} USD/t NH3`, { x: X + 0.2, y: 2.95, w: W - 0.4, h: 0.32, fontSize: 13, color: K.text2 });
    text(s, e.lit.cites.join("; "), { x: X + 0.2, y: 3.3, w: W - 0.4, h: 0.7, fontSize: 11, color: K.muted, objectName: nm("cap_") });
  }
  box(s, X, 4.3, W, 1.65, K.surface);
  if (d.env) {
    pill(s, X + 0.2, 4.45, "ASPY");
    text(s, d.env, { x: X + 0.2, y: 4.75, w: W - 0.4, h: 0.4, fontSize: 17, bold: true, color: K.text, objectName: nm("num_") });
    text(s, d.env_label, { x: X + 0.2, y: 5.17, w: W - 0.4, h: 0.7, fontSize: 12, color: K.text2 });
  }
  text(s, "Preliminary order-of-magnitude estimate; excludes NOx treatment, NH3 polishing, compression and installed-cost factors.", { x: 0.6, y: 6.08, w: 12.1, h: 0.45, fontSize: 14, color: K.text2, valign: "middle" });
};

R.economics_old = (s, d) => {
  frame(s, d);
  const e = d.eco;
  if (e) {
    const cards = [{ v: `${e.lcoh} ${e.unit}`, l: "levelised cost of hydrogen, baseline", tag: "ASPY", c: "accent" }];
    if (e.feed_share) cards.push({ v: e.feed_share, l: "of the LCOH is the ammonia feed", tag: "ASPY", c: "nh3" });
    (e.extras || []).forEach(([lab, v, tag]) => cards.push({ v, l: lab, tag, c: "text" }));
    cards.slice(0, 3).forEach((c, i) => numCard(s, 0.6, 1.6 + i * 1.47, 3.7, 1.35, c));
    if (e.breakdown) {
      s.addChart(pres.charts.BAR, [{ name: e.unit, labels: e.breakdown.map((b) => b[0]), values: e.breakdown.map((b) => +b[1].toFixed(3)) }], chartBase({
        x: 4.55, y: 1.55, w: 4.0, h: 4.4, barDir: "bar", chartColors: [K.accent], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00",
        title: `LCOH breakdown (${e.unit})`, valAxisHidden: true, valGridLine: { style: "none" }, catAxisOrientation: "maxMin", objectName: nm("chart_") }));
    } else if (d.tornado) image(s, d.tornado, 4.55, 1.55, 4.0, 4.4, "lcoh_figure");
    else pending(s, 4.55, 1.55, 4.0, 4.4, "LCOH breakdown / tornado", "results/figures/lcoh_*.png");
  } else {
    pending(s, 0.6, 1.6, 7.95, 4.35, "AmCraX LCOH, cost breakdown and tornado", "results/simulations/economics_baseline.json, results/figures/lcoh_*.png");
  }
  // literature context, explicitly separated
  const X = 8.8, W = 3.9;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X, y: 1.6, w: W, h: 2.9, rectRadius: 0.08, fill: { color: K.surface }, line: { color: K.ok, width: 1, dashType: "dash" }, objectName: nm("card_") });
  pill(s, X + 0.2, 1.8, "LIT");
  text(s, "Context, not an AmCraX result", { x: X + 0.2, y: 2.15, w: W - 0.4, h: 0.35, fontSize: 13, bold: true, color: K.ok });
  text(s, d.lit.v, { x: X + 0.2, y: 2.55, w: W - 0.4, h: 0.6, fontSize: 26, bold: true, fontFace: FONT_SB, color: K.text, objectName: nm("num_") });
  text(s, d.lit.l, { x: X + 0.2, y: 3.2, w: W - 0.4, h: 0.6, fontSize: 13, color: K.text2 });
  text(s, d.lit.cite, { x: X + 0.2, y: 3.95, w: W - 0.4, h: 0.4, fontSize: 11, color: K.muted, objectName: nm("cap_") });
  box(s, X, 4.65, W, 1.3, K.surface);
  if (d.env) {
    pill(s, X + 0.2, 4.8, "ASPY");
    text(s, d.env, { x: X + 0.2, y: 5.08, w: W - 0.4, h: 0.4, fontSize: 18, bold: true, color: K.text, objectName: nm("num_") });
    text(s, d.env_label, { x: X + 0.2, y: 5.47, w: W - 0.4, h: 0.45, fontSize: 12, color: K.text2 });
  } else {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X, y: 4.65, w: W, h: 1.3, rectRadius: 0.08, fill: { color: K.surface }, line: { color: K.accent, width: 1.25, dashType: "dash" }, objectName: nm("pending_") });
    text(s, [{ text: "RESULT PENDING", options: { bold: true, color: K.accent, breakLine: true, fontSize: 15 } }, { text: "carbon intensity (environmental_baseline.json)", options: { color: K.text2, fontSize: 12 } }],
      { x: X + 0.2, y: 4.65, w: W - 0.4, h: 1.3, valign: "middle" });
    log("pending marker on slide: carbon intensity");
  }
  text(s, "Costs are a preliminary estimate: inputs are cited or labelled assumptions; feed price dominates in the literature.", { x: 0.6, y: 6.1, w: 12.1, h: 0.45, fontSize: 14, color: K.text2 });
};

R.different = (s, d) => {
  frame(s, d);
  const cw = 3.94, gap = (12.1 - 3 * cw) / 2;
  text(s, "Users", { x: 0.6, y: 1.48, w: 6, h: 0.3, fontSize: 14, bold: true, color: K.primary });
  d.users.forEach(([h, c], i) => chip(s, 0.6 + i * (cw + gap), 1.85, cw, 0.75, h, c));
  text(s, "What is different", { x: 0.6, y: 2.92, w: 6, h: 0.3, fontSize: 14, bold: true, color: K.primary });
  d.cards.forEach(([h, b, tag], i) => {
    const x = 0.6 + i * (cw + gap);
    box(s, x, 3.26, cw, 1.2, K.surface);
    pill(s, x + 0.2, 3.38, tag);
    text(s, h, { x: x + 0.2, y: 3.66, w: cw - 0.4, h: 0.35, fontSize: 16, bold: true, color: K.text });
    text(s, b, { x: x + 0.2, y: 4.02, w: cw - 0.4, h: 0.38, fontSize: 13, color: K.text2 });
  });
  if (d.failures) text(s, d.failures, { x: 0.6, y: 4.55, w: 12.1, h: 0.58, fontSize: 13, color: K.text, valign: "middle" });
  else if (d.proof_pending) { text(s, d.proof_pending, { x: 0.6, y: 4.55, w: 12.1, h: 0.58, fontSize: 13, color: K.accent }); log("pending marker on slide: validation matrix"); }
  box(s, 0.6, 5.22, 12.1, 1.33, K.surface);
  text(s, "What AmCraX does not claim", { x: 0.85, y: 5.3, w: 6, h: 0.38, fontSize: 16, bold: true, color: K.accent });
  const n = d.noclaim.length, w = (12.1 - 0.5 - (n - 1) * 0.1) / n;
  d.noclaim.forEach((t, i) => {
    s.addText(t, { isTextBox: true, x: 0.85 + i * (w + 0.1), y: 5.75, w, h: 0.64, shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.08, fill: { color: K.surface2 }, line: { color: K.border, width: 0.75 },
      fontFace: FONT, fontSize: 12, color: K.text, align: "center", valign: "middle", margin: 3, objectName: nm("chipf_") });
  });
};

R.different_old = (s, d) => {
  frame(s, d);
  d.cards.forEach(([h, b, tag], i) => {
    const x = 0.6 + (i % 2) * 6.15, y = 1.6 + Math.floor(i / 2) * 1.5;
    box(s, x, y, 5.95, 1.35, K.surface);
    const pw = pillR(s, x + 5.95 - 0.2, y + 0.2, tag, 1.35);
    text(s, h, { x: x + 0.25, y: y + 0.15, w: 5.95 - 0.45 - pw - 0.15, h: 0.4, fontSize: 18, bold: true, color: K.text });
    text(s, b, { x: x + 0.25, y: y + 0.6, w: 5.45, h: 0.65, fontSize: 15, color: K.text2 });
  });
  if (d.proof) text(s, [{ text: "Validation  ", options: { bold: true, color: K.ok } }, { text: d.proof, options: { color: K.text } }], { x: 0.6, y: 4.65, w: 12.1, h: 0.4, fontSize: 15 });
  else {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 4.6, w: 12.1, h: 0.45, rectRadius: 0.06, fill: { color: K.bg }, line: { color: K.accent, width: 1.25, dashType: "dash" }, objectName: nm("pending_") });
    text(s, d.proof_pending, { x: 0.8, y: 4.6, w: 11.7, h: 0.45, fontSize: 13, color: K.accent, valign: "middle" });
    log("pending marker on slide: validation matrix");
  }
  box(s, 0.6, 5.2, 12.1, 1.4, K.surface);
  text(s, "What AmCraX does not claim", { x: 0.85, y: 5.3, w: 6, h: 0.4, fontSize: 17, bold: true, color: K.accent });
  const n = d.noclaim.length, cw = (12.1 - 0.5 - (n - 1) * 0.12) / n;
  d.noclaim.forEach((t, i) => {
    s.addText(t, { isTextBox: true, x: 0.85 + i * (cw + 0.12), y: 5.8, w: cw, h: 0.6, shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.08, fill: { color: K.surface2 }, line: { color: K.border, width: 0.75 },
      fontFace: FONT, fontSize: 13, color: K.text, align: "center", valign: "middle", margin: 2, objectName: nm("chipf_") });
  });
};

R.roadmap = (s, d) => {
  frame(s, d);
  d.stages.forEach(([stage, head, items, c], i) => {
    const x = 0.6 + i * 3.07;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.6, w: 2.9, h: 4.3, rectRadius: 0.08, fill: { color: K.surface }, line: i === 0 ? { color: K.surface, width: 0 } : { color: K.border, width: 1, dashType: "dash" }, objectName: nm("card_") });
    s.addText(stage, { isTextBox: true, x: x + 0.2, y: 1.8, w: 1.15, h: 0.42, shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.21, fill: { color: col(c) }, line: { color: col(c), width: 0 }, fontFace: FONT_SB, fontSize: 14, bold: true, color: K.bg, align: "center", valign: "middle", margin: 0, objectName: nm("chipf_") });
    text(s, i === 0 ? "BUILT" : "FUTURE WORK", { x: x + 1.45, y: 1.8, w: 1.3, h: 0.42, fontSize: 10, bold: true, color: i === 0 ? K.ok : K.muted, align: "right", valign: "middle", charSpacing: 1, objectName: nm("tag_") });
    text(s, head, { x: x + 0.2, y: 2.4, w: 2.5, h: 0.5, fontSize: 20, bold: true, color: K.text });
    text(s, items.map((t, j) => ({ text: t, options: { bullet: { indent: 14 }, breakLine: j < items.length - 1 } })), { x: x + 0.2, y: 3.05, w: 2.55, h: 2.75, fontSize: 16, color: K.text2, paraSpaceAfter: 10 });
  });
  text(s, d.footer, { x: 0.6, y: 6.1, w: 12.1, h: 0.4, fontSize: 16, italic: true, color: K.text2 });
};

R.close = (s, d) => {
  frame(s, d);
  text(s, d.claim, { x: 0.6, y: 1.6, w: 6.6, h: 2.1, fontSize: 28, bold: true, fontFace: FONT_SB, color: K.text, valign: "top", lineSpacingMultiple: 1.05 });
  d.links.forEach(([lab, url], i) => {
    const y = 4.0 + i * 0.85;
    text(s, lab, { x: 0.6, y, w: 6.6, h: 0.3, fontSize: 13, bold: true, color: K.text2 });
    text(s, url || "address pending", { x: 0.6, y: y + 0.3, w: 6.6, h: 0.42, fontSize: 19, bold: true, color: K.primary, valign: "middle", objectName: nm("link_") });
  });
  const X = 7.55, W = 5.15;
  text(s, "Next steps", { x: X, y: 1.55, w: W, h: 0.4, fontSize: 18, bold: true, color: K.accent });
  d.steps.forEach(([h, b, c], i) => {
    const y = 2.05 + i * 0.98;
    box(s, X, y, W, 0.86, K.surface);
    s.addText(String(i + 1), { isTextBox: true, x: X + 0.18, y: y + 0.2, w: 0.46, h: 0.46, shape: pres.shapes.OVAL, fill: { color: col(c) }, line: { color: col(c), width: 0 },
      fontFace: FONT_SB, fontSize: 15, bold: true, color: K.bg, align: "center", valign: "middle", margin: 0, objectName: nm("tag_") });
    text(s, h, { x: X + 0.8, y: y + 0.08, w: W - 1.0, h: 0.38, fontSize: 16, bold: true, color: K.text, valign: "middle" });
    text(s, b, { x: X + 0.8, y: y + 0.45, w: W - 1.0, h: 0.34, fontSize: 13, color: K.text2, valign: "middle" });
  });
  text(s, d.footer, { x: 0.6, y: 6.08, w: 12.1, h: 0.4, fontSize: 15, italic: true, color: K.text2, valign: "middle" });
};

R.close_old = (s, d) => {
  frame(s, d);
  text(s, d.claim, { x: 0.6, y: 1.65, w: 7.5, h: 2.1, fontSize: 30, bold: true, fontFace: FONT_SB, color: K.text, valign: "top", lineSpacingMultiple: 1.05 });
  text(s, "What we are looking for", { x: 0.6, y: 4.0, w: 7.5, h: 0.4, fontSize: 17, bold: true, color: K.accent });
  leadLines(s, d.ask, { x: 0.6, y: 4.45, w: 7.5, h: 1.9, fontSize: 16, paraSpaceAfter: 8 }, "primary");
  d.proof.forEach((p, i) => {
    const y = 1.65 + i * 1.4;
    box(s, 8.6, y, 4.1, 1.25, K.surface);
    const pw = pillR(s, 8.6 + 4.1 - 0.2, y + 0.22, p.tag, 1.3);
    text(s, p.v, { x: 8.8, y: y + 0.1, w: 3.7 - pw - 0.1, h: 0.55, fontSize: 26, bold: true, fontFace: FONT_SB, color: i === 0 ? K.nh3 : K.text, valign: "middle", objectName: nm("num_") });
    text(s, p.l, { x: 8.8, y: y + 0.68, w: 3.7, h: 0.5, fontSize: 12, color: K.text2 });
  });
  const tail = [];
  if (d.tests) tail.push({ text: d.tests + " guard the code", options: { color: K.text2, breakLine: !!d.evidence } });
  if (d.evidence) tail.push({ text: d.evidence, options: { color: K.muted } });
  if (tail.length) text(s, tail, { x: 8.6, y: 5.82, w: 4.1, h: 0.82, fontSize: 11.5, paraSpaceAfter: 2 });
};

// ------------------------------------------------------------------ build
for (const d of D.slides) {
  const s = pres.addSlide({ masterName: "AMCRAX" });
  if (!R[d.id]) throw new Error(`no renderer for slide id ${d.id}`);
  R[d.id](s, d);
  log(`slide ${d.n} ${d.id} built`);
}
pres.writeFile({ fileName: outPath }).then(() => {
  log(`wrote ${outPath}`);
  fs.writeFileSync(logPath, LOG.join("\n") + "\n", "utf8");
}).catch((e) => {
  fs.writeFileSync(logPath, LOG.join("\n") + "\nERROR " + (e && e.stack || e) + "\n", "utf8");
  process.exit(1);
});
