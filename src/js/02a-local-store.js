/* ---------- served from the home computer: progress lives in its database ----------
   The server marks every answer, sets levels and keeps points; the page shows its own copy at once
   and takes the server's on the reply. Mock tests run on the server's clock. */
const LOCAL = { child: null, timer: null, chain: Promise.resolve(), session: null, summary: null, resume: null };
async function api(method, path, body) {
  let r;
  try {
    r = await fetch(path, { method, headers: body ? { 'content-type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined });
  } catch (e) { throw { code: 'offline' }; }
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw { code: j.code || (r.status === 409 ? 'conflict' : 'failed'), detail: j.detail || '', status: r.status };
  return j;
}
const fromServerSkill = s => ({ level: s.level, up: s.up, down: s.down, n: s.attempts, ok: s.correct, reasons: s.reasons || {}, recent: s.recent || [] });
async function loadLocalState() {   // his saved progress from the database, in the page's own shape
  const kids = await api('GET', '/api/children');
  if (!kids.length) return null;
  const id = LOCAL.child = kids[0].id;                    // the first child, until there is a picker
  const [sum, days, custom, mocks] = await Promise.all([api('GET', '/api/children/' + id), api('GET', '/api/children/' + id + '/days'),
    api('GET', '/api/children/' + id + '/topics'), api('GET', '/api/children/' + id + '/mocks')]);
  env.childName = sum.first_name || '';
  LOCAL.summary = sum;
  LOCAL.resume = await localResume(sum).catch(() => null);
  const set = sum.settings || {}, pl = sum.placement || {};
  return {
    v: 1, contest: sum.contest || null, focus: sum.focus || null,
    placement: Array.isArray(pl.queue) ? { queue: pl.queue, i: pl.i || 0, done: !!pl.done } : { queue: [], i: 0, done: false },
    skills: Object.fromEntries(Object.entries(sum.skills || {}).map(([k, s]) => [k, fromServerSkill(s)])),
    goals: sum.goals, tier: set.tier === 'default' ? 'default' : 'quick', verify: !!set.verify,
    planned: set.planned || null, retry: set.retry || null, last: set.last || null,
    custom, points: sum.points || 0, topicPts: sum.topic_points || {}, name: sum.first_name || '',
    days: Object.fromEntries(days.map(d => [d.day, { n: d.n, ok: d.ok, pts: d.pts }])),
    mocks: mockHistoryFromServer(mocks),
  };
}
function localNotice(e) {
  showNotice(e && e.code === 'offline' ? "Can't reach the home computer, so this wasn't saved. Check that it is on."
    : 'Something could not be saved on the home computer. Your last answer may not count.');
}
function queueChildSave() {          // settings and the placement, sent a moment after the last change
  clearTimeout(LOCAL.timer);
  LOCAL.timer = setTimeout(() => {
    const g = goals(), body = { contest: S.contest, focus: S.focus, daily_goal: g.day, weekly_goal: g.week, placement: S.placement,
      settings: { tier: S.tier, verify: !!S.verify, planned: S.planned, retry: S.retry, last: S.last } };
    LOCAL.chain = LOCAL.chain.then(() => api('PATCH', '/api/children/' + LOCAL.child, body)).catch(localNotice);
  }, 300);
}
function localAnswer(c) {            // store the problem, then the answer; the reply's level and points are the real ones
  const p = c.p, t = c.target;
  c.saved = (async () => {
    const pid = await (c.problemSaved || Promise.reject()).catch(() => api('POST', '/api/problems', problemBody(c)).then(pr => pr.id));
    const a = await api('POST', '/api/children/' + LOCAL.child + '/answers', { problem_id: pid, mode: t.mode,
      chosen_index: c.picked, hints_used: c.hints, seconds: c.ms != null ? Math.round(c.ms / 1000) : null });
    S.skills[t.skill] = fromServerSkill(a.skill);
    return a.answer_id;
  })();
  c.saved.catch(localNotice);
}
function afterSave(c, step) {         // changes to one answer go out one at a time, in the order he made them
  if (!c.saved) return;
  c.queue = (c.queue || c.saved).then(id => step(id).catch(e => { if (e.status !== 409) localNotice(e); }).then(() => id));
  c.queue.catch(() => {});
}
function localReason(c) {            // a reason or note added after answering; a guess redoes the level change
  const body = { trouble_reason: c.reason || null, note: c.note || null };
  afterSave(c, id => api('PATCH', '/api/children/' + LOCAL.child + '/answers/' + id, body)
    .then(r => { if (r && r.releveled && r.skill) { S.skills[c.target.skill] = fromServerSkill(r.skill); if (cur === c) render(); } }));
}
function localRetry(c, pick) {       // another go at a missed problem, marked by the server
  afterSave(c, id => api('POST', '/api/children/' + LOCAL.child + '/answers/' + id + '/retry', { chosen_index: pick }));
}
function localLevel(skill, level) {  // placement sets a starting level directly
  api('PUT', '/api/children/' + LOCAL.child + '/skills/' + encodeURIComponent(skill), { level }).catch(localNotice);
}

/* ---------- practice: the problem on screen is saved as his current one, so any device can pick it up ---------- */
function problemBody(c) {
  const p = c.p, t = c.target;
  return { skill: t.skill, level: Math.max(1, Math.min(5, t.level)), contest: S.contest && S.contest !== 'both' ? S.contest : null,
    question: p.question, choices: p.choices, answer_index: p.answer, solution: p.solution || null, hints: p.hints || [],
    figure: p.figure || null, choice_figures: p.choice_figures || null, written_by: 'writer', check_status: p.checked ? 'passed' : 'unchecked' };
}
function practiceSet() {             // the open practice set, started once and reused
  if (!LOCAL.session) LOCAL.session = api('POST', '/api/children/' + LOCAL.child + '/practice', { kind: S.placement.done ? 'daily' : 'placement' }).then(s => s.id);
  LOCAL.session.catch(() => { LOCAL.session = null; });
  return LOCAL.session;
}
function localShowProblem(c) {
  c.problemSaved = api('POST', '/api/problems', problemBody(c)).then(pr => pr.id);
  c.problemSaved.then(pid => practiceSet().then(sid => api('PATCH', '/api/children/' + LOCAL.child + '/practice/' + sid, { current_problem_id: pid, position: doneToday() })))
    .catch(() => {});                // resuming is a convenience; the answer itself is what must be saved
}
const fromServerProblem = p => ({ question: p.question, choices: p.choices, answer: p.answer_index, hints: p.hints || [], solution: p.solution || '',
  figure: p.figure || null, choice_figures: p.choice_figures || null, checked: p.check_status === 'passed' });
async function localResume(sum) {    // the problem he left on screen, if he has not answered it since
  const open = sum.open_practice;
  if (!open || !open.current_problem_id) return null;
  LOCAL.session = Promise.resolve(open.id);
  const seen = await api('GET', '/api/children/' + LOCAL.child + '/seen');
  if (seen.includes(open.current_problem_id)) return null;
  const p = await api('GET', '/api/problems/' + open.current_problem_id);
  return p && p.answer_index != null ? p : null;
}
function resumeProblem(p) {          // put it back on screen exactly as it was
  const mode = !S.placement.done ? 'placement' : S.retry === p.skill ? 'retry' : 'practice';
  cur = { target: { skill: p.skill, level: p.level, mode }, p: fromServerProblem(p), picked: null, checked: false, hints: 0, t0: Date.now(),
    chat: [], chatOpen: false, reason: null, note: '', problemSaved: Promise.resolve(p.id), resumed: true };
}

/* ---------- mock tests: the server holds the paper, the clock and his answers ---------- */
async function localStartMock(m, minutes) {
  m.starting = true; render();
  try {
    const ids = await Promise.all(m.items.map(it => api('POST', '/api/problems', problemBody({ p: it.p, target: { skill: it.skill, level: it.level } })).then(pr => pr.id)));
    const made = await api('POST', '/api/children/' + LOCAL.child + '/mocks', { contest: mockPaper().key, size: m.size, minutes, unit: m.unit || 'point',
      items: m.items.map((it, i) => ({ problem_id: ids[i], points: it.points, label: it.label || null })) });
    const run = await api('POST', '/api/children/' + LOCAL.child + '/mocks/' + made.id + '/start');
    Object.assign(m, { serverId: made.id, phase: 'run', answers: m.items.map(() => null), at: 0, started: Date.parse(run.started_at), endsAt: Date.parse(run.ends_at), beat: Date.now() });
  } catch (e) { showNotice("The test couldn't be started on the home computer. Try again."); }
  m.starting = false;
  saveMock(); render();
}
function localMockAnswer(m, pos, choice) {   // only his latest answer to each question is kept
  m.sending = (m.sending || Promise.resolve()).then(() => api('PUT', '/api/children/' + LOCAL.child + '/mocks/' + m.serverId + '/answers/' + pos, { chosen_index: choice }))
    .catch(e => { if (e.status === 409) localMockBeat(m, true); else localNotice(e); });
}
function localMockBeat(m, now) {     // tell the server he is still here; it ends a test left for more than two minutes
  if (!m.serverId || m.phase !== 'run' || (!now && Date.now() - (m.beat || 0) < 15000)) return;
  m.beat = Date.now();
  api('POST', '/api/children/' + LOCAL.child + '/mocks/' + m.serverId + '/heartbeat').then(r => {
    if (mock !== m) return;
    if (r.status === 'abandoned') { mock = null; saveMock(); showNotice('The test was left for more than two minutes, so it ended. You can start a new one.'); render(); }
    else if (r.status === 'finished') finishMock();
  }).catch(() => {});
}
async function localFinishMock(m) {  // the server scores it; the keys come back for the review
  try {
    const done = await (m.sending || Promise.resolve()).then(() => api('POST', '/api/children/' + LOCAL.child + '/mocks/' + m.serverId + '/finish'));
    fillFromServer(m, done);
    m.serverDone = true;
    finishMock();
  } catch (e) {
    m.serverDone = false;
    if (e.status === 409) { mock = null; saveMock(); showNotice('The test was left for more than two minutes, so it was not scored.'); render(); }
    else localNotice(e);
  }
}
function fillFromServer(m, done) {   // keys, solutions and his saved answers, from the server's copy of the test
  done.items.forEach((row, i) => {
    const it = m.items[i];
    if (!it) return;
    if (row.problem.answer_index != null) { it.p.answer = row.problem.answer_index; it.p.solution = row.problem.solution || ''; }
    m.answers[i] = row.chosen_index;
  });
  if (done.seconds_used != null) m.usedSecs = done.seconds_used;
}
function mockFromServer(t) {         // a test on the server, in the page's shape
  return { v: 1, phase: t.status === 'in_progress' ? 'run' : 'done', serverId: t.id, serverDone: t.status === 'finished', size: t.size, unit: t.unit,
    items: t.items.map(r => ({ skill: r.problem.skill, level: r.problem.level, points: r.points, label: r.label, p: fromServerProblem(r.problem) })),
    answers: t.items.map(r => r.chosen_index), at: 0, started: Date.parse(t.started_at), endsAt: Date.parse(t.ends_at), usedSecs: t.seconds_used || 0, beat: 0 };
}
async function localLoadMock(sum) {  // a test still running on the server, or the one he last left in this browser
  if (sum.live_mock && sum.live_mock.status === 'in_progress') return mockFromServer(await api('GET', '/api/children/' + LOCAL.child + '/mocks/' + sum.live_mock.id));
  let kept = null;
  try { kept = JSON.parse(localStorage.getItem(LS_MOCK) || 'null'); } catch (e) {}
  if (!kept || !kept.serverId || kept.phase !== 'run') return null;
  const t = await api('GET', '/api/children/' + LOCAL.child + '/mocks/' + kept.serverId).catch(() => null);
  if (t && t.status === 'abandoned') showNotice('Your last test was left for more than two minutes, so it ended and was not scored.');
  return null;                       // a finished one is already in his history
}
const mockHistoryFromServer = list => list.map(t => ({ at: t.finished_at, size: t.size, n: t.questions, correct: t.correct, score: t.score, max: t.max_score, secs: t.seconds_used, unit: t.unit || 'point' })).reverse();
