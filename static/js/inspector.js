// static/js/inspector.js — local diagnostic inspector opened with /inspector
import sessionModule from './sessions.js';

const API_BASE = '';
let state = { traces: [], trace: null, tab: 'prompt' };

function esc(s) {
  return String(s ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}
function fmtTime(ts) {
  if (!ts) return '—';
  try { return new Date(ts * 1000).toLocaleTimeString(); } catch { return '—'; }
}
function kv(k, v) { return `<div class="insp-kv"><span>${esc(k)}</span><b>${esc(v ?? '—')}</b></div>`; }
function chips(items) {
  const arr = (items || []).filter(Boolean);
  if (!arr.length) return '<span class="insp-muted">none</span>';
  return arr.map(x => `<span class="insp-chip">${esc(x)}</span>`).join('');
}
function tokens(n) { return (n === 0 || n) ? Number(n).toLocaleString() : '—'; }

function ensureStyles() {
  if (document.getElementById('inspector-styles')) return;
  const s = document.createElement('style');
  s.id = 'inspector-styles';
  s.textContent = `
#inspector-modal .modal-content{width:min(980px,94vw);height:min(760px,92vh);background:var(--bg);display:flex;flex-direction:column;overflow:hidden}
.inspector-body{display:flex;flex-direction:column;gap:12px;height:100%;overflow:hidden;padding:12px 14px 14px}
.insp-top{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.insp-select{background:var(--input-bg,var(--bg));color:var(--fg);border:1px solid var(--border);border-radius:8px;padding:7px 9px;min-width:260px}.insp-btn{border:1px solid var(--border);background:var(--button-bg,transparent);color:var(--fg);border-radius:8px;padding:7px 10px;cursor:pointer}.insp-btn:hover{background:var(--hover-bg,rgba(127,127,127,.12))}
.insp-tabs{display:flex;gap:6px;border-bottom:1px solid var(--border);padding-bottom:8px}.insp-tab{border:0;background:transparent;color:var(--fg);opacity:.65;padding:7px 10px;border-radius:8px;cursor:pointer}.insp-tab.active{opacity:1;background:var(--accent-soft,rgba(127,127,127,.14))}
.insp-summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}.insp-card{border:1px solid var(--border);border-radius:12px;padding:10px;background:var(--card-bg,rgba(127,127,127,.05))}.insp-card small{display:block;opacity:.55;margin-bottom:4px}.insp-card b{font-size:1.05em}.insp-panel{overflow:auto;min-height:0;padding-right:2px}.insp-section{display:flex;flex-direction:column;gap:8px;margin-bottom:12px}.insp-row{border:1px solid var(--border);border-radius:12px;padding:10px;background:var(--card-bg,rgba(127,127,127,.045));display:grid;grid-template-columns:1.2fr .8fr .8fr .8fr auto;gap:8px;align-items:center}.insp-row-main{font-weight:600}.insp-muted{opacity:.55}.insp-kv{display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px solid color-mix(in srgb,var(--border),transparent 55%)}.insp-kv span{opacity:.62}.insp-kv b{text-align:right;font-weight:600}.insp-chip{display:inline-block;border:1px solid var(--border);border-radius:999px;padding:3px 8px;margin:2px;background:rgba(127,127,127,.06);font-size:.86em}.insp-popup{z-index:9999!important}.insp-popup .modal-content{width:min(1080px,96vw);height:min(820px,94vh);background:var(--bg);display:flex;flex-direction:column}.insp-pre{white-space:pre-wrap;word-break:break-word;overflow:auto;flex:1;margin:0;padding:14px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.86em;line-height:1.45;background:rgba(127,127,127,.045);border-top:1px solid var(--border)}
@media(max-width:700px){.insp-row{grid-template-columns:1fr}.insp-select{min-width:0;width:100%}}
`;
  document.head.appendChild(s);
}

function ensureModal() {
  ensureStyles();
  let modal = document.getElementById('inspector-modal');
  if (modal) return modal;
  modal = document.createElement('div');
  modal.id = 'inspector-modal';
  modal.className = 'modal hidden';
  modal.innerHTML = `<div class="modal-content" role="dialog" aria-label="Inspector">
    <div class="modal-header"><h3>Inspector</h3><button class="close-btn" id="inspector-close" aria-label="Close">✖</button></div>
    <div class="modal-body inspector-body"></div>
  </div>`;
  document.body.appendChild(modal);
  modal.querySelector('#inspector-close').addEventListener('click', () => modal.classList.add('hidden'));
  return modal;
}

async function fetchTraces() {
  const sid = sessionModule?.getCurrentSessionId?.() || '';
  const url = `${API_BASE}/api/inspector/traces?limit=30` + (sid ? `&session_id=${encodeURIComponent(sid)}` : '');
  const res = await fetch(url, { credentials: 'same-origin' });
  const data = await res.json();
  state.traces = data.traces || [];
  if (!state.trace && state.traces[0]) await fetchTrace(state.traces[0].trace_id);
}
async function fetchTrace(id) {
  if (!id) return;
  const res = await fetch(`${API_BASE}/api/inspector/traces/${encodeURIComponent(id)}`, { credentials: 'same-origin' });
  state.trace = await res.json();
}

function openText(title, text) {
  let modal = document.getElementById('inspector-content-popup');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'inspector-content-popup';
    modal.className = 'modal insp-popup hidden';
    modal.innerHTML = `<div class="modal-content" role="dialog" aria-label="Inspector content"><div class="modal-header"><h3></h3><button class="close-btn">✖</button></div><pre class="insp-pre"></pre></div>`;
    document.body.appendChild(modal);
    modal.querySelector('.close-btn').addEventListener('click', () => modal.classList.add('hidden'));
  }
  modal.querySelector('h3').textContent = title;
  modal.querySelector('pre').textContent = text || '(empty)';
  modal.classList.remove('hidden');
}

