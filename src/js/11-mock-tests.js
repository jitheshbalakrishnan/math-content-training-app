/* ---------- mock tests: a timed paper in the Math Kangaroo format, with no hints, tutor or feedback until the end ---------- */
const MOCK_SIZES = { short: { name: 'Short test', part: 0.4 }, full: { name: 'Full test', part: 1 } };
function mockPaper() {               // the real paper's layout for the learner's contest; Math Kangaroo's when that contest has none on file
  const c = MAP.contests[S.contest];
  return c && c.paper ? { key: S.contest, paper: c.paper } : { key: 'kangaroo', paper: MAP.contests.kangaroo.paper };
}
function mockShape(size) {           // how many questions per section, and how long, for a short or a full test
  const { paper } = mockPaper(), part = MOCK_SIZES[size].part;
  const sections = paper.sections.map(sec => Object.assign({}, sec, { count: Math.max(1, Math.round(sec.count * part)) }));
  const count = sections.reduce((a, sec) => a + sec.count, 0), full = paper.sections.reduce((a, sec) => a + sec.count, 0);
  return { sections, count, minutes: Math.max(5, Math.round(paper.minutes * count / full)), unit: paper.unit || 'point' };
}
const units = (k, unit) => k + ' ' + unit + (k === 1 ? '' : 's');
const LS_MOCK = 'mct-mock-v1';
let mock = null;                     // null, or { phase: 'prep' | 'run' | 'done', size, items, ... }
let mockChain = Promise.resolve();
let confirmFinish = false;

