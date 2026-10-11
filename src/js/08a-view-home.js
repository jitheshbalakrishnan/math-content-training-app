/* ---------- home: today's set and the ways in ---------- */
function viewHome() {
  if (!env.ready) return [h('div', { class: 'sheet' }, busyLine('Loading your progress'))];
  if (!S.contest) return viewPracticeBody();                // first visit: choose a contest
  const g = goals(), done = doneToday(), run = streak(), week = thisWeek().reduce((a, d) => a + d.n, 0);
  const pl = S.placement, placing = !pl.done && !S.focus, left = pl.queue.length - pl.i;
  const focus = S.focus ? (SK[S.focus] ? SK[S.focus].name : TOPIC[S.focus]) : '';
  const go = () => { location.hash = '#practice'; if (!cur && env.sample) loadProblem(); else render(); };
  const say = placing ? 'First, ' + left + (left === 1 ? ' problem' : ' problems') + ' to find your level. They count toward today.'
    : done >= g.day ? "Today's set is done. You answered " + done + ' problems.'
    : done ? 'You have done ' + done + " of today's " + g.day + ' problems.'
    : g.day + ' problems' + (focus ? ' on ' + focus + '.' : ', mixed from every topic.');
  const label = placing ? (pl.i ? 'Carry on finding my level' : 'Find my level')
    : done >= g.day ? 'Practice some more' : done ? 'Carry on with problem ' + (done + 1) : "Start today's set";
  return [h('div', { class: 'home' },
    h('div', { class: 'stack' },
      h('div', { class: 'sheet' },
        h('h2', null, 'Today'),
        h('p', null, say),
        h('div', { class: 'setline' }, setBar(done, g.day, done < g.day ? done : -1)),
        h('div', { class: 'row' }, h('button', { class: 'btn primary', type: 'button', onclick: go }, label))),
      run >= 2 ? h('p', { class: 'notice' }, run + ' days of practice in a row') : null),
    h('div', { class: 'stack' },
      h('div', { class: 'sheet' },
        h('h3', null, 'Or choose'),
        h('div', { class: 'stack' },
          h('a', { class: 'btn', href: '#practice' }, 'Practice one topic'),
          h('a', { class: 'btn', href: '#mock' }, 'Take a timed mock test'),
          h('a', { class: 'btn', href: '#progress' }, 'See my progress'))),
      h('p', { class: 'muted' }, 'This week: ' + week + ' of ' + g.week + ' problems')))];
}
