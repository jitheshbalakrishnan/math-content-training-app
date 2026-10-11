/* ---------- celebrations: a short moment for a right answer, a level-up and finishing the day's set ---------- */
function burst() {                   // a ring of paper squares flying out; decoration only, hidden from screen readers
  const colors = ['--hl', '--good', '--ink', '--margin'];
  return h('span', { class: 'burst', 'aria-hidden': 'true' }, Array.from({ length: 14 }, (_, i) => {
    const angle = (i / 14) * Math.PI * 2, reach = 44 + (i % 3) * 16;
    return h('i', { style: '--dx:' + Math.round(Math.cos(angle) * reach) + 'px;--dy:' + Math.round(Math.sin(angle) * reach) + 'px;--c:var(' + colors[i % 4] + ')' });
  }));
}