function saveMock() {                // a test in progress survives a reload; the clock keeps running, as in a real test
  const keep = mock && mock.phase !== 'prep' ? clone({ v: 1, phase: mock.phase, size: mock.size, answers: mock.answers, at: mock.at, started: mock.started, endsAt: mock.endsAt, usedSecs: mock.usedSecs || 0, unit: mock.unit || 'point',
    items: mock.items.map(it => ({ skill: it.skill, level: it.level, points: it.points, label: it.label, p: it.p })) }) : null;
  try { if (keep) localStorage.setItem(LS_MOCK, JSON.stringify(keep)); else localStorage.removeItem(LS_MOCK); } catch (e) {}
  if (env.db && env.base) {
    const doc = env.db.collection(env.base).doc('mock');
    mockChain = mockChain.then(() => keep ? doc.set(keep) : doc.delete()).catch(() => {});
  }
}
async function loadMock() {
  let m = null;
  if (env.db && env.base) { try { const snap = await env.db.collection(env.base).doc('mock').get(); if (snap.exists) m = clone(snap.data()); } catch (e) {} }     // a frozen document would silently refuse his answers
  if (!m) { try { const raw = localStorage.getItem(LS_MOCK); m = raw ? JSON.parse(raw) : null; } catch (e) {} }
  const ok = m && m.v === 1 && (m.phase === 'run' || m.phase === 'done') && Array.isArray(m.items) && m.items.length && Array.isArray(m.answers)
    && m.items.every(it => it && it.p && Array.isArray(it.p.choices) && typeof it.p.question === 'string');
  return ok ? m : null;
}
function shuffled(list) { const a = list.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
function mockPlan(size) {            // the paper's sections in order, spread across the contest's own syllabus skills
  const shape = mockShape(size), all = contestSkills(), core = all.filter(x => !x.extra);
  const skills = shuffled(core.length ? core : all), plan = [];
  let k = 0;
  for (const sec of shape.sections) for (let i = 0; i < sec.count; i++) {
    const level = sec.levels[Math.floor(i * sec.levels.length / sec.count)];
    plan.push({ skill: skills[k++ % skills.length].id, level, points: sec.points, label: sec.label, status: 'wait', p: null });
  }
  return plan;
}
function prepareMock(size) {
  const shape = mockShape(size);
  mock = { phase: 'prep', size, items: mockPlan(size), ctl: new AbortController(), unit: shape.unit, planned: shape.count, plannedMinutes: shape.minutes };
  writeMockItems();
}
async function writeMockItems() {    // write every question still missing, two at a time, each one tried once per press
  const m = mock, todo = m.items.filter(it => it.status !== 'ok');
  for (const it of todo) it.status = 'wait';
  m.busy = true; m.stop = '';
  render();
  const worker = async () => {
    for (let it = todo.shift(); it && !m.ctl.signal.aborted; it = todo.shift()) {
      try { it.p = await makeProblem(it.skill, it.level, m.ctl.signal); it.status = 'ok'; }
      catch (e) {
        it.status = 'fail';
        if (e && (e.code === 'not_granted' || e.code === 'rate_limited')) { m.stop = errCopy(e); todo.forEach(x => { x.status = 'fail'; }); todo.length = 0; }
      }
      if (mock === m && m.phase === 'prep') render();
    }
  };
  await Promise.all([worker(), worker()]);
  m.busy = false;
  if (mock === m && m.phase === 'prep') render();
}
function cancelMock() { if (mock && mock.ctl) mock.ctl.abort(); mock = null; confirmFinish = false; pad.forget(); saveMock(); render(); }
function startMock() {
  const m = mock;
  m.items = m.items.filter(it => it.status === 'ok');
  const minutes = Math.max(5, Math.round(m.plannedMinutes * m.items.length / m.planned));    // fewer questions, less time
  pad.forget();
  m.phase = 'run'; m.answers = m.items.map(() => null); m.at = 0;
  m.started = Date.now(); m.endsAt = m.started + minutes * 60000;
  saveMock(); render();
}
function mockScore(m) {
  const r = { correct: 0, score: 0, max: 0, blank: 0, tier: {}, topic: {} };
  m.items.forEach((it, i) => {
    const ok = m.answers[i] === it.p.answer, name = SK[it.skill] ? TOPIC[SK[it.skill].topic] : 'Other';
    const part = it.label || it.points + '-point questions';
    const t = r.tier[part] || (r.tier[part] = { ok: 0, n: 0 }), g = r.topic[name] || (r.topic[name] = { ok: 0, n: 0 });
    t.n++; g.n++; r.max += it.points;
    if (m.answers[i] == null) r.blank++;
    if (ok) { t.ok++; g.ok++; r.correct++; r.score += it.points; }
  });
  return r;
}
function finishMock() {
  const m = mock;
  if (!m || m.phase !== 'run') return;
  m.phase = 'done'; confirmFinish = false; pad.forget();
  m.usedSecs = Math.round((Math.min(Date.now(), m.endsAt) - m.started) / 1000);
  const r = mockScore(m), at = new Date().toISOString();
  S.mocks = (S.mocks || []).concat({ at, size: m.size, n: m.items.length, correct: r.correct, score: r.score, max: r.max, secs: m.usedSecs, unit: m.unit || 'point' }).slice(-20);
  saveState(); saveMock();          // skill levels are left alone: a test measures, practice teaches
  m.items.forEach((it, i) => logAttempt({ at, skill: it.skill, level: it.level, mode: 'mock', question: it.p.question, figure: it.p.figure || null, choices: it.p.choices, answer: it.p.answer, picked: m.answers[i], correct: m.answers[i] === it.p.answer, ms: null, hints: 0, reason: null, note: '' }));
  render();
}
const clockText = ms => { const sec = Math.max(0, Math.ceil(ms / 1000)); return Math.floor(sec / 60) + ':' + String(sec % 60).padStart(2, '0'); };
setInterval(() => {                  // the test clock; time is taken from the end time, so a reload cannot add minutes
  if (!mock || mock.phase !== 'run') return;
  const left = mock.endsAt - Date.now();
  if (left <= 0) { finishMock(); return; }
  const el = $('mock-clock');
  if (el) { el.textContent = clockText(left); el.classList.toggle('low', left < 5 * 60000); }
}, 1000);

function mockChoices(it, picked, review, onPick) {
  const p = it.p;
  return h('div', { role: 'group', 'aria-label': 'Answer choices' }, p.choices.map((txt, i) => {
    const right = review && i === p.answer, wrong = review && picked === i && i !== p.answer;
    return h('button', { class: 'choice' + (p.choice_figures ? ' pic' : '') + (right ? ' right' : wrong ? ' wrong' : ''), type: 'button', disabled: review, 'aria-pressed': !review && picked === i ? 'true' : 'false', onclick: () => onPick && onPick(i) },
      h('b', null, LETTERS[i]), h('span', null, p.choice_figures ? figureEl(p.choice_figures[i], true) : txt),
      right ? h('em', null, picked === i ? 'Your answer, correct' : 'Correct answer') : wrong ? h('em', null, 'Your answer') : null);
  }));
}
function viewMock() {
  if (!env.ready) return [h('div', { class: 'sheet' }, busyLine('Loading'))];
  if (!mock) {
    if (!S.contest) return [h('div', { class: 'sheet' }, h('h2', null, 'Pick a contest first'), h('p', { class: 'muted' }, 'Choose what you are training for on the Practice tab, then come back for a test.'), h('div', { class: 'row' }, h('a', { class: 'btn primary', href: '#practice', style: 'text-decoration:none;display:inline-flex;align-items:center' }, 'Go to practice')))];
    if (!env.sample) return [h('div', { class: 'sheet' }, h('h2', null, 'Open this page in Claude to take a test'), h('p', { class: 'muted' }, 'Test questions are written by Claude, which is not available in this view.'))];
    const { key, paper } = mockPaper(), mine = key === S.contest;
    return [h('div', { class: 'sheet' },
      h('h2', null, 'Timed mock test'),
      h('p', null, 'Set up like the real ' + CONTESTS[key] + ' paper, with a countdown clock and no hints or tutor until you finish.' + (paper.note ? ' ' + paper.note : '')),
      h('p', { class: 'muted' }, 'The full paper: ' + paper.sections.map(sec => sec.count + ' questions at ' + units(sec.points, paper.unit || 'point')).join(', ') + ', in ' + paper.minutes + ' minutes.'),
      mine ? null : h('p', { class: 'muted' }, 'This uses the ' + CONTESTS[key] + ' layout with your ' + (CONTESTS[S.contest] === 'All of them' ? 'topics from every contest' : CONTESTS[S.contest] + ' topics') + '.'),
      h('div', { class: 'row' }, Object.keys(MOCK_SIZES).map(k => { const sh = mockShape(k); return h('button', { class: 'btn', type: 'button', onclick: () => prepareMock(k) }, MOCK_SIZES[k].name + ': ' + sh.count + ' questions, ' + sh.minutes + ' minutes'); })),
      h('p', { class: 'muted small' }, 'Every question is written before the clock starts. That takes a few minutes for a short test and a good deal longer for a full one. A full test also uses a lot of Claude usage.'))];
  }
  const m = mock, n = m.items.length;
  if (m.phase === 'prep') {
    const ready = m.items.filter(it => it.status === 'ok').length, failed = m.items.filter(it => it.status === 'fail').length;
    return [h('div', { class: 'sheet' },
      h('h2', null, m.busy ? 'Writing your test' : failed ? 'Some questions are missing' : 'Your test is ready'),
      h('p', null, m.busy ? h('span', { class: 'dots' }, h('i'), h('i'), h('i')) : null, ready + ' of ' + n + ' questions ready'),
      h('div', { class: 'slots', role: 'img', 'aria-label': ready + ' of ' + n + ' questions ready' }, m.items.map(it => h('i', { class: it.status === 'ok' ? 'ok' : it.status === 'fail' ? 'fail' : '' }))),
      m.stop ? h('p', null, m.stop) : null,
      !m.busy && failed ? h('p', { class: 'muted' }, failed + (failed === 1 ? ' question' : ' questions') + ' could not be written.') : null,
      !m.busy && !failed ? h('p', { class: 'muted' }, 'The clock starts when you press Start. Have paper and a pencil ready.') : null,
      h('div', { class: 'row' },
        !m.busy && ready >= 3 ? h('button', { class: 'btn primary', type: 'button', onclick: startMock }, failed ? 'Start with ' + ready + ' questions' : 'Start the test') : null,
        !m.busy && failed ? h('button', { class: 'btn', type: 'button', onclick: writeMockItems }, 'Write the missing ones') : null,
        h('button', { class: 'btn quiet', type: 'button', onclick: cancelMock }, 'Cancel')))];
  }
  if (m.phase === 'run') {
    const it = m.items[m.at], left = m.endsAt - Date.now(), answered = m.answers.filter(a => a != null).length;
    const go = i => { m.at = Math.max(0, Math.min(n - 1, i)); confirmFinish = false; saveMock(); render(); };
    return [
      h('div', { class: 'mockbar' }, h('span', { class: 'clock' + (left < 5 * 60000 ? ' low' : ''), id: 'mock-clock', role: 'timer', 'aria-label': 'Time left' }, clockText(left)),
        h('span', null, 'Question ' + (m.at + 1) + ' of ' + n + ', ' + units(it.points, m.unit || 'point'))),
      withPad('mock' + m.at, h('div', { class: 'sheet' },
        h('p', { class: 'question' }, it.p.question),
        it.p.figure ? figureEl(it.p.figure) : null,
        mockChoices(it, m.answers[m.at], false, i => { m.answers[m.at] = m.answers[m.at] === i ? null : i; saveMock(); render(); }),
        h('div', { class: 'row' },
          h('button', { class: 'btn quiet', type: 'button', disabled: m.at === 0, onclick: () => go(m.at - 1) }, 'Back'),
          h('button', { class: 'btn primary', type: 'button', disabled: m.at === n - 1, onclick: () => go(m.at + 1) }, 'Next question')),
        h('hr'),
        h('div', { class: 'qnav', role: 'group', 'aria-label': 'Jump to a question' }, m.items.map((x, i) => h('button', { type: 'button', class: m.answers[i] != null ? 'done' : '', 'aria-current': i === m.at ? 'true' : 'false', 'aria-label': 'Question ' + (i + 1) + (m.answers[i] != null ? ', answered' : ', not answered'), onclick: () => go(i) }, i + 1))),
        h('div', { class: 'row' }, confirmFinish
          ? [h('span', null, 'Finish now? You answered ' + answered + ' of ' + n + '.'), h('button', { class: 'btn', type: 'button', onclick: finishMock }, 'Finish the test'), h('button', { class: 'btn quiet', type: 'button', onclick: () => { confirmFinish = false; render(); } }, 'Keep going')]
          : h('button', { class: 'btn', type: 'button', onclick: () => { confirmFinish = true; render(); } }, 'Finish the test'))))];
  }
  const r = mockScore(m), unchecked = m.items.some(it => !it.p.checked);
  return [h('div', { class: 'sheet' },
      h('h2', null, r.score + ' of ' + units(r.max, m.unit || 'point')),
      h('p', null, r.correct + ' of ' + n + ' correct in ' + clockText((m.usedSecs || 0) * 1000) + (r.blank ? ', with ' + r.blank + ' left blank' : '') + '.'),
      unchecked ? h('p', { class: 'muted small' }, 'The answer keys on this test were not double-checked, so now and then a key may be wrong. If an answer looks wrong, ask a grown-up.') : null,
      h('div', { class: 'tally' }, Object.keys(r.tier).flatMap(k => [h('span', null, k), h('span', null, r.tier[k].ok + ' of ' + r.tier[k].n)])),
      h('hr'),
      h('div', { class: 'tally' }, Object.keys(r.topic).flatMap(k => [h('span', null, k), h('span', null, r.topic[k].ok + ' of ' + r.topic[k].n)])),
      h('div', { class: 'row' }, h('button', { class: 'btn primary', type: 'button', onclick: cancelMock }, 'Take another test'))),
    h('div', { class: 'sheet' }, h('h3', null, 'Go through your answers'),
      h('div', null, m.items.map((it, i) => {
        const a = m.answers[i], verdict = a == null ? 'left blank' : a === it.p.answer ? 'correct' : 'not correct';
        return h('details', { class: 'rev' }, h('summary', null, 'Question ' + (i + 1) + ', ' + units(it.points, m.unit || 'point') + ', ' + verdict),
          h('div', null, h('p', { class: 'question' }, it.p.question), it.p.figure ? figureEl(it.p.figure) : null, mockChoices(it, a, true), h('p', { class: 'solution' }, it.p.solution)));
      })))];
}
function mockHistory() {
  return h('div', { class: 'sheet' }, h('h3', null, 'Mock tests'),
    h('div', null, S.mocks.slice().reverse().map(x => h('div', { class: 'prog-row' },
      h('span', null, new Date(x.at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + ', ' + (MOCK_SIZES[x.size] ? MOCK_SIZES[x.size].name.toLowerCase() : 'test')),
      h('span', null, x.score + ' of ' + units(x.max, x.unit || 'point')),
      h('span', { class: 'n' }, x.correct + ' of ' + x.n + ' right')))));
}

