/* ---------- leveling: two clean rights go up, two wrongs go down ---------- */
function applyResult(st, r) {
  const wrong = !r.correct || r.guessed;
  const clean = r.correct && !r.guessed && r.hints === 0;
  st.n++;
  if (!wrong) st.ok++;
  if (clean) { st.up++; st.down = 0; if (st.up >= 2 && st.level < 5) { st.level++; st.up = 0; } }
  else if (wrong) { st.down++; st.up = 0; if (st.down >= 2 && st.level > 1) { st.level--; st.down = 0; } }
  else { st.up = 0; st.down = 0; }
  if (wrong && r.reason) st.reasons[r.reason] = (st.reasons[r.reason] || 0) + 1;
  return st;
}
function focusSkills() {              // the skills in play: one topic if the student picked one, otherwise all of them
  const all = contestSkills();
  if (!S.focus) return all;
  const some = all.filter(s => s.id === S.focus || s.topic === S.focus);     // the choice is one skill or a whole topic
  if (some.length) return some;
  S.focus = null;                    // the chosen topic or skill is not in play any more, so fall back to the mix
  return all;
}
function pickNext(excludeId) {
  const pool = focusSkills(), others = pool.filter(s => s.id !== excludeId);
  const list = others.length ? others : pool;       // a topic with a single skill repeats that skill
  const weights = list.map(s => {
    const st = skillState(s.id);
    let w = 1 + (st.n === 0 ? 2 : 0) + (st.n >= 2 && st.ok / st.n < 0.6 ? 2 : 0) + (st.down > 0 ? 1 : 0);
    if (s.prerequisites.some(p => S.skills[p] && S.skills[p].n > 0 && S.skills[p].level <= 1)) w *= 0.2;
    return w;
  });
  let x = Math.random() * weights.reduce((a, b) => a + b, 0);
  for (let i = 0; i < list.length; i++) { x -= weights[i]; if (x <= 0) return list[i].id; }
  return list[list.length - 1].id;
}

