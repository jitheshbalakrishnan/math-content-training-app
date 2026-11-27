/* ---------- score: his points as a climb up PuzzlePeak, this week's points and points by topic ---------- */
function climber(x, y) {             // a small hiker with a backpack, standing on the trail at (x, y)
  return sv('g', { transform: `translate(${x},${y})` },
    sv('ellipse', { cx: 0, cy: 1, rx: 10, ry: 3, fill: 'rgba(24,36,74,.25)' }),
    sv('rect', { x: -9, y: -21, width: 7, height: 11, rx: 2, fill: 'var(--pine)' }),
    sv('path', { d: 'M-4,-3 L-2,-12 M4,-3 L2,-12', stroke: 'var(--ink)', 'stroke-width': 3, 'stroke-linecap': 'round' }),
    sv('rect', { x: -4, y: -23, width: 8, height: 12, rx: 3, fill: 'var(--sun)' }),
    sv('circle', { cx: 0, cy: -28, r: 5, fill: '#F2C9A0', stroke: 'var(--ink)', 'stroke-width': 1.5 }),
    sv('path', { d: 'M-6,-30 Q0,-38 6,-30 Z', fill: 'var(--margin)' }));
}
const BADGE_ICONS = {                 // simple drawn emblems, no emoji
  flag: [['line', { x1: 26, y1: 46, x2: 26, y2: 16, stroke: 'currentColor', 'stroke-width': 4, 'stroke-linecap': 'round' }], ['polygon', { points: '26,16 44,22 26,28', fill: 'currentColor' }]],
  flame: [['path', { d: 'M32,14 C40,24 44,30 42,38 A10,10 0 0 1 22,38 C20,32 26,28 27,22 C30,26 30,28 32,30 C34,26 34,20 32,14 Z', fill: 'currentColor' }]],
  star: [['polygon', { points: '32,13 37.5,26 51,27 40.5,35.5 44,49 32,41.5 20,49 23.5,35.5 13,27 26.5,26', fill: 'currentColor' }]],
  check: [['path', { d: 'M18,33 L28,43 L46,22', fill: 'none', stroke: 'currentColor', 'stroke-width': 6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }]],
  clock: [['circle', { cx: 32, cy: 33, r: 15, fill: 'none', stroke: 'currentColor', 'stroke-width': 4 }], ['path', { d: 'M32,24 V33 L39,37', fill: 'none', stroke: 'currentColor', 'stroke-width': 4, 'stroke-linecap': 'round' }]],
  boot: [['path', { d: 'M22,16 H34 V34 L46,38 V46 H20 Z', fill: 'currentColor' }]],
};
function badgeIcon(kind, on) {
  return sv('svg', { viewBox: '0 0 64 64', 'aria-hidden': 'true' },
    sv('circle', { cx: 32, cy: 32, r: 29, fill: on ? 'var(--sun)' : 'var(--sheet)', stroke: on ? 'var(--sun-soft)' : 'var(--lock)', 'stroke-width': 4 }),
    sv('g', { style: 'color:' + (on ? 'var(--ink)' : 'var(--lock)') }, BADGE_ICONS[kind].map(([t, a]) => sv(t, a))));
}
function badges() {                  // worked out from what is already saved, so old progress counts
  const days = Object.values(S.days || {}), best = Math.max(0, ...Object.values(S.skills || {}).map(s => s.level || 0));
  const answered = days.reduce((a, d) => a + (d.n || 0), 0), run = streak(), c = climb(S.points), passed = need => (S.points || 0) >= need;
  return [
    ['boot', 'First steps', 'Answer your first problem', answered > 0],
    ['flag', 'Camp 1', 'Reach 50 points', passed(50)],
    ['flag', 'Camp 2', 'Reach 150 points', passed(150)],
    ['flag', 'Camp 3', 'Reach 300 points', passed(300)],
    ['flag', 'Summit', 'Reach 800 points', passed(800) || c.mountain > 1],
    ['flame', '3 days in a row', 'Practice 3 days running', run >= 3],
    ['flame', '7 days in a row', 'Practice a whole week running', run >= 7],
    ['check', 'Full set', "Finish a day's set", days.some(d => (d.n || 0) >= goals().day)],
    ['star', 'Level 5', 'Get any skill to level 5', best >= 5],
    ['clock', 'Test taker', 'Finish a mock test', (S.mocks || []).length > 0],
  ];
}
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
      sv('rect', { x: 0, y: 0, width: W, height: base, fill: 'var(--sky)', rx: 12 }),
      sv('circle', { cx: 520, cy: 60, r: 26, fill: 'var(--sun-soft)' }), sv('circle', { cx: 520, cy: 60, r: 18, fill: 'var(--sun)' }),
      sv('g', { fill: 'var(--sheet)' }, sv('ellipse', { cx: 110, cy: 60, rx: 34, ry: 12 }), sv('ellipse', { cx: 135, cy: 52, rx: 22, ry: 12 }), sv('ellipse', { cx: 440, cy: 110, rx: 26, ry: 9 })),
      sv('polygon', { points: `0,${base} 90,150 170,${base}`, fill: 'var(--far)' }), sv('polygon', { points: `430,${base} 530,140 600,190 600,${base}`, fill: 'var(--far)' }),
      sv('polygon', { points: `0,${base} ${peak.join(',')} 600,${base}`, fill: 'var(--near)' }),
      sv('polygon', { points: `243,72 ${peak.join(',')} 357,72 332,64 314,77 292,63 268,77`, fill: 'var(--sheet)' }),      // snow cap
      sv('rect', { x: 0, y: base, width: W, height: H - base, fill: 'var(--pine-bg)' }),
      [[28, 252], [52, 258], [548, 254], [574, 260], [592, 250]].map(([x, y]) => sv('polygon', { points: `${x},${y - 30} ${x - 11},${y} ${x + 11},${y}`, fill: 'var(--pine)' })),
      sv('polyline', { points: pts(trail), fill: 'none', stroke: 'var(--sheet)', 'stroke-width': 3, 'stroke-dasharray': '2 7', 'stroke-linecap': 'round' }),
      sv('polyline', { points: pts(trail.slice(0, seg + 1).concat([me])), fill: 'none', stroke: 'var(--ink)', 'stroke-width': 4, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }),
      CAMPS.map(([need, name], i) => {
        const [x, y] = trail[i], reached = c.here >= need, left = x < 300;
        return sv('g', null,
          sv('line', { x1: x, y1: y, x2: x, y2: y - 20, stroke: 'var(--ink)', 'stroke-width': 2 }),
          sv('polygon', { points: `${x},${y - 20} ${x + 14},${y - 15} ${x},${y - 10}`, fill: reached ? 'var(--sun)' : 'var(--sheet)', stroke: 'var(--ink)', 'stroke-width': 1.5 }),
          sv('text', { x: left ? x - 8 : x + 20, y: y - 9, 'text-anchor': left ? 'end' : 'start', 'font-size': 14, 'font-weight': reached ? 700 : 400, fill: 'var(--ink)', 'paint-order': 'stroke', stroke: 'var(--sky)', 'stroke-width': 4 }, name + (need ? ' · ' + need : '')));
      }),
      climber(me[0], me[1])),
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
          hgt ? sv('path', { d: `M${x},${base} V${y + r} Q${x},${y} ${x + r},${y} H${x + bw - r} Q${x + bw},${y} ${x + bw},${y + r} V${base} Z`, fill: d.today ? 'var(--sun)' : 'var(--pine)', stroke: d.today ? 'var(--ink)' : 'none', 'stroke-width': 2 }) : null,
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
        h('span', { class: 'small' }, c.mountain > 1 ? 'Mountain ' + c.mountain : 'PuzzlePeak')),
      h('div', { class: 'tile' }, h('span', { class: 'muted' }, 'Today'), h('span', { class: 'big' }, '+' + pointsToday()), h('span', { class: 'small' }, week + ' this week')),
      h('div', { class: 'tile' }, h('span', { class: 'muted' }, 'Days in a row'), h('span', { class: 'big' }, run), h('span', { class: 'small' }, run ? 'Keep it going tomorrow' : 'Practice today to start'))),
    h('div', { class: 'sheet' }, h('h2', null, c.camp), mountainSvg(c)),
    h('div', { class: 'sheet' }, h('h3', null, 'Badges'),
      h('div', { class: 'badges' }, badges().map(([icon, title, how, on]) =>
        h('div', { class: 'badge' + (on ? '' : ' locked'), role: 'img', 'aria-label': title + (on ? ', earned' : ', not yet: ' + how) },
          badgeIcon(icon, on), h('b', null, title), h('span', null, on ? 'Earned' : how))))),
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
