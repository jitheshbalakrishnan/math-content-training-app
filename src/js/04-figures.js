/* ---------- figures: drawn by code from data the generator supplies, so what he sees is what was checked ---------- */
const NS = 'http://www.w3.org/2000/svg';
function sv(tag, attrs, ...kids) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  for (const c of kids.flat()) if (c != null) e.append(c.nodeType ? c : document.createTextNode(String(c)));
  return e;
}
const INK = 'var(--ink)', SHADE = 'var(--shade)', SHEET = 'var(--sheet)', LINE = 'var(--line)', MUTED = 'var(--muted)';
const isNum = v => typeof v === 'number' && isFinite(v);
const isPt = a => Array.isArray(a) && a.length === 2 && a.every(v => isNum(v) && v >= 0 && v <= 20);
const str = (v, n) => String(v == null ? '' : v).slice(0, n);
const PICTURE_CHOICES = ['grid', 'shape'];

function validFigure(f, allowed) {
  if (!f || typeof f !== 'object' || !allowed.includes(f.type)) return null;
  if (f.type === 'grid') {
    const rows = f.rows;
    if (!Array.isArray(rows) || rows.length < 1 || rows.length > 10) return null;
    if (rows.some(r => typeof r !== 'string' || r.length < 1 || r.length > 10 || r.length !== rows[0].length)) return null;
    return { type: 'grid', rows };
  }
  if (f.type === 'shape') {
    if (!Array.isArray(f.shapes) || f.shapes.length < 1 || f.shapes.length > 4) return null;
    const shapes = [];
    for (const sh of f.shapes) {
      if (!sh || !Array.isArray(sh.points) || sh.points.length < 3 || sh.points.length > 12 || !sh.points.every(isPt)) return null;
      shapes.push({ points: sh.points, sides: sh.points.map((_, i) => str(Array.isArray(sh.sides) ? sh.sides[i] : '', 12)), shaded: !!sh.shaded });
    }
    const marks = Array.isArray(f.marks) ? f.marks.slice(0, 10) : [];
    if (marks.some(m => !m || !isPt(m.at))) return null;
    return { type: 'shape', shapes, marks: marks.map(m => ({ at: m.at, label: str(m.label, 3) })), show_grid: !!f.show_grid, axes: !!f.axes };
  }
  if (f.type === 'bars') {
    if (!Array.isArray(f.labels) || !Array.isArray(f.values) || f.labels.length < 2 || f.labels.length > 8 || f.values.length !== f.labels.length) return null;
    if (f.values.some(v => !isNum(v) || v < 0 || v > 1000)) return null;
    return { type: 'bars', title: str(f.title, 60), labels: f.labels.map(l => str(l, 10)), values: f.values };
  }
  if (f.type === 'table') {
    const head = f.header, rows = f.rows;
    if (!Array.isArray(head) || head.length < 1 || head.length > 6 || !Array.isArray(rows) || rows.length < 1 || rows.length > 8) return null;
    if (rows.some(r => !Array.isArray(r) || r.length !== head.length)) return null;
    return { type: 'table', header: head.map(c => str(c, 24)), rows: rows.map(r => r.map(c => str(c, 24))) };
  }
  if (f.type === 'clock') {
    if (!Number.isInteger(f.hour) || !Number.isInteger(f.minute) || f.hour < 0 || f.hour > 23 || f.minute < 0 || f.minute > 59) return null;
    return { type: 'clock', hour: f.hour, minute: f.minute };
  }
  return null;
}
function figText(f) {                // the same figure as text, for the answer check and the tutor
  if (f.type === 'grid') return 'a grid of ' + f.rows.length + ' rows by ' + f.rows[0].length + ' columns. Rows from the top, where "#" is a shaded cell, "." is an empty cell and any other character is written in that cell: ' + f.rows.join(' / ');
  if (f.type === 'bars') return 'a bar chart' + (f.title ? ' titled "' + f.title + '"' : '') + ': ' + f.labels.map((l, i) => l + ' = ' + f.values[i]).join(', ');
  if (f.type === 'table') return 'a table. ' + [f.header].concat(f.rows).map(r => r.join(' | ')).join(' / ');
  if (f.type === 'clock') return 'an analog clock showing ' + (f.hour % 12 || 12) + ':' + String(f.minute).padStart(2, '0');
  return 'a drawing on a coordinate plane with y going up, given as data: ' + JSON.stringify({ shapes: f.shapes, marks: f.marks });
}
function label(x, y, text, size, fill, anchor) {
  return sv('text', { x, y, 'font-size': size, fill: fill || INK, 'text-anchor': anchor || 'middle', 'dominant-baseline': 'central' }, text);
}
function drawGrid(f, small) {
  const R = f.rows.length, C = f.rows[0].length, u = 10;
  const svg = sv('svg', { viewBox: '-0.5 -0.5 ' + (C * u + 1) + ' ' + (R * u + 1) });
  f.rows.forEach((row, r) => [...row].forEach((ch, c) => {
    svg.append(sv('rect', { x: c * u, y: r * u, width: u, height: u, fill: ch === '#' ? SHADE : SHEET, stroke: INK, 'stroke-width': 0.6 }));
    if (ch !== '#' && ch !== '.' && ch !== ' ') svg.append(label(c * u + 5, r * u + 5.3, ch, 6));
  }));
  return [svg, Math.min(C * (small ? 18 : 34), small ? 150 : 340)];
}
function drawShape(f, small) {
  const all = f.shapes.flatMap(sh => sh.points).concat(f.marks.map(m => m.at));
  const lined = f.show_grid || f.axes;
  let x0 = Math.min(...all.map(p => p[0])), x1 = Math.max(...all.map(p => p[0])), y0 = Math.min(...all.map(p => p[1])), y1 = Math.max(...all.map(p => p[1]));
  if (f.axes) { x0 = 0; y0 = 0; }
  if (lined) { x0 = Math.floor(x0); y0 = Math.floor(y0); x1 = Math.ceil(x1); y1 = Math.ceil(y1); }
  if (x1 - x0 < 1) x1 = x0 + 1;
  if (y1 - y0 < 1) y1 = y0 + 1;
  const u = 10, pad = 14, X = x => (x - x0) * u, Y = y => (y1 - y) * u, W = (x1 - x0) * u, H = (y1 - y0) * u;
  const svg = sv('svg', { viewBox: -pad + ' ' + -pad + ' ' + (W + 2 * pad) + ' ' + (H + 2 * pad) });
  if (lined) {
    for (let x = x0; x <= x1; x++) svg.append(sv('line', { x1: X(x), y1: 0, x2: X(x), y2: H, stroke: f.axes && x === 0 ? INK : LINE, 'stroke-width': f.axes && x === 0 ? 0.8 : 0.4 }));
    for (let y = y0; y <= y1; y++) svg.append(sv('line', { x1: 0, y1: Y(y), x2: W, y2: Y(y), stroke: f.axes && y === 0 ? INK : LINE, 'stroke-width': f.axes && y === 0 ? 0.8 : 0.4 }));
  }
  if (f.axes) {
    for (let x = x0; x <= x1; x++) svg.append(label(X(x), H + 6, x, 4, MUTED));
    for (let y = y0 + 1; y <= y1; y++) svg.append(label(-5, Y(y), y, 4, MUTED));
  }
  for (const sh of f.shapes) {
    svg.append(sv('polygon', { points: sh.points.map(p => X(p[0]) + ',' + Y(p[1])).join(' '), fill: sh.shaded ? SHADE : 'none', stroke: INK, 'stroke-width': 1, 'stroke-linejoin': 'round' }));
    const cx = sh.points.reduce((a, p) => a + X(p[0]), 0) / sh.points.length, cy = sh.points.reduce((a, p) => a + Y(p[1]), 0) / sh.points.length;
    sh.points.forEach((a, i) => {
      if (!sh.sides[i]) return;
      const b = sh.points[(i + 1) % sh.points.length];
      const mx = (X(a[0]) + X(b[0])) / 2, my = (Y(a[1]) + Y(b[1])) / 2;
      let nx = -(Y(b[1]) - Y(a[1])), ny = X(b[0]) - X(a[0]);
      const len = Math.hypot(nx, ny) || 1; nx /= len; ny /= len;
      if ((mx + nx - cx) ** 2 + (my + ny - cy) ** 2 < (mx - nx - cx) ** 2 + (my - ny - cy) ** 2) { nx = -nx; ny = -ny; }   // push the label away from the middle of the shape
      svg.append(label(mx + nx * 6.5, my + ny * 5, sh.sides[i], 4.6));
    });
  }
  for (const m of f.marks) {
    svg.append(sv('circle', { cx: X(m.at[0]), cy: Y(m.at[1]), r: 1.3, fill: INK }));
    if (m.label) svg.append(label(X(m.at[0]) + 4, Y(m.at[1]) - 4, m.label, 5));
  }
  const px = Math.max(150, Math.min(380, (W + 2 * pad) * 2.6));
  return [svg, small ? px / 2.3 : px];
}
function drawBars(f, small) {
  const n = f.values.length, W = 120, H = 70, ox = 16, oy = 6, max = Math.max(1, ...f.values);
  const step = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500].find(st => max / st <= 6) || 500, top = Math.ceil(max / step) * step;
  const svg = sv('svg', { viewBox: '0 0 ' + (W + ox + 6) + ' ' + (H + oy + 14) });
  for (let v = 0; v <= top; v += step) {
    const y = oy + H - (v / top) * H;
    svg.append(sv('line', { x1: ox, y1: y, x2: ox + W, y2: y, stroke: v ? LINE : INK, 'stroke-width': v ? 0.4 : 0.8 }));
    svg.append(label(ox - 3, y, v, 4, MUTED, 'end'));
  }
  const slot = W / n, bw = slot * 0.6;
  f.values.forEach((v, i) => {
    const bh = (v / top) * H, x = ox + i * slot + (slot - bw) / 2;
    svg.append(sv('rect', { x, y: oy + H - bh, width: bw, height: bh, fill: SHADE, stroke: INK, 'stroke-width': 0.6 }));
    svg.append(label(x + bw / 2, oy + H + 6, f.labels[i], 4));
  });
  return [svg, small ? 180 : 400];
}
function drawClock(f, small) {
  const svg = sv('svg', { viewBox: '-52 -52 104 104' });
  svg.append(sv('circle', { cx: 0, cy: 0, r: 48, fill: SHEET, stroke: INK, 'stroke-width': 2 }));
  for (let k = 1; k <= 12; k++) { const a = k * Math.PI / 6; svg.append(label(39 * Math.sin(a), -39 * Math.cos(a) + 0.5, k, 8)); }
  const hand = (deg, len, w) => { const a = deg * Math.PI / 180; return sv('line', { x1: 0, y1: 0, x2: len * Math.sin(a), y2: -len * Math.cos(a), stroke: INK, 'stroke-width': w, 'stroke-linecap': 'round' }); };
  svg.append(hand((f.hour % 12 + f.minute / 60) * 30, 23, 3.2), hand(f.minute * 6, 33, 1.8), sv('circle', { cx: 0, cy: 0, r: 2.2, fill: INK }));
  return [svg, small ? 90 : 170];
}
function figureEl(f, small) {
  const wrap = h('div', { class: 'figure' });
  if (f.type === 'table') {
    wrap.append(h('table', null, h('thead', null, h('tr', null, f.header.map(c => h('th', { scope: 'col' }, c)))), h('tbody', null, f.rows.map(r => h('tr', null, r.map(c => h('td', null, c)))))));
    return wrap;
  }
  const [svg, px] = (f.type === 'grid' ? drawGrid : f.type === 'bars' ? drawBars : f.type === 'clock' ? drawClock : drawShape)(f, small);
  svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', 'Figure: ' + figText(f)); svg.setAttribute('width', Math.round(px));
  wrap.append(svg);
  if (f.type === 'bars' && f.title) wrap.append(h('div', { class: 'muted small' }, f.title));
  return wrap;
}
const FIG_FORMAT = {
  grid: 'grid: {"type":"grid","rows":["#..","...",".#."]}. Equal-length strings, one per row from the top, at most 10 by 10. "#" is a shaded cell, "." an empty cell, and any other single character is written in that cell.',
  shape: 'shape: {"type":"shape","shapes":[{"points":[[0,0],[6,0],[6,4],[0,4]],"sides":["6 cm","","",""],"shaded":false}],"marks":[{"at":[2,3],"label":"A"}],"show_grid":false,"axes":false}. Up to 4 shapes. "points" are the corners in order, in units from 0 to 20 with y going up. "sides"[i] labels the side from corner i to the next corner, "" for no label. The drawing uses your coordinates, so keep them in proportion to the labeled lengths. "marks" are labeled points. "show_grid" draws unit squares, and "axes" adds numbered axes from 0.',
  bars: 'bars: {"type":"bars","title":"Books read each day","labels":["Mon","Tue","Wed"],"values":[3,5,2]}. 2 to 8 bars, values from 0 to 1000 that can be read off the gridlines.',
  table: 'table: {"type":"table","header":["Day","Cups sold"],"rows":[["Mon","4"],["Tue","7"]]}. At most 6 columns and 8 rows.',
  clock: 'clock: {"type":"clock","hour":3,"minute":40}. An analog clock face.',
};
function figurePrompt(sk, n) {
  const pics = sk.figures.filter(t => PICTURE_CHOICES.includes(t));
  return [
    '- This skill is visual. Include a figure whenever it makes the problem more natural, which is most of the time. The student sees the figure drawn by code from your data, so the data must be exact and complete.',
    '- Allowed figure types and their formats:',
    ...sk.figures.map(t => '  ' + FIG_FORMAT[t]),
    '- Put the figure in "figure" and call it "the figure" in the question. Do not repeat in words what the figure shows, and never let the figure state the answer.',
    pics.length ? '- If the answer choices are pictures, put ' + n + ' ' + pics.join(' or ') + ' figures in "choice_figures" and set "choices" to ' + JSON.stringify([...LETTERS.slice(0, n)].map(l => 'Figure ' + l)) + '. Otherwise set "choice_figures" to null.' : '- Set "choice_figures" to null.',
    '- If the problem needs no picture, set "figure" to null and make it solvable from the text alone.',
  ].join('\n');
}

