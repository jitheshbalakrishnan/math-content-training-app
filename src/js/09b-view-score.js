/* ---------- score: his points as a climb up Puzzle Peak, this week's points and points by topic ---------- */
function mountainSvg(c) {            // a mountain with a zig-zag trail; a flag at each camp; him between camps by points
  const W = 600, H = 280, base = 250, peak = [300, 30];
  const trail = [[120, 248], [470, 205], [160, 160], [395, 115], [255, 72], [300, 36]];   // one bend per camp, inside the slopes
  let seg = 0;
  for (let i = 0; i < CAMPS.length - 1; i++) if (c.here >= CAMPS[i][0]) seg = i;
  const f = (c.here - CAMPS[seg][0]) / (CAMPS[seg + 1][0] - CAMPS[seg][0]);
  const me = [trail[seg][0] + (trail[seg + 1][0] - trail[seg][0]) * f, trail[seg][1] + (trail[seg + 1][1] - trail[seg][1]) * f];
  const pts = a => a.map(p => p.join(',')).join(' ');
  return h('figure', { class: 'climb' },
    sv('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Mountain ' + c.mountain + ': at ' + c.camp + (c.next ? ', ' + c.toNext + ' points to ' + c.next : '') },
      sv('polygon', { points: `0,${base} ${peak.join(',')} 600,${base}`, fill: 'var(--grid)' }),
      sv('polygon', { points: `243,72 ${peak.join(',')} 357,72 332,64 314,77 292,63 268,77`, fill: 'var(--sheet)' }),      // snow cap
      sv('line', { x1: 0, y1: base, x2: W, y2: base, stroke: 'var(--line)', 'stroke-width': 2 }),
      sv('polyline', { points: pts(trail), fill: 'none', stroke: 'var(--shade)', 'stroke-width': 3, 'stroke-dasharray': '2 7', 'stroke-linecap': 'round' }),
      sv('polyline', { points: pts(trail.slice(0, seg + 1).concat([me])), fill: 'none', stroke: 'var(--ink)', 'stroke-width': 4, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }),
      CAMPS.map(([need, name], i) => {
        const [x, y] = trail[i], reached = c.here >= need, left = x < 300;
        return sv('g', null,
          sv('line', { x1: x, y1: y, x2: x, y2: y - 20, stroke: 'var(--ink)', 'stroke-width': 2 }),
          sv('polygon', { points: `${x},${y - 20} ${x + 14},${y - 15} ${x},${y - 10}`, fill: reached ? 'var(--margin)' : 'var(--sheet)', stroke: 'var(--ink)', 'stroke-width': 1.5 }),
          sv('text', { x: left ? x - 8 : x + 20, y: y - 9, 'text-anchor': left ? 'end' : 'start', 'font-size': 14, 'font-weight': reached ? 700 : 400, fill: reached ? 'var(--ink)' : 'var(--muted)' }, name + (need ? ' · ' + need : '')));
      }),
      sv('circle', { cx: me[0], cy: me[1], r: 10, fill: 'var(--hl)', stroke: 'var(--ink)', 'stroke-width': 3 })),
    h('figcaption', null, c.next ? h('span', null, h('b', null, c.toNext), ' more ' + (c.toNext === 1 ? 'point' : 'points') + ' to ' + c.next + '.') : 'You reached the summit!'));
}
function weekBars(days) {            // points each day this week; today is highlighted, the others share one color
  const W = 420, H = 170, top = 18, base = 140, max = Math.max(10, ...days.map(d => d.pts));
  const slot = W / 7, bw = Math.min(34, slot - 14);
  return h('figure', { class: 'weekpts' },
    sv('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Points this week: ' + days.map(d => d.letter + ' ' + d.pts).join(', ') },
      sv('line', { x1: 0, y1: base, x2: W, y2: base, stroke: 'var(--line)', 'stroke-width': 1 }),
      days.map((d, i) => {
        const hgt = d.pts ? Math.max(4, (base - top) * d.pts / max) : 0, x = i * slot + (slot - bw) / 2, y = base - hgt, r = Math.min(4, hgt);
        return sv('g', null,
          sv('title', null, d.letter + ': ' + d.pts + (d.pts === 1 ? ' point' : ' points')),
          sv('rect', { x: i * slot, y: top, width: slot, height: base - top, fill: 'transparent' }),           // a bigger target for hovering
          hgt ? sv('path', { d: `M${x},${base} V${y + r} Q${x},${y} ${x + r},${y} H${x + bw - r} Q${x + bw},${y} ${x + bw},${y + r} V${base} Z`, fill: d.today ? 'var(--hl)' : 'var(--ink)', stroke: d.today ? 'var(--ink)' : 'none', 'stroke-width': 2 }) : null,
          d.today || d.pts === max ? sv('text', { x: x + bw / 2, y: y - 6, 'text-anchor': 'middle', 'font-size': 13, 'font-weight': 700, fill: 'var(--ink)' }, d.pts) : null,
          sv('text', { x: x + bw / 2, y: base + 20, 'text-anchor': 'middle', 'font-size': 13, 'font-weight': d.today ? 700 : 400, fill: d.today ? 'var(--ink)' : 'var(--muted)' }, d.letter));
      })));
}
function viewScore() {
  if (!env.ready) return [h('div', { class: 'sheet' }, busyLine('Loading your score'))];
  const c = climb(S.points), name = childName(), run = streak();
  const days = thisWeek().map(d => ({ ...d, pts: (S.days && S.days[d.key] && S.days[d.key].pts) || 0 }));
  const week = days.reduce((a, d) => a + d.pts, 0);
  const topics = TOPICS.map(t => ({ name: t.name, pts: (S.topicPts && S.topicPts[t.id]) || 0 })).filter(t => t.pts > 0).sort((a, b) => b.pts - a.pts);
  const most = topics.length ? topics[0].pts : 1;
  return [
    h('div', { class: 'tiles' },
      h('div', { class: 'tile dark' }, h('span', { class: 'muted' }, name ? name + "'s points" : 'Your points'), h('span', { class: 'big' }, S.points || 0),
        h('span', { class: 'small' }, c.mountain > 1 ? 'Mountain ' + c.mountain : 'Puzzle Peak')),
      h('div', { class: 'tile' }, h('span', { class: 'muted' }, 'Today'), h('span', { class: 'big' }, '+' + pointsToday()), h('span', { class: 'small' }, week + ' this week')),
      h('div', { class: 'tile' }, h('span', { class: 'muted' }, 'Days in a row'), h('span', { class: 'big' }, run), h('span', { class: 'small' }, run ? 'Keep it going tomorrow' : 'Practice today to start'))),
    h('div', { class: 'sheet' }, h('h2', null, c.camp), mountainSvg(c)),
    h('div', { class: 'sheet' }, h('h3', null, 'Points this week'), weekBars(days)),
    h('div', { class: 'sheet' }, h('h3', null, 'Points by topic'),
      topics.length ? h('div', { class: 'tbars' }, topics.map(t => h('div', { class: 'tbar' },
        h('span', null, t.name), h('span', { class: 'track' }, h('i', { style: 'width:' + Math.max(3, Math.round(100 * t.pts / most)) + '%' })), h('b', null, t.pts))))
        : h('p', { class: 'muted' }, 'Answer a few problems and your points show up here, topic by topic.')),
    h('div', { class: 'sheet' }, h('h3', null, 'How points work'),
      h('p', null, 'Right first time: the problem\'s level in points, so a level 4 problem is worth 4. Right on a second try: 1 point. A guess earns no points, even when it is right.'),
      h('p', { class: 'muted small' }, 'Points never change your levels. Mock test questions earn points the same way.')),
  ];
}