function fullPromptText() {
  const t = state.trace || {};
  const msgs = t.provider_messages || t.messages_after_context || [];
  if (msgs.length) return msgs.map(m => `--- ${m.index}. ${String(m.role || '').toUpperCase()} · ${tokens(m.tokens)} tokens ---\n${m.content || ''}`).join('\n\n');
  return (t.layers || []).map((l, i) => `--- ${i + 1}. ${l.name} [${l.role}] · ${tokens(l.tokens)} tokens ---\n${l.content || ''}`).join('\n\n');
}
function systemText() {
  const msgs = (state.trace?.provider_messages || state.trace?.messages_after_context || []).filter(m => m.role === 'system');
  if (msgs.length) return msgs.map((m, i) => `--- SYSTEM ${i + 1} · ${tokens(m.tokens)} tokens ---\n${m.content || ''}`).join('\n\n');
  return (state.trace?.layers || []).filter(l => l.role === 'system').map((l, i) => `--- ${l.name} · ${tokens(l.tokens)} tokens ---\n${l.content || ''}`).join('\n\n');
}
function providerText(kind='payload') {
  const p = state.trace?.provider_payload || {};
  const r = state.trace?.result || {};
  if (kind === 'messages') return (state.trace?.provider_messages || []).map(m => `--- ${m.index}. ${String(m.role).toUpperCase()} · ${tokens(m.tokens)} tokens ---\n${m.content || ''}`).join('\n\n');
  if (kind === 'tools') return (p.tool_names || state.trace?.tools?.sent_tool_names || []).join('\n') || '(no tools)';
  if (kind === 'response') return r.response || '(empty response)';
  if (kind === 'reasoning') return r.reasoning || '(empty reasoning)';
  try { return JSON.stringify(p.payload || p, null, 2); } catch { return String(p); }
}

