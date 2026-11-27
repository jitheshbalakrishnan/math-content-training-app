/* ---------- running from the home computer: Claude calls go to the local server, which holds the key ---------- */
async function findLocalServer() {   // only when the page is not inside Claude and was served over http by our server
  if (window.claude || !/^https?:$/.test(location.protocol)) return null;
  try {
    const r = await fetch('/api/health', { cache: 'no-store' });
    const j = r.ok ? await r.json() : null;
    return j && j.ok ? j : null;
  } catch (e) { return null; }
}
function readJson(text) {            // a reply that should be only JSON, perhaps wrapped in a code fence or a sentence
  const t = String(text || '').trim().replace(/^```(?:json)?\s*/i, '').replace(/```\s*$/, '').trim();
  try { return JSON.parse(t); } catch (e) {}
  const a = t.indexOf('{'), b = t.lastIndexOf('}');
  if (a >= 0 && b > a) { try { return JSON.parse(t.slice(a, b + 1)); } catch (e) {} }
  return undefined;
}
function localSample() {             // the same shape as Claude's page capability: sample(turns, opts) and sample.json(prompt, opts)
  const post = async (agent, messages, opts) => {
    let r;
    try {
      r = await fetch('/api/claude', { method: 'POST', headers: { 'content-type': 'application/json' }, signal: opts.signal,
        body: JSON.stringify({ agent, messages, tier: opts.modelTier === 'default' ? 'default' : 'quick' }) });
    } catch (e) { throw { code: e && e.name === 'AbortError' ? 'cancelled' : 'offline' }; }
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw { code: j.code || 'unavailable' };
    return String(j.text || '');
  };
  const sample = async (turns, opts = {}) => {
    const text = await post(opts.agent || 'tutor', turns, opts);
    if (opts.onText) opts.onText({ text });
    return { text };
  };
  sample.json = async (prompt, opts = {}) => {
    const data = readJson(await post(opts.agent || 'writer', [{ role: 'user', content: prompt }], opts));
    if (data === undefined || data === null || typeof data !== 'object') throw { code: 'invalid_json' };
    return data;
  };
  return sample;
}
async function localChildName() {    // the child's first name from the database (the first child, until there is a picker)
  try { const r = await fetch('/api/children', { cache: 'no-store' }); const list = r.ok ? await r.json() : []; return (list[0] && list[0].first_name) || ''; }
  catch (e) { return ''; }
}
function withAgent(opts, agent) { return env.local ? Object.assign(opts, { agent }) : opts; }   // Claude's own page does not take this option
