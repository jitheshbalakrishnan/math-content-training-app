/* ---------- tutor ---------- */
function tutorRules(c) {
  const p = c.p;
  const status = !c.checked ? 'He has NOT answered yet. Never reveal the answer or which choice is right.'
    : c.correct ? 'He answered ' + LETTERS[c.picked] + ', which is correct.' + (c.reason === 'guess' ? ' He says he guessed.' : '')
    : 'He answered ' + LETTERS[c.picked] + ' ("' + p.choices[c.picked] + '"), which is wrong.' + ((c.missed || []).length ? ' He tried again and also missed with ' + c.missed.map(i => LETTERS[i]).join(', ') + '.' : '') + (c.fixed ? ' He then got it right on another try.' : '') + (c.reason ? ' He says: ' + REASON_TEXT[c.reason] + '.' : '') + (c.note ? ' His note: "' + c.note + '"' : '');
  return [
    'You are a patient math tutor for a grade 5-6 student practicing for math contests. Follow these rules in every reply.',
    '- Use simple words. Keep each reply under 80 words. Ask one question or give one step at a time.',
    '- Guide with questions and the smallest hint that unblocks him. First find out what he was thinking.',
    '- Do not state the final answer or the correct letter unless he has already answered the problem and either asks to see it or has made two real attempts in this chat.',
    '- If an explanation does not land, try a different one: smaller numbers, a picture described in words, or a real-life version.',
    '- Be encouraging and honest. Never tell him a wrong step is right.',
    p.checked ? '- The verified answer and solution below are the ground truth. Never give a different answer.'
      : '- The answer key below was NOT double-checked. Work the problem out yourself as you go. If the key is wrong, tell him plainly that the answer key has a mistake, show the correct answer, and tell him it was not his fault.',
    '- Plain text only: no Markdown, no LaTeX. Write fractions like 3/4.',
    '- Stay on math. If he goes off topic, bring him back kindly in one sentence.',
    'Skill: ' + SK[c.target.skill].name + ', level ' + c.target.level + ' of 5.',
    'Problem: ' + p.question,
    p.figure ? 'The figure he sees: ' + figText(p.figure) : '',
    'Choices: ' + p.choices.map((x, i) => LETTERS[i] + ') ' + (p.choice_figures ? figText(p.choice_figures[i]) : x)).join('; '),
    (p.checked ? 'Verified answer: ' : 'Answer key (not double-checked): ') + LETTERS[p.answer] + ') ' + p.choices[p.answer],
    (p.checked ? 'Verified solution: ' : 'Solution from the answer key (not double-checked): ') + p.solution,
    'Status: ' + status,
  ].filter(Boolean).join('\n');
}
async function tutorSend(text, hidden) {
  const c = cur;
  if (!c || c.busy || !text.trim()) return;
  c.chat.push({ role: 'user', content: text.trim(), hidden: !!hidden });
  const reply = { role: 'assistant', content: '', pending: true };
  const turns = [{ role: 'user', content: tutorRules(c) }].concat(c.chat.filter(m => m.content && !m.error).slice(-16).map(m => ({ role: m.role, content: m.content })));
  c.chat.push(reply); c.busy = true; c.ctl = new AbortController();
  let late = false;
  const timer = setTimeout(() => { late = true; c.ctl.abort(); }, CALL_LIMIT_MS);   // same limit as problem writing
  renderChat();
  try {
    const r = await env.sample(turns, { cache: false, modelTier: 'quick', signal: c.ctl.signal, onText: ({ text }) => { reply.content = text; reply.pending = false; if (cur === c) renderChat(); } });
    reply.content = r.text;
  } catch (e) {
    reply.content = (e && e.text) || '';
    if (late) reply.error = 'The tutor took too long to answer, so it was stopped. Ask again.';
    else if (!(e && e.code === 'cancelled')) reply.error = e && e.code === 'not_granted' ? "Claude isn't allowed on this page yet. Allow it from the page's Permissions menu." : e && e.code === 'rate_limited' ? 'Too many questions at once. Wait a minute, then ask again.' : "The tutor couldn't answer just now. Ask again.";
    if (!reply.content && !reply.error) c.chat.splice(c.chat.indexOf(reply), 1);
  }
  clearTimeout(timer);
  reply.pending = false; c.busy = false;
  if (cur === c) renderChat();
}
function speak(text) {
  try { speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(text); u.rate = 0.95; speechSynthesis.speak(u); } catch (e) {}
}
const canSpeak = 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;

function renderChat() {
  const log = $('chat-log'); if (!log || !cur) return;
  log.replaceChildren(...cur.chat.filter(m => !m.hidden).map(m => {
    if (m.pending) return h('div', { class: 'msg assistant' }, h('span', { class: 'dots' }, h('i'), h('i'), h('i')), 'Thinking');
    return h('div', { class: 'msg ' + m.role + (m.error && !m.content ? ' err' : '') }, m.content || m.error,
      m.content && m.error ? h('div', { class: 'small' }, m.error) : null,
      m.role === 'assistant' && m.content && canSpeak ? h('button', { class: 'say', type: 'button', onclick: () => speak(m.content) }, 'Read this aloud') : null);
  }));
  $('chat-send').hidden = !!cur.busy; $('chat-stop').hidden = !cur.busy;
}
function chatBlock(c) {
  if (!c.chatOpen) return h('div', { class: 'row' }, h('button', { class: 'btn quiet', type: 'button', onclick: () => { c.chatOpen = true; render(); const i = $('tutor-input'); if (i) i.focus(); } }, 'Ask the tutor'));
  return h('section', { class: 'stack', 'aria-label': 'Tutor' },
    h('hr'), h('h3', null, 'Tutor'),
    h('div', { class: 'log', id: 'chat-log', 'aria-live': 'polite' }),
    h('form', { class: 'row', onsubmit: ev => { ev.preventDefault(); const i = $('tutor-input'); const t = i.value; if (!t.trim() || c.busy) return; i.value = ''; tutorSend(t); } },
      h('input', { type: 'text', id: 'tutor-input', autocomplete: 'off', placeholder: 'Ask a question or show your first step', 'aria-label': 'Message to the tutor' }),
      h('button', { class: 'btn primary', id: 'chat-send', type: 'submit' }, 'Send'),
      h('button', { class: 'btn', id: 'chat-stop', type: 'button', hidden: true, onclick: () => c.ctl && c.ctl.abort() }, 'Stop')),
    h('p', { class: 'muted small' }, "To talk, tap the microphone key on your keyboard. The tutor won't give the answer away before you try."));
}

