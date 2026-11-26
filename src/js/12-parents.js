/* ---------- parents: add topics beyond the built-in skill map ---------- */
let removing = null;
function addTopic(ev) {
  ev.preventDefault();
  const name = $('pt-name').value.trim().slice(0, 60), note = $('pt-note').value.trim().slice(0, 400), group = $('pt-group').value;
  const contests = CONTEST_KEYS.filter(c => $('pt-' + c).checked);
  const err = !name ? 'Give the topic a name.'
    : !contests.length ? 'Tick at least one contest.'
    : allSkills().some(s => s.name.toLowerCase() === name.toLowerCase()) ? 'There is already a topic called "' + name + '".'
    : (S.custom || []).length >= MAX_ADDED ? 'You can add up to ' + MAX_ADDED + ' topics. Remove one first.' : '';
  if (err) { const e = $('pt-error'); e.textContent = err; e.hidden = false; return; }
  S.custom = (S.custom || []).concat({ id: 'custom.' + Date.now().toString(36), name, topic: TOPIC[group] ? group : 'custom', contests, prerequisites: [], note });
  syncCustom(); saveState(); render();
}
function removeTopic(id) {
  S.custom = (S.custom || []).filter(s => s.id !== id);
  delete S.skills[id];
  const q = S.placement.queue, at = q.indexOf(id);
  if (at >= 0) { q.splice(at, 1); if (at < S.placement.i) S.placement.i--; if (S.contest && S.placement.i >= q.length) S.placement.done = true; }
  for (const k of ['planned', 'retry', 'last']) if (S[k] === id) S[k] = null;
  if (cur && cur.target && cur.target.skill === id) { if (cur.ctl) cur.ctl.abort(); cur = null; }
  removing = null;
  syncCustom(); saveState(); render();
}
function viewParents() {
  if (!env.ready) return [h('div', { class: 'sheet' }, busyLine('Loading your progress'))];
  const mine = S.custom || [];
  const form = h('form', { class: 'sheet', onsubmit: addTopic },
    h('h2', null, 'Add a topic'),
    h('p', { class: 'muted' }, 'For parents. Add anything the built-in list misses. Problems for it are written the same way as the built-in topics. It starts at level 3 and moves up or down as he answers.'),
    h('div', { class: 'field' }, h('label', { for: 'pt-name' }, 'Topic name'),
      h('input', { type: 'text', id: 'pt-name', maxlength: 60, autocomplete: 'off', placeholder: 'Ratios and proportions' })),
    h('div', { class: 'field' }, h('label', { for: 'pt-note' }, 'What should the problems cover?'),
      h('textarea', { id: 'pt-note', rows: 3, maxlength: 400, placeholder: 'Sharing in a ratio, scaling a recipe, simple proportion word problems' })),
    h('div', { class: 'field' }, h('label', { for: 'pt-group' }, 'Show it under'),
      h('select', { id: 'pt-group' }, TOPICS.map(t => h('option', { value: t.id, selected: t.id === 'custom' }, t.name)))),
    h('fieldset', null, h('legend', null, 'Use it for'),
      CONTEST_KEYS.map(k => h('label', { class: 'check' }, h('input', { type: 'checkbox', id: 'pt-' + k, checked: true }), CONTESTS[k]))),
    h('p', { class: 'err', id: 'pt-error', role: 'alert', hidden: true }),
    h('div', { class: 'row' }, h('button', { class: 'btn primary', type: 'submit' }, 'Add topic')));
  const list = h('div', { class: 'sheet' }, h('h3', null, 'Topics you added'),
    mine.length ? h('div', null, mine.map(s => {
      const st = S.skills[s.id];
      return h('div', { class: 'added' },
        h('div', null, h('strong', null, s.name),
          h('div', { class: 'muted small' }, TOPIC[s.topic] + ', ' + s.contests.map(c => CONTESTS[c]).join(', ') + (st && st.n ? ', level ' + st.level + ', ' + st.ok + ' of ' + st.n + ' right' : ', not tried yet')),
          s.note ? h('div', { class: 'small' }, s.note) : null),
        removing === s.id
          ? h('div', { class: 'row' }, h('span', null, 'Remove it and its progress?'),
              h('button', { class: 'btn', type: 'button', onclick: () => removeTopic(s.id) }, 'Remove topic'),
              h('button', { class: 'btn quiet', type: 'button', onclick: () => { removing = null; render(); } }, 'Keep it'))
          : h('button', { class: 'btn quiet', type: 'button', onclick: () => { removing = s.id; render(); } }, 'Remove'));
    })) : h('p', { class: 'muted' }, 'None yet. A topic you add shows up here, in Progress, and in his practice within a few problems.'));
  const check = h('div', { class: 'sheet' }, h('h3', null, 'Problem writing'),
    h('div', { class: 'field' }, h('label', { for: 'pt-tier' }, 'Which Claude writes the problems'),
      h('select', { id: 'pt-tier', onchange: ev => { S.tier = ev.target.value === 'default' ? 'default' : 'quick'; dropPrepared(); saveState(); render(); } },
        h('option', { value: 'quick', selected: writerTier() === 'quick' }, 'Fast (the small, quick model)'),
        h('option', { value: 'default', selected: writerTier() === 'default' }, 'Careful (the standard model, slower)'))),
    h('p', { class: 'muted small' }, writerTier() === 'quick'
      ? 'Fast. Problems appear in seconds and use less of your Claude usage. The small model makes more mistakes, so wrong answer keys are more likely, especially on harder levels.'
      : 'Careful. Problems take longer and use more of your Claude usage, with fewer mistakes.'),
    h('label', { class: 'check' }, h('input', { type: 'checkbox', id: 'pt-verify', checked: !!S.verify, onchange: ev => { S.verify = ev.target.checked; dropPrepared(); saveState(); render(); } }), 'Solve each problem a second time before showing it'),
    h('p', { class: 'muted small' }, S.verify
      ? 'On. A problem is shown only when a second, independent solution agrees with its answer. Slower, and some problems are thrown away and rewritten.'
      : 'Off. Problems appear sooner and are never thrown away, but now and then one may have a wrong answer key. The tutor is told the key is unchecked and to say so if it finds a mistake.'));
  const setGoal = (key, lo, hi) => ev => { const v = Math.round(Number(ev.target.value)); S.goals = Object.assign({}, goals(), { [key]: Math.max(lo, Math.min(hi, v || lo)) }); saveState(); render(); };
  const goal = h('div', { class: 'sheet' }, h('h3', null, 'Goals'),
    h('div', { class: 'row' },
      h('div', { class: 'field' }, h('label', { for: 'pt-day' }, 'Problems a day'), h('input', { type: 'text', inputmode: 'numeric', id: 'pt-day', value: goals().day, onchange: setGoal('day', 3, 30) })),
      h('div', { class: 'field' }, h('label', { for: 'pt-week' }, 'Problems a week'), h('input', { type: 'text', inputmode: 'numeric', id: 'pt-week', value: goals().week, onchange: setGoal('week', 10, 200) }))),
    h('p', { class: 'muted small' }, 'The daily goal is the size of "today\'s set" on his Home screen. Reaching it does not stop him practicing. Daily goal 3 to 30, weekly goal 10 to 200.'));
  return [form, list, goal, check];
}

