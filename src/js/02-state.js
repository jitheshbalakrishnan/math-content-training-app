/* ---------- state ---------- */
let S = null;                       // learner state (saved)
let cur = null;                     // the problem on screen (not saved)
let placedNote = false;
const env = { ready: false, sample: null, db: null, base: null };

function newState() { return { v: 1, contest: null, placement: { queue: [], i: 0, done: false }, skills: {}, planned: null, retry: null, last: null, custom: [], focus: null, verify: false, mocks: [], tier: 'quick' }; }
function skillState(id) { return S.skills[id] || (S.skills[id] = { level: 3, up: 0, down: 0, n: 0, ok: 0, reasons: {}, recent: [] }); }
function allSkills() { return MAP.skills.concat(S.custom || []); }
function syncCustom() {              // keep the lookup table in step with the topics a parent added
  for (const k in SK) if (k.startsWith('custom.')) delete SK[k];
  for (const s of (S.custom || [])) SK[s.id] = s;
}
function choiceCount() {              // how many answer choices a problem has: 4 for a contest that uses four, otherwise 5
  const c = MAP.contests[S.contest];
  return (c && c.choices) || 5;
}
function styleFor(sk) {               // a contest style guide for this skill, from the contests the learner is training for
  const ok = sk.contests.filter(c => MAP.contests[c] && MAP.contests[c].style && (S.contest === 'both' || S.contest === c));
  if (!ok.length) return null;
  const c = ok[Math.floor(Math.random() * ok.length)];
  return { name: MAP.contests[c].short, style: MAP.contests[c].style };
}
function contestSkills() { return allSkills().filter(s => S.contest === 'both' || s.contests.includes(S.contest)); }

function showNotice(t) { const n = $('notice'); n.textContent = t; n.hidden = !t; }

async function loadState() {
  if (env.db && env.base) {
    try {
      const snap = await env.db.collection(env.base).doc('state').get();
      if (snap.exists) return clone(snap.data());      // documents from the database are frozen; the app edits its state in place, so it needs its own copy
    } catch (e) { env.db = null; showNotice('Could not reach your saved progress. For now, progress is kept on this device only.'); }
  }
  try { const raw = localStorage.getItem(LS); return raw ? JSON.parse(raw) : null; } catch (e) { return null; }
}
let saveChain = Promise.resolve();
function saveState() {
  const copy = clone(S);
  try { localStorage.setItem(LS, JSON.stringify(copy)); } catch (e) {}
  if (env.db && env.base) {
    saveChain = saveChain.then(() => env.db.collection(env.base).doc('state').set(copy))
      .catch(() => showNotice('Could not save to your account just now. Progress is kept on this device.'));
  }
}
async function logAttempt(a) {
  if (!(env.db && env.base)) return null;
  try { return await env.db.collection(env.base).doc('log').collection('attempts').add(a); } catch (e) { return null; }
}

