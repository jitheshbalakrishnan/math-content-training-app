function render() {
  const route = ['practice', 'progress', 'parents', 'mock', 'score'].find(r => location.hash === '#' + r) || 'home';
  for (const r of ['home', 'practice', 'mock', 'score', 'progress', 'parents']) { const a = $('tab-' + r); if (r === route) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); }
  $('view').replaceChildren(...(route === 'progress' ? viewProgress() : route === 'parents' ? viewParents() : route === 'mock' ? viewMock() : route === 'score' ? viewScore() : route === 'home' ? viewHome() : viewPractice()));
  document.querySelector('.book').classList.toggle('wide', !!$('view').querySelector('.work'));     // room for the scratchpad beside the problem
  if (route === 'practice' && cur && cur.p) { if (cur.chatOpen) renderChat(); if (cur.target.mode !== 'placement' && placedNote && cur.checked) placedNote = false; }
}
window.addEventListener('hashchange', render);

async function boot() {
  S = newState();
  render();
  const use = n => (window.claude && window.claude.use) ? window.claude.use(n).catch(() => null) : Promise.resolve(null);
  const [sample, db, user] = await Promise.all([use('sample'), use('db'), use('user')]);
  env.sample = sample;
  if (!sample && await findLocalServer()) { env.sample = localSample(); env.local = true; env.childName = await localChildName(); }
  if (db && user) { try { const id = await user.id(); if (id) { env.db = db; env.base = 'data/users/' + id; } } catch (e) {} }
  const saved = await loadState();
  if (saved && saved.v === 1) S = Object.assign(newState(), saved);
  if (!Array.isArray(S.custom)) S.custom = [];
  syncCustom();
  if (!Array.isArray(S.mocks)) S.mocks = [];
  if (!S.days || typeof S.days !== 'object' || Array.isArray(S.days)) S.days = {};
  if (!S.goals || typeof S.goals !== 'object') S.goals = { day: 10, week: 50 };
  if (typeof S.points !== 'number' || !(S.points >= 0)) S.points = 0;
  if (!S.topicPts || typeof S.topicPts !== 'object' || Array.isArray(S.topicPts)) S.topicPts = {};
  if (typeof S.name !== 'string') S.name = '';
  mock = await loadMock();
  env.ready = true;
  if (mock && mock.phase === 'run' && Date.now() >= mock.endsAt) finishMock();   // time ran out while the page was closed
  else render();
}
boot();
