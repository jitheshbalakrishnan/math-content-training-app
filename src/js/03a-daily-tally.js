/* ---------- daily tally: how many problems he answered each day, for today's set, the week and the streak ---------- */
function dayKey(d) {                 // a local calendar day as YYYY-MM-DD
  const x = d || new Date();
  return x.getFullYear() + '-' + String(x.getMonth() + 1).padStart(2, '0') + '-' + String(x.getDate()).padStart(2, '0');
}
function goals() {
  const g = S.goals || {};
  return { day: g.day > 0 ? g.day : 10, week: g.week > 0 ? g.week : 50 };
}
function tally(n, ok) {              // count n answered problems, ok of them right, against today
  if (!S.days || typeof S.days !== 'object' || Array.isArray(S.days)) S.days = {};
  const k = dayKey(), day = S.days[k] || (S.days[k] = { n: 0, ok: 0 });
  day.n += n; day.ok += ok;
  const keys = Object.keys(S.days).sort();
  for (const old of keys.slice(0, Math.max(0, keys.length - 120))) delete S.days[old];      // keep about four months
}
function doneToday() { const day = S.days && S.days[dayKey()]; return day ? day.n : 0; }
function thisWeek() {                // Monday to Sunday, each with its count
  const now = new Date(), today = dayKey(now), back = (now.getDay() + 6) % 7;
  return [...'MTWTFSS'].map((letter, i) => {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - back + i), key = dayKey(d), day = S.days && S.days[key];
    return { letter, key, n: day ? day.n : 0, today: key === today, future: key > today };
  });
}
function streak() {                  // days in a row with practice, ending today, or yesterday if he has not practiced yet today
  const now = new Date();
  let count = 0;
  for (let i = 0; i < 400; i++) {
    const day = S.days && S.days[dayKey(new Date(now.getFullYear(), now.getMonth(), now.getDate() - i))];
    if (day && day.n > 0) count++;
    else if (i > 0) break;
  }
  return count;
}
function setBar(done, total, now) {  // one square per problem: filled when done, highlighted for the one in hand
  return h('span', { class: 'setbar', role: 'img', 'aria-label': Math.min(done, total) + ' of ' + total + ' done' },
    Array.from({ length: total }, (_, i) => h('i', { class: i < done ? 'on' : i === now ? 'now' : '' })));
}
