let confirmReset = false;
function viewProgress() {
  const out = viewProgressBody();
  if (env.ready && S.mocks && S.mocks.length) out.splice(out.length > 1 ? out.length - 1 : 1, 0, mockHistory());   // above the Start over row
  return out;
}
function viewProgressBody() {
  if (!env.ready) return [h('div', { class: 'sheet' }, busyLine('Loading your progress'))];
  const list = S.contest ? contestSkills() : [];
  const all = list.map(s => S.skills[s.id]).filter(Boolean);
  const n = all.reduce((a, s) => a + s.n, 0), ok = all.reduce((a, s) => a + s.ok, 0);
  if (!n) return [h('div', { class: 'sheet' }, h('h2', null, 'Nothing to show yet'), h('p', { class: 'muted' }, 'Answer a few problems and each skill appears here with its level and how many you got right.'), h('div', { class: 'row' }, h('a', { class: 'btn primary', href: '#practice', style: 'text-decoration:none;display:inline-flex;align-items:center' }, 'Go to practice')))];
  const reasons = {};
  for (const s of all) for (const k in s.reasons) reasons[k] = (reasons[k] || 0) + s.reasons[k];
  const top = Object.entries(reasons).sort((a, b) => b[1] - a[1])[0];
  const head = h('div', { class: 'sheet' },
    h('h2', null, n + (n === 1 ? ' problem' : ' problems') + ' answered, ' + Math.round(100 * ok / n) + '% correct'),
    h('p', { class: 'muted' }, CONTESTS[S.contest] + (S.placement.done ? '' : ', placement in progress') + '. Guesses count as not correct.'),
    top ? h('p', null, 'Most common trouble: ' + REASON_TEXT[top[0]].replace(/^I /, 'he ').replace(/^he didn't/, "didn't").replace(/^he knew/, 'knew').replace(/^he guessed/, 'guessed') + ' (' + top[1] + (top[1] === 1 ? ' time' : ' times') + ').') : null);
  const groups = TOPICS.filter(tp => list.some(s => s.topic === tp.id)).map(tp => h('div', { class: 'sheet' },
    h('h3', null, tp.name),
    h('div', null, list.filter(s => s.topic === tp.id).map(s => {
      const st = S.skills[s.id];
      return h('div', { class: 'prog-row' }, h('span', null, s.name), st && st.n ? levelDots(st.level) : h('span', { class: 'muted small' }, 'not tried'), h('span', { class: 'n' }, st && st.n ? st.ok + ' of ' + st.n + ' right' : ''));
    }))));
  const reset = h('div', { class: 'row' }, confirmReset
    ? [h('span', null, 'Erase all progress? Topics you added stay.'), h('button', { class: 'btn', type: 'button', onclick: () => { confirmReset = false; const kept = S.custom || []; S = newState(); S.custom = kept; syncCustom(); if (live) live.abort(); cur = null; dropPrepared(); saveState(); location.hash = '#practice'; render(); } }, 'Erase progress'), h('button', { class: 'btn quiet', type: 'button', onclick: () => { confirmReset = false; render(); } }, 'Keep it')]
    : h('button', { class: 'btn quiet', type: 'button', onclick: () => { confirmReset = true; render(); } }, 'Start over'));
  return [head, ...groups, reset];
}

