const MAP = __SKILLMAP__;
const SK = Object.fromEntries(MAP.skills.map(s => [s.id, s]));
const TOPICS = MAP.topics.concat([{ id: 'custom', name: 'Added topics' }]);
const TOPIC = Object.fromEntries(TOPICS.map(t => [t.id, t.name]));
const MAX_ADDED = 20;
const CONTEST_KEYS = Object.keys(MAP.contests);
const CONTESTS = Object.assign(Object.fromEntries(CONTEST_KEYS.map(k => [k, MAP.contests[k].short])), { both: 'All of them' });   // 'both' is the saved value for every contest, kept from when there were two
const REASONS = [
  ['read', "I didn't understand the question"],
  ['start', "I didn't know how to start"],
  ['slip', 'I knew the method but made a mistake'],
  ['guess', 'I guessed'],
];
const REASON_TEXT = Object.fromEntries(REASONS);
const THEMES = ['a swim meet', 'a school bake sale', 'a space station', 'a soccer tournament', 'a pet shelter', 'a train journey', 'a video game shop', 'a garden', 'a library', 'a pizza party', 'a robot workshop', 'a camping trip', 'a board game', 'a science fair'];
const LETTERS = 'ABCDE';
const LS = 'mct-state-v1';

const $ = id => document.getElementById(id);
function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const k in (attrs || {})) {
    const v = attrs[k];
    if (v == null || v === false) continue;
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (v === true) e.setAttribute(k, '');
    else e.setAttribute(k, v);
  }
  for (const c of kids.flat()) {
    if (c == null || c === false) continue;
    e.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return e;
}
const clone = o => JSON.parse(JSON.stringify(o));

