/* ---------- progress: a training log of what he has done and where each skill stands ---------- */
let confirmReset = false;
function viewProgress() {
  const out = viewProgressBody();
  if (env.ready && S.mocks && S.mocks.length) out.splice(out.length > 1 ? out.length - 1 : 1, 0, mockHistory());   // above the Start over row
  return out;
}
function bestMock() {                // the mock test with the highest share of its points
  return (S.mocks || []).reduce((best, m) => (!best || m.score / m.max > best.score / best.max ? m : best), null);
}
function logTiles() {
  const g = goals(), days = thisWeek(), week = days.reduce((a, d) => a + d.n, 0), run = streak(), best = bestMock();
  return h('div', { class: 'tiles' },
    h('div', { class: 'tile dark' },
      h('span', { class: 'muted' }, 'Best mock test'),
      best ? h('span', { class: 'big' }, best.score, h('small', null, ' of ' + units(best.max, best.unit || 'point')))
        : h('span', { class: 'big' }, h('small', null, 'None yet')),
      best ? h('span', { class: 'muted small' }, best.correct + ' of ' + best.n + ' right, ' + new Date(best.at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }))
        : h('a', { class: 'small', href: '#mock' }, 'Take a timed mock test')),
    h('div', { class: 'tile' },
      h('span', { class: 'muted' }, 'This week'),
      h('span', { class: 'big' }, week, h('small', null, ' of ' + g.week + ' problems')),
      h('span', { class: 'meter', role: 'img', 'aria-label': week + ' of ' + g.week + ' problems this week' }, h('i', { style: 'width:' + Math.min(100, Math.round(100 * week / g.week)) + '%' }))),
    h('div', { class: 'tile' },
      h('span', { class: 'muted' }, 'Practice days'),
      h('span', { class: 'week', role: 'img', 'aria-label': days.filter(d => d.n).length + ' practice days this week' },
        days.map(d => h('span', null, h('i', { class: (d.n ? 'on' : '') + (d.today ? ' today' : '') }), d.letter))),
      h('span', { class: 'small' }, run >= 2 ? run + ' days in a row' : run === 1 ? 'Practice tomorrow to start a streak' : 'Practice today to start a streak')));
}
function viewProgressBody() {
  if (!env.ready) return [h('div', { class: 'sheet' }, busyLine('Loading your progress'))];
  const list = S.contest ? contestSkills() : [];
  const all = list.map(s => S.skills[s.id]).filter(Boolean);
  const n = all.reduce((a, s) => a + s.n, 0), ok = all.reduce((a, s) => a + s.ok, 0);
  const erase = () => {               // progress goes; what a parent set up stays
    const keep = { custom: S.custom || [], goals: goals(), tier: S.tier, verify: !!S.verify };
    confirmReset = false;
    S = Object.assign(newState(), keep);
    syncCustom();
    if (live) live.abort();
    if (mock && mock.ctl) mock.ctl.abort();             // a test being written or taken goes too, so it cannot refill the history
    mock = null; confirmFinish = false; pad.forget(); saveMock();
    cur = null; dropPrepared(); saveState();
    location.hash = '#home'; render();
  };
  const reset = h('div', { class: 'row' }, confirmReset
    ? [h('span', null, 'Erase all progress? Added topics and settings stay.'), h('button', { class: 'btn', type: 'button', onclick: erase }, 'Erase progress'), h('button', { class: 'btn quiet', type: 'button', onclick: () => { confirmReset = false; render(); } }, 'Keep it')]
    : h('button', { class: 'btn quiet', type: 'button', onclick: () => { confirmReset = true; render(); } }, 'Start over'));
  const some = (S.mocks && S.mocks.length) || Object.keys(S.days || {}).length;      // anything a reset would clear
  if (!n) return [logTiles(), h('div', { class: 'sheet' }, h('h2', null, 'No skills to show yet'),
    h('p', { class: 'muted' }, 'Answer a few problems and each skill appears here with its level and how many you got right.'),
    h('div', { class: 'row' }, h('a', { class: 'btn primary', href: '#home' }, 'Go to today\'s set'))), ...(some ? [reset] : [])];
  const reasons = {};
  for (const s of all) for (const k in s.reasons) reasons[k] = (reasons[k] || 0) + s.reasons[k];
  const top = Object.entries(reasons).sort((a, b) => b[1] - a[1])[0];
  const trouble = { read: "didn't understand the question", start: "didn't know how to start", slip: 'knew the method but made a mistake', guess: 'guessed' };
  const head = h('div', { class: 'sheet' },
    h('h2', null, n + (n === 1 ? ' problem' : ' problems') + ' answered, ' + Math.round(100 * ok / n) + '% right first time'),
    h('p', { class: 'muted' }, CONTESTS[S.contest] + (S.placement.done ? '' : ', still finding your level') + '. Guesses count as not right.'),
    top ? h('p', null, 'Most common trouble: ' + (trouble[top[0]] || top[0]) + ' (' + top[1] + (top[1] === 1 ? ' time' : ' times') + ').') : null);
  const weak = st => st && st.n >= 3 && st.ok / st.n < 0.5;
  const groups = TOPICS.filter(tp => list.some(s => s.topic === tp.id)).map(tp => h('div', { class: 'sheet' },
    h('h3', null, tp.name),
    h('div', null, list.filter(s => s.topic === tp.id).map(s => {
      const st = S.skills[s.id];
      return h('div', { class: 'prog-row' },
        h('span', null, s.name, weak(st) ? h('span', { class: 'tag' }, 'work on this') : null),
        st && st.n ? levelDots(st.level) : h('span', { class: 'muted small' }, 'not tried'),
        h('span', { class: 'n' }, st && st.n ? st.ok + ' of ' + st.n + ' right' : ''));
    }))));
  return [logTiles(), head, ...groups, reset];
}

