/* ---------- views ---------- */
function levelDots(n) { return h('span', { class: 'lv', role: 'img', 'aria-label': 'Level ' + n + ' of 5' }, [1, 2, 3, 4, 5].map(i => h('i', { class: i <= n ? 'on' : '' }))); }
function busyLine(t) { return h('p', null, h('span', { class: 'dots' }, h('i'), h('i'), h('i')), t); }

function chooseTopic(id) {
  S.focus = id && (TOPIC[id] || SK[id]) ? id : null;
  S.planned = null; S.retry = null;
  dropPrepared();                    // problems prepared for the old choice are no longer wanted
  saveState();
  if (cur && !(cur.p && cur.checked)) { if (cur.ctl) cur.ctl.abort(); loadProblem(); }   // swap an unanswered problem right away
  else render();                     // an answered one stays up; the choice applies from the next problem
}
function switchContest(key) {        // change what he is training for without losing progress on any skill
  if (!CONTESTS[key] || key === S.contest) return;
  const placed = S.placement.done;
  chooseContest(key);                // sets the contest and builds a placement for it
  if (placed) S.placement.done = true;         // already placed once: skills new to him simply start at level 3
  S.focus = null; S.planned = null; S.retry = null;
  dropPrepared();
  if (live) live.abort();
  if (cur && cur.ctl) cur.ctl.abort();
  cur = null;
  saveState(); render();
}
function topicPicker() {
  const inPlay = contestSkills();
  return h('div', { class: 'pick' },
    h('label', { for: 'contest-pick' }, 'Training for'),
    h('select', { id: 'contest-pick', onchange: ev => switchContest(ev.target.value) }, Object.keys(CONTESTS).map(k => h('option', { value: k, selected: S.contest === k }, CONTESTS[k]))),
    h('label', { for: 'topic-pick' }, 'What to practice'),
    h('select', { id: 'topic-pick', onchange: ev => chooseTopic(ev.target.value) },
      h('option', { value: '', selected: !S.focus }, 'A mix of everything'),
      TOPICS.filter(tp => inPlay.some(x => x.topic === tp.id)).map(tp => h('optgroup', { label: tp.name },
        h('option', { value: tp.id, selected: S.focus === tp.id }, 'All of ' + tp.name),
        inPlay.filter(x => x.topic === tp.id).map(x => h('option', { value: x.id, selected: S.focus === x.id }, x.name))))));
}
function viewPractice() {
  if (env.ready && S.contest) focusSkills();        // drop a chosen topic that no longer has skills
  const body = viewPracticeBody();
  if (!(env.ready && S.contest && env.sample)) return body;
  return cur && cur.p ? [topicPicker(), withPad(cur.p, ...body)] : [topicPicker(), ...body];
}
function progressLine(c, t) {        // where he is in the placement, or in today's set
  if (t.mode === 'placement') {
    const i = S.placement.i, total = S.placement.queue.length;
    return h('div', { class: 'setline' }, h('b', null, 'Problem ' + (i + 1) + ' of ' + total), setBar(c.checked ? i + 1 : i, total, c.checked ? -1 : i));
  }
  const goal = goals().day, done = doneToday(), number = c.checked ? done : done + 1;      // an answered problem is already in the tally
  if (number > goal) return h('div', { class: 'setline' }, h('b', null, "Today's set is done"), h('span', { class: 'muted' }, 'Extra practice, problem ' + number + ' today'));
  return h('div', { class: 'setline' }, h('b', null, 'Problem ' + number + ' of ' + goal + ' today'), setBar(done, goal, c.checked ? -1 : done));
}
function viewPracticeBody() {
  if (!env.ready) return [h('div', { class: 'sheet' }, busyLine('Loading your progress'))];
  if (!S.contest) return [h('div', { class: 'sheet' },
    h('h2', null, 'Which contest are you training for?'),
    h('p', { class: 'muted' }, 'You start with a few medium problems, one per topic. After that, every skill moves up or down on its own as you answer.'),
    h('div', { class: 'row' }, Object.keys(CONTESTS).map(k => h('button', { class: 'btn', type: 'button', onclick: () => chooseContest(k) }, CONTESTS[k]))))];
  if (!env.sample) return [h('div', { class: 'sheet' }, h('h2', null, 'Open this page in Claude to practice'), h('p', { class: 'muted' }, 'Problems and tutor replies are written by Claude, which is not available in this view.'))];
  if (!cur && S.focus) return [h('div', { class: 'sheet' },
    h('h2', null, SK[S.focus] ? SK[S.focus].name : TOPIC[S.focus]),
    h('p', { class: 'muted' }, SK[S.focus] ? 'Problems on this one skill only. It still moves up or down as you answer. Switch back to a mix whenever you like.' : 'Problems from this topic only. Each skill in it still moves up or down as you answer. Switch back to a mix whenever you like.'),
    h('div', { class: 'row' }, h('button', { class: 'btn primary', type: 'button', onclick: loadProblem }, 'Start')))];
  if (!cur) {
    const pl = S.placement, fresh = !pl.done && pl.i === 0;
    return [h('div', { class: 'sheet' },
      h('h2', null, fresh ? 'First, ' + pl.queue.length + ' problems to find your level' : pl.done ? 'Ready for more?' : 'Finish finding your level'),
      h('p', { class: 'muted' }, fresh ? 'One medium problem from each topic. No timer. Each problem is written fresh' + (S.verify ? ' and its answer is checked before you see it' : '') + ', so the first one can take up to a minute.' : pl.done ? 'Pick up where you left off. ' + CONTESTS[S.contest] + '.' : (pl.queue.length - pl.i) + ' placement problems left.'),
      h('div', { class: 'row' }, h('button', { class: 'btn primary', type: 'button', onclick: loadProblem }, fresh ? 'Start' : 'Continue')))];
  }
  const t = cur.target, sk = SK[t.skill];
  const meta = h('div', { class: 'meta' },
    h('span', { class: 'skill' }, sk.name), levelDots(t.level),
    h('span', null, t.mode === 'placement' ? 'Finding your level'
      : 'Level ' + t.level + ((S.contest === 'kangaroo' || S.contest === 'both') && sk.contests.includes('kangaroo') ? ', about a ' + (t.level <= 2 ? 3 : t.level <= 4 ? 4 : 5) + '-point Kangaroo question' : '')),
    t.mode === 'retry' ? h('span', null, 'A similar one to try again') : null);
  if (cur.loading) return [h('div', { class: 'sheet' }, meta,
    h('p', null, h('span', { class: 'dots' }, h('i'), h('i'), h('i')), h('span', { id: 'wait-line' }, waitText())),
    h('p', { class: 'muted small' }, S.verify ? 'Each problem is written, then solved a second time to check the answer. That usually takes under a minute, and longer for problems with figures.' : 'Each problem is written fresh. That usually takes under a minute, and longer for problems with figures.'),
    h('div', { class: 'row', id: 'wait-again', hidden: Date.now() - cur.since < 45000 },
      h('span', null, 'Taking a while?'), h('button', { class: 'btn quiet', type: 'button', onclick: loadProblem }, 'Start this one again')))];
  if (cur.error) return [h('div', { class: 'sheet' }, meta, h('p', null, cur.error),
    cur.swapped ? h('p', null, 'The next try uses a different skill from the same topic.') : null,
    cur.why && cur.why.length ? h('p', { class: 'muted small' }, 'For a grown-up: ' + cur.why.map((w, i) => 'draft ' + (i + 1) + ', ' + w).join('; ') + '.') : null,
    h('div', { class: 'row' }, h('button', { class: 'btn primary', type: 'button', onclick: loadProblem }, 'Try again')))];

  const c = cur, p = c.p, st = skillState(t.skill);
  const missed = c.checked && !c.correct ? [c.picked].concat(c.missed || []) : [];     // every choice he has tried and got wrong
  const showRight = c.checked && (c.correct || c.revealed || c.fixed);
  const open = !c.checked || c.retrying;
  const canRetry = c.checked && !c.correct && !c.fixed && !c.revealed && !c.retrying && missed.length < p.choices.length - 1;
  const choices = h('div', { role: 'group', 'aria-label': 'Answer choices' }, p.choices.map((txt, i) => {
    const right = showRight && i === p.answer, wrong = missed.includes(i);
    return h('button', { class: 'choice' + (p.choice_figures ? ' pic' : '') + (right ? ' right' : wrong ? ' wrong' : ''), type: 'button', disabled: !open || wrong, 'aria-pressed': open && (c.retrying ? c.pick2 : c.picked) === i ? 'true' : 'false', onclick: () => { if (c.retrying) c.pick2 = i; else c.picked = i; render(); } },
      h('b', null, LETTERS[i]), h('span', null, p.choice_figures ? figureEl(p.choice_figures[i], true) : txt), right ? h('em', null, 'Correct') : wrong ? h('em', null, missed.length > 1 ? 'Tried' : 'Your answer') : null);
  }));
  const out = [progressLine(c, t), meta];
  if (placedNote && t.mode !== 'placement') out.push(h('p', { class: 'notice' }, 'Placement done. From here each skill adjusts on its own.'));
  out.push(h('div', null, h('p', { class: 'question' }, p.question), canSpeak ? h('button', { class: 'say', type: 'button', onclick: () => speak(p.question + '. ' + p.choices.map((x, i) => LETTERS[i] + ': ' + x).join('. ')) }, 'Read this aloud') : null));
  if (p.figure) out.push(figureEl(p.figure));
  out.push(choices);
  for (let i = 0; i < c.hints; i++) out.push(h('p', { class: 'hint' }, 'Hint ' + (i + 1) + ': ' + p.hints[i]));
  if (!c.checked) {
    out.push(h('div', { class: 'row' },
      h('button', { class: 'btn primary', type: 'button', disabled: c.picked == null, onclick: check }, 'Check answer'),
      c.hints < p.hints.length ? h('button', { class: 'btn quiet', type: 'button', onclick: () => { c.hints++; render(); } }, c.hints ? 'Another hint' : 'Show a hint') : null));
  } else {
    const moved = st.level - c.before.level;
    out.push(h('hr'));
    out.push(h('p', { class: 'verdict ' + (c.correct || c.fixed ? 'good' : 'bad') }, c.correct ? 'Correct' : c.fixed ? 'Correct on try ' + (missed.length + 1) : c.retrying ? 'Pick another answer' : 'Not this one'));
    if (c.retrying) {                 // a second go at the same question; the first answer is the one that counts for his level
      out.push(h('div', { class: 'row' },
        h('button', { class: 'btn primary', type: 'button', disabled: c.pick2 == null, onclick: checkRetry }, 'Check answer'),
        h('button', { class: 'btn quiet', type: 'button', onclick: () => { c.retrying = false; c.pick2 = null; render(); } }, 'Stop trying')));
      out.push(chatBlock(c));
      return [h('div', { class: 'sheet' }, out)];
    }
    if (moved && t.mode !== 'placement') out.push(h('p', null, moved > 0 ? 'Two in a row. This skill moves up to level ' + st.level + '.' : 'This skill drops to level ' + st.level + ' for now, to rebuild it.'));
    if (c.correct) {
      out.push(h('div', { class: 'row' },
        h('button', { class: 'btn quiet', type: 'button', 'aria-pressed': c.reason === 'guess' ? 'true' : 'false', onclick: () => setFeedback({ reason: c.reason === 'guess' ? null : 'guess' }) }, 'I guessed this one'),
        !c.revealed ? h('button', { class: 'btn quiet', type: 'button', onclick: () => { c.revealed = true; render(); } }, 'Show the solution') : null));
    } else {
      out.push(h('div', { class: 'stack' }, h('h3', null, 'What happened?'),
        h('div', { class: 'row' }, REASONS.map(([k, label]) => h('button', { class: 'btn quiet', type: 'button', 'aria-pressed': c.reason === k ? 'true' : 'false', onclick: () => setFeedback({ reason: k }) }, label))),
        h('div', { class: 'row' }, h('input', { type: 'text', id: 'note', value: c.note, placeholder: 'Anything else? (optional)', 'aria-label': 'What was hard about it', onchange: ev => setFeedback({ note: ev.target.value.slice(0, 300) }) }))));
      out.push(h('div', { class: 'row' },
        canRetry ? h('button', { class: 'btn', type: 'button', onclick: () => { c.retrying = true; c.pick2 = null; render(); } }, 'Try this one again') : null,
        h('button', { class: 'btn', type: 'button', disabled: c.busy, onclick: () => { c.chatOpen = true; render(); tutorSend('I picked ' + LETTERS[c.picked] + ' and it was wrong.' + (c.reason ? ' ' + REASON_TEXT[c.reason] + '.' : '') + ' Help me work it out, one step at a time.', true); } }, 'Work through it with the tutor'),
        !c.revealed ? h('button', { class: 'btn quiet', type: 'button', onclick: () => { c.revealed = true; render(); } }, 'Show the solution') : null));
    }
    if (c.revealed) out.push(h('p', { class: 'solution' }, p.solution));
    const wrongNow = !c.correct || c.reason === 'guess';
    out.push(h('div', { class: 'row' }, h('button', { class: 'btn primary', type: 'button', onclick: advance }, t.mode === 'practice' && wrongNow ? 'Try a similar one' : 'Next problem')));
  }
  out.push(chatBlock(c));
  return [h('div', { class: 'sheet' }, out)];
}

