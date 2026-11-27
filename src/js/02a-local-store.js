/* ---------- served from the home computer: progress lives in its database ----------
   The server marks every answer, sets levels and keeps points; the page shows its own copy at once
   and takes the server's on the reply. Mock tests are kept in this browser until they move too. */
const LOCAL = { child: null, timer: null, chain: Promise.resolve() };
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
  const [sum, days, custom] = await Promise.all([api('GET', '/api/children/' + id), api('GET', '/api/children/' + id + '/days'), api('GET', '/api/children/' + id + '/topics')]);
  env.childName = sum.first_name || '';
  const set = sum.settings || {}, pl = sum.placement || {};
  let kept = {};                                           // what still lives in this browser: past mock test results
  try { kept = JSON.parse(localStorage.getItem(LS) || '{}') || {}; } catch (e) {}
  return {
    v: 1, contest: sum.contest || null, focus: sum.focus || null,
    placement: Array.isArray(pl.queue) ? { queue: pl.queue, i: pl.i || 0, done: !!pl.done } : { queue: [], i: 0, done: false },
    skills: Object.fromEntries(Object.entries(sum.skills || {}).map(([k, s]) => [k, fromServerSkill(s)])),
    goals: sum.goals, tier: set.tier === 'default' ? 'default' : 'quick', verify: !!set.verify,
    planned: set.planned || null, retry: set.retry || null, last: set.last || null,
    custom, points: sum.points || 0, topicPts: sum.topic_points || {}, name: sum.first_name || '',
    days: Object.fromEntries(days.map(d => [d.day, { n: d.n, ok: d.ok, pts: d.pts }])),
    mocks: Array.isArray(kept.mocks) ? kept.mocks : [],
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
    const prob = await api('POST', '/api/problems', { skill: t.skill, level: Math.max(1, Math.min(5, t.level)),
      contest: S.contest && S.contest !== 'both' ? S.contest : null, question: p.question, choices: p.choices, answer_index: p.answer,
      solution: p.solution || null, hints: p.hints || [], figure: p.figure || null, choice_figures: p.choice_figures || null,
      written_by: 'writer', check_status: p.checked ? 'passed' : 'unchecked' });
    const a = await api('POST', '/api/children/' + LOCAL.child + '/answers', { problem_id: prob.id, mode: t.mode,
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