function renderSummary(t) {
  const c = t.context || {}, tools = t.tools || {}, ep = t.endpoint || {}, p = t.provider_payload || {};
  return `<div class="insp-summary">
    <div class="insp-card"><small>Trace</small><b>${esc(t.label || t.trace_type || t.mode || '—')}</b></div>
    <div class="insp-card"><small>Model</small><b>${esc(ep.model || p.model || '—')}</b></div>
    <div class="insp-card"><small>Input tokens</small><b>${tokens(c.tokens_after_trim || c.tokens_after_compaction || c.tokens_before_compaction)} / ${tokens(c.context_length)}</b></div>
    <div class="insp-card"><small>Tools sent</small><b>${tokens(tools.schema_count ?? p.tools_count)}</b></div>
    <div class="insp-card"><small>Compacted</small><b>${c.compacted ? 'yes' : 'no'}</b></div>
    <div class="insp-card"><small>Trimmed</small><b>${c.trimmed ? 'yes' : 'no'}</b></div>
  </div>`;
}
function renderPrompt() {
  const layers = state.trace?.layers || [];
  return `<div class="insp-section"><div><button class="insp-btn" data-show="full">Show full prompt</button> <button class="insp-btn" data-show="system">Show system</button></div>
    ${layers.map(l => `<div class="insp-row"><div><div class="insp-row-main">${esc(l.name)}</div><div class="insp-muted">${esc(l.source || '')}</div></div><div>Role<br><b>${esc(l.role)}</b></div><div>Tokens<br><b>${tokens(l.tokens)}</b></div><div>Status<br><b>${esc(l.status || 'included')}</b></div><button class="insp-btn" data-layer="${esc(l.id)}">Show</button></div>`).join('') || '<div class="insp-muted">No prompt trace yet.</div>'}</div>`;
}
function renderTools() {
  const x = state.trace?.tools || {};
  return `<div class="insp-section">
    ${kv('Mode', state.trace?.mode)}${kv('Native schemas', x.native_tools_sent ? 'yes' : 'no')}${kv('Fenced prompt tools', x.fenced_prompt_used ? 'yes' : 'no')}${kv('Schema estimate', tokens(x.schema_tokens_est || x.schema_count))}
    <div><b>Disabled by UI/global</b><br>${chips(x.disabled_tools)}</div>
    <div><b>Relevant tools</b><br>${chips(x.relevant_tools)}</div>
    <div><b>Sent tools</b><br>${chips(x.sent_tool_names)}</div>
    <div><b>Tool events</b>${(x.events || []).map(e => `<div class="insp-card"><b>${esc(e.tool || e.type || 'event')}</b><div class="insp-muted">round ${esc(e.round ?? '')} · ${esc(e.command || '')} · exit ${esc(e.exit_code ?? '')}</div><div>${esc(e.output || e.message || e.status || '')}</div>${e.doc_id ? `<div class="insp-muted">doc: ${esc(e.doc_title || e.doc_id)}</div>` : ''}</div>`).join('') || '<div class="insp-muted">none</div>'}</div>
  </div>`;
}
function renderContext() {
  const c = state.trace?.context || {};
  return `<div class="insp-section">
    ${kv('Context length', tokens(c.context_length))}${kv('Before compaction', tokens(c.tokens_before_compaction))}${kv('Compaction ran', c.compacted ? 'yes' : 'no')}${kv('After compaction', tokens(c.tokens_after_compaction))}${kv('Before trim', tokens(c.tokens_before_trim))}${kv('After trim', tokens(c.tokens_after_trim))}${kv('Trimmed', c.trimmed ? 'yes' : 'no')}${kv('Messages after trim', c.messages_after_trim)}
    <div><b>Recent traces</b>${state.traces.map((tr, i) => `<div class="insp-card" data-trace-pick="${esc(tr.trace_id)}" style="cursor:pointer"><b>${i + 1}. ${esc(tr.label || tr.trace_type || tr.mode || 'chat')}</b> ${tr.internal ? '<span class="insp-chip">internal</span>' : ''} · ${tokens(tr.tokens)} / ${tokens(tr.context_length)} tokens · compacted ${tr.compacted ? 'yes' : 'no'} · trimmed ${tr.trimmed ? 'yes' : 'no'}<div class="insp-muted">${fmtTime(tr.created_at)} · ${esc(tr.model || '')}</div></div>`).join('')}</div>
  </div>`;
}
function renderProvider() {
  const p = state.trace?.provider_payload || {};
  return `<div class="insp-section">
    ${kv('Provider', p.provider)}${kv('Target URL', p.target_url)}${kv('Model', p.model)}${kv('Temperature', p.temperature)}${kv('Max tokens', p.max_tokens)}${kv('Stream', p.stream ? 'yes' : 'no')}${kv('Message count', p.message_count)}${kv('Tools', p.tools_count)}
    <div><button class="insp-btn" data-show="provider">Show provider prompt</button> <button class="insp-btn" data-show="messages">Show final messages</button> <button class="insp-btn" data-show="schemas">Show tool schemas</button></div>
  </div>`;
}
function renderRuntime() {
  const ep = state.trace?.endpoint || {}, p = state.trace?.provider_payload || {};
  const r = state.trace?.result || {};
  return `<div class="insp-section">${kv('Session', state.trace?.session_id)}${kv('Trace type', state.trace?.trace_type)}${kv('Label', state.trace?.label)}${kv('Parent trace', state.trace?.parent_trace_id)}${kv('Endpoint', ep.url || p.target_url)}${kv('Model', ep.model || p.model)}${kv('Created', fmtTime(state.trace?.created_at))}${kv('Status', state.trace?.status)}${kv('Response chars', r.response_chars)}${kv('Reasoning chars', r.reasoning_chars)}${kv('Result', r.title || r.message || r.reason || r.error || r.response_preview || '—')}<div><button class="insp-btn" data-show="response">Show response</button> <button class="insp-btn" data-show="reasoning">Show reasoning</button></div></div>`;
}

