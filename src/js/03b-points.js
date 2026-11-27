/* ---------- points: a reward that never changes levels; right first time earns the level, a fixed retry earns 1 ---------- */
function pointsFor(level, correct, guessed, fixed) {
  if (correct && !guessed) return Math.max(1, Math.min(5, level || 1));
  return fixed ? 1 : 0;
}
function award(delta, topic) {       // add (or take back) points, for the total, today and the topic
  if (!delta) return;
  S.points = Math.max(0, (S.points || 0) + delta);
  if (!S.days || typeof S.days !== 'object' || Array.isArray(S.days)) S.days = {};
  const day = S.days[dayKey()] || (S.days[dayKey()] = { n: 0, ok: 0 });
  day.pts = Math.max(0, (day.pts || 0) + delta);
  if (!S.topicPts || typeof S.topicPts !== 'object') S.topicPts = {};
  const t = topic || 'custom';
  S.topicPts[t] = Math.max(0, (S.topicPts[t] || 0) + delta);
}
function repoint(c) {                // bring this problem's points in line with what we now know (a guess, a fixed retry)
  const want = pointsFor(c.target.level, c.correct, c.reason === 'guess', !!c.fixed);
  award(want - (c.pts || 0), SK[c.target.skill] && SK[c.target.skill].topic);
  c.pts = want;
}
function pointsToday() { const d = S.days && S.days[dayKey()]; return (d && d.pts) || 0; }

/* The climb: points take him up a mountain, camp by camp. After the summit a new, taller climb starts. */
const CAMPS = [[0, 'Base camp'], [50, 'Camp 1'], [150, 'Camp 2'], [300, 'Camp 3'], [500, 'High camp'], [800, 'Summit']];
const SUMMIT = CAMPS[CAMPS.length - 1][0];
function climb(points) {
  const p = Math.max(0, points || 0), mountain = Math.floor(p / SUMMIT) + 1, here = p % SUMMIT;
  let at = 0;
  for (let i = 0; i < CAMPS.length; i++) if (here >= CAMPS[i][0]) at = i;
  const next = CAMPS[at + 1];
  return { mountain, here, camp: CAMPS[at][1], next: next ? next[1] : null, toNext: next ? next[0] - here : 0, share: here / SUMMIT };
}
function campShare(points) {         // how far he is from the last camp to the next, 0 to 100
  const c = climb(points), i = CAMPS.findIndex(x => x[1] === c.camp), from = CAMPS[i][0], to = (CAMPS[i + 1] || [SUMMIT])[0];
  return to > from ? Math.round(100 * (c.here - from) / (to - from)) : 100;
}
function childName() { return (env.childName || S.name || '').trim(); }
