/* ---------- scratchpad: squared paper beside the problem, for working things out by hand ---------- */
const pad = (() => {
  const canvas = h('canvas', { role: 'img', 'aria-label': 'Scratchpad for working out the answer. Draw with a finger, pen or mouse.' }), ctx = canvas.getContext('2d');
  const store = new Map();           // strokes kept per problem, so going back to a test question brings its working back
  let key = null, strokes = [], tool = 'pen', active = null, w = 0, hgt = 0, dpr = 1;
  const ink = () => getComputedStyle(document.documentElement).getPropertyValue('--ink').trim() || '#18244A';
  function style(st) {
    ctx.globalCompositeOperation = st.erase ? 'destination-out' : 'source-over';
    ctx.lineWidth = st.erase ? 24 : 2.4; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = ink();
  }
  function drawStroke(st) {
    if (!st.pts.length) return;
    style(st); ctx.beginPath(); ctx.moveTo(st.pts[0][0], st.pts[0][1]);
    for (const q of st.pts) ctx.lineTo(q[0], q[1]);
    if (st.pts.length === 1) ctx.lineTo(st.pts[0][0] + 0.1, st.pts[0][1]);       // a tap leaves a dot
    ctx.stroke();
  }
  function redraw() { ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, w, hgt); strokes.forEach(drawStroke); }
  function fit() {                    // match the canvas bitmap to its size on screen, then repaint from the strokes
    const cw = canvas.clientWidth, ch = canvas.clientHeight, ratio = window.devicePixelRatio || 1;
    if (!cw || !ch || (cw === w && ch === hgt && ratio === dpr)) return;
    w = cw; hgt = ch; dpr = ratio; canvas.width = Math.round(cw * dpr); canvas.height = Math.round(ch * dpr);
    redraw();
  }
  const at = ev => { const r = canvas.getBoundingClientRect(); return [ev.clientX - r.left, ev.clientY - r.top]; };
  canvas.addEventListener('pointerdown', ev => {
    if (ev.button) return;
    ev.preventDefault(); fit();
    try { canvas.setPointerCapture(ev.pointerId); } catch (e) {}
    active = { erase: tool === 'eraser', pts: [at(ev)] };
    strokes.push(active); drawStroke(active);
  });
  canvas.addEventListener('pointermove', ev => {
    if (!active) return;
    const a = active.pts[active.pts.length - 1], q = at(ev);
    active.pts.push(q);
    style(active); ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(q[0], q[1]); ctx.stroke();
  });
  for (const type of ['pointerup', 'pointercancel']) canvas.addEventListener(type, () => { active = null; });
  window.addEventListener('resize', fit);
  const penBtn = h('button', { class: 'btn quiet mini', type: 'button', 'aria-pressed': 'true', onclick: () => pick('pen') }, 'Pen');
  const rubBtn = h('button', { class: 'btn quiet mini', type: 'button', 'aria-pressed': 'false', onclick: () => pick('eraser') }, 'Eraser');
  function pick(t) { tool = t; penBtn.setAttribute('aria-pressed', String(t === 'pen')); rubBtn.setAttribute('aria-pressed', String(t === 'eraser')); }
  const el = h('section', { class: 'pad', 'aria-label': 'Scratchpad' },
    h('div', { class: 'pad-head' }, h('h3', null, 'Scratchpad'),
      h('div', { class: 'row' }, penBtn, rubBtn,
        h('button', { class: 'btn quiet mini', type: 'button', onclick: () => { strokes.pop(); redraw(); } }, 'Undo'),
        h('button', { class: 'btn quiet mini', type: 'button', onclick: () => { strokes.length = 0; redraw(); } }, 'Clear'))),
    canvas);
  return {
    el, fit,
    show(k) {                         // switch to the working for problem k; a new practice problem starts with a clean sheet
      if (k === key) return;
      if (typeof k === 'object') store.clear(); else if (key != null) store.set(key, strokes);
      key = k; strokes = store.get(k) || []; active = null;
      if (w) redraw();
    },
    forget() { store.clear(); key = null; strokes = []; active = null; if (w) redraw(); },
    count: () => strokes.length,
  };
})();
function withPad(key, ...nodes) {     // the problem on the left, the scratchpad on the right (below it on a phone)
  pad.show(key);
  requestAnimationFrame(pad.fit);
  return h('div', { class: 'work' }, h('div', { class: 'stack work-main' }, nodes), pad.el);
}