function render() {
  const modal = ensureModal();
  const body = modal.querySelector('.inspector-body');
  const t = state.trace;
  const tabs = [['prompt','Prompt Stack'],['tools','Tools'],['context','Compaction / Pruning'],['provider','Provider Payload'],['runtime','Runtime']];
  body.innerHTML = `<div class="insp-top"><select class="insp-select" id="insp-trace-select">${state.traces.map(tr => `<option value="${esc(tr.trace_id)}" ${t?.trace_id === tr.trace_id ? 'selected' : ''}>${fmtTime(tr.created_at)} · ${esc(tr.label || tr.trace_type || tr.mode || 'chat')} · ${esc(tr.model || '')}</option>`).join('')}</select><button class="insp-btn" id="insp-refresh">Refresh</button><button class="insp-btn" id="insp-clear">Clear traces</button></div>
    ${t ? renderSummary(t) : '<div class="insp-muted">No traces yet. Send a normal non-incognito message, then refresh.</div>'}
    <div class="insp-tabs">${tabs.map(([id,label]) => `<button class="insp-tab ${state.tab===id?'active':''}" data-tab="${id}">${label}</button>`).join('')}</div>
    <div class="insp-panel">${!t ? '' : state.tab === 'prompt' ? renderPrompt() : state.tab === 'tools' ? renderTools() : state.tab === 'context' ? renderContext() : state.tab === 'provider' ? renderProvider() : renderRuntime()}</div>`;

  body.querySelector('#insp-refresh')?.addEventListener('click', async () => { await fetchTraces(); render(); });
  body.querySelector('#insp-clear')?.addEventListener('click', async () => { await fetch('/api/inspector/traces', { method:'DELETE', credentials:'same-origin' }); state.trace=null; await fetchTraces(); render(); });
  body.querySelector('#insp-trace-select')?.addEventListener('change', async e => { await fetchTrace(e.target.value); render(); });
  body.querySelectorAll('[data-tab]').forEach(b => b.addEventListener('click', () => { state.tab = b.dataset.tab; render(); }));
  body.querySelectorAll('[data-layer]').forEach(b => b.addEventListener('click', () => { const l = (state.trace?.layers || []).find(x => x.id === b.dataset.layer); openText(l?.name || 'Layer', l?.content || ''); }));
  body.querySelectorAll('[data-show]').forEach(b => b.addEventListener('click', () => {
    const k = b.dataset.show;
    if (k === 'full') openText('Full prompt', fullPromptText());
    else if (k === 'system') openText('System prompt', systemText());
    else if (k === 'provider') openText('Provider prompt', providerText('payload'));
    else if (k === 'messages') openText('Final messages', providerText('messages'));
    else if (k === 'schemas') openText('Tool schemas', providerText('tools'));
    else if (k === 'response') openText('Model response', providerText('response'));
    else if (k === 'reasoning') openText('Model reasoning', providerText('reasoning'));
  }));
  body.querySelectorAll('[data-trace-pick]').forEach(el => el.addEventListener('click', async () => { await fetchTrace(el.dataset.tracePick); render(); }));
}

export async function open() {
  const modal = ensureModal();
  modal.classList.remove('hidden');
  await fetchTraces();
  render();
}

export default { open };
