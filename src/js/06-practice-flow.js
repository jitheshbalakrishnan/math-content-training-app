/* ---------- practice flow ---------- */
function nextTarget() {
  const pool = focusSkills();        // also clears a chosen topic that has no skills left
  if (!S.focus) {                    // placement waits while the student practices a chosen topic
    while (!S.placement.done && !SK[S.placement.queue[S.placement.i]]) {   // skip a placement slot whose topic was removed
      S.placement.i++;
      if (S.placement.i >= S.placement.queue.length) S.placement.done = true;
    }
    if (!S.placement.done) return { skill: S.placement.queue[S.placement.i], level: 3, mode: 'placement' };
  }
  if (S.retry && SK[S.retry]) return { skill: S.retry, level: skillState(S.retry).level, mode: 'retry' };
  if (!S.planned || !SK[S.planned] || S.planned === S.last || !pool.some(x => x.id === S.planned)) S.planned = pickNext(S.last);
  return { skill: S.planned, level: skillState(S.planned).level, mode: 'practice' };
}
async function loadProblem() {
  const t = nextTarget();
  cur = { target: t, loading: true, since: Date.now() };
  render();
  try {
    const wanted = takeProblem(t.skill, t.level);
    // Start the following problem now, so it is being written while this one is written and solved.
    if (t.mode === 'placement') { const nx = S.placement.queue[S.placement.i + 1]; if (nx && SK[nx]) fetchProblem(nx, 3); }
    else { S.planned = pickNext(t.skill); fetchProblem(S.planned, skillState(S.planned).level); }
    const p = await wanted;
    if (!cur || cur.target !== t) return;
    cur = { target: t, p, picked: null, checked: false, hints: 0, t0: Date.now(), chat: [], chatOpen: false, reason: null, note: '' };
  } catch (e) {
    if (!cur || cur.target !== t) return;
    cur = { target: t, error: errCopy(e), why: e && e.why };
    if (e && e.code === 'unverified' && t.mode === 'placement') {      // do not keep retrying a skill that just failed twice
      const others = contestSkills().filter(x => x.topic === SK[t.skill].topic && x.id !== t.skill && !S.placement.queue.includes(x.id));
      if (others.length) {
        S.placement.queue[S.placement.i] = others[Math.floor(Math.random() * others.length)].id;
        cur.swapped = true; saveState();
      }
    }
  }
  try { render(); }
  catch (e) {                          // a problem that cannot be drawn must not leave the waiting screen up forever
    console.error(e);
    cur = { target: t, error: 'That problem could not be shown, so it was dropped. Try again for a new one.' };
    render();
  }
}
const STAGE_TEXT = { write: 'Writing a problem', check: 'Checking its answer', redo: 'The first draft could not be used. Writing another', recheck: 'Checking the second draft' };
function waitText() {
  const secs = Math.round((Date.now() - cur.since) / 1000);
  return (STAGE_TEXT[stage.get(cur.target.skill + '@' + cur.target.level)] || STAGE_TEXT.write) + ' (' + secs + ' s)';
}
setInterval(() => {                    // keep the waiting screen honest about how long it has been
  if (!cur || !cur.loading) return;
  const line = $('wait-line'), again = $('wait-again');
  if (line) line.textContent = waitText();
  if (again) again.hidden = Date.now() - cur.since < 45000;
}, 1000);
function settle() {                  // (re)apply this problem's outcome from the snapshot taken before it
  const c = cur, id = c.target.skill;
  const st = applyResult(clone(c.before), { correct: c.correct, guessed: c.reason === 'guess', hints: c.hints, reason: c.reason });
  st.recent = c.before.recent.concat(c.p.question.slice(0, 160)).slice(-3);
  S.skills[id] = st;
  saveState();
}
function check() {
  const c = cur, id = c.target.skill;
  if (c.picked == null || c.checked) return;
  c.checked = true; c.correct = c.picked === c.p.answer; c.ms = Date.now() - c.t0;
  c.before = clone(skillState(id));
  const goal = goals().day, soFar = doneToday();
  tally(1, c.correct ? 1 : 0);
  c.fresh = true;
  c.setDone = soFar < goal && doneToday() >= goal;      // this answer finished today's set
  settle();
  if (!c.correct && c.target.mode === 'practice') fetchProblem(id, skillState(id).level);
  c.log = logAttempt({ at: new Date().toISOString(), skill: id, level: c.target.level, mode: c.target.mode, question: c.p.question, figure: c.p.figure || null, choices: c.p.choices, answer: c.p.answer, picked: c.picked, correct: c.correct, ms: c.ms, hints: c.hints, reason: null, note: '' });
  render();
}
function checkRetry() {              // another go at a missed question; stats and level keep the first answer
  const c = cur;
  if (!c || !c.retrying || c.pick2 == null) return;
  c.fresh = true;
  if (c.pick2 === c.p.answer) c.fixed = true;
  else c.missed = (c.missed || []).concat(c.pick2);
  c.retrying = false; c.pick2 = null;
  if (c.log) c.log.then(ref => ref && ref.update({ retries: (c.missed || []).length + (c.fixed ? 1 : 0), fixed: !!c.fixed })).catch(() => {});
  render();
}
function setFeedback(patch) {
  const c = cur; Object.assign(c, patch); settle();
  if (c.log) c.log.then(ref => ref && ref.update({ reason: c.reason, note: c.note })).catch(() => {});
  render();
}
function advance() {
  const c = cur, id = c.target.skill, wrong = !c.correct || c.reason === 'guess';
  if (c.ctl) c.ctl.abort();
  if (c.target.mode === 'placement') {
    if (wrong) for (const s of contestSkills()) if (s.topic === SK[id].topic) { const x = skillState(s.id); if (x.n === 0 || s.id === id) { x.level = 2; x.up = 0; x.down = 0; } }
    S.placement.i++;
    if (S.placement.i >= S.placement.queue.length) { S.placement.done = true; placedNote = true; }
  } else S.retry = (c.target.mode === 'practice' && wrong) ? id : null;
  S.last = id;
  saveState();
  loadProblem();
}
function chooseContest(key) {
  S.contest = key;
  const byTopic = {};
  for (const s of contestSkills()) (byTopic[s.topic] = byTopic[s.topic] || []).push(s.id);
  S.placement = { queue: Object.values(byTopic).map(a => a[Math.floor(Math.random() * a.length)]), i: 0, done: false };
  saveState(); render();
}

