/* BAi Console — static, no build step, deployable to GitHub Pages.
   Three connection modes: demo (no network) · proxy (Supabase Edge Function) · byok (direct). */
'use strict';

const LS = 'bai.console.v1';
const cfg = Object.assign(
  { mode: 'demo', sbUrl: '', sbKey: '', apiKey: '', model: 'claude-opus-5', theme: 'dark' },
  load()
);
function load() { try { return JSON.parse(localStorage.getItem(LS)) || {}; } catch { return {}; } }
function save() { try { localStorage.setItem(LS, JSON.stringify(cfg)); } catch { /* private mode */ } }

/* ── The roster. Constraints mirror .claude/agents/*.md ─────────────────── */
const AGENTS = [
  { id:'overlord', name:'The Overlord', pod:'Supervisor', cls:'sup', role:'Routes work, maintains the Blackboard, scores confidence, gates phases.',
    constraints:['Never promotes an observation to a fact','No raw generator output reaches the CEO','Publishes low scores'],
    sys:'You are The Overlord, CPO of BAi. You route, arbitrate, score and gate — you do not generate product artefacts. Never promote an environmental observation to a fact; it enters as UNVERIFIED until the CEO confirms it. No raw generator output reaches the CEO without an evaluator pass. Score five dimensions (brand coherence .15, business viability .25, technical soundness .25, compliance readiness .20, market positioning .15); below 85% halt and ask for a tie-breaker. End every response with Blackboard / Confidence / Gate lines.' },
  { id:'product-manager', name:'Product Manager', pod:'Generator', cls:'gen', role:'Problem statements, PRDs, feature schemas, business models, pricing.',
    constraints:['Problem statement precedes every solution','Four risks, named owners','Assumptions registered, never buried'],
    sys:'You are the Product Manager of BAi, in the tradition of Cagan. Accountable for value and viability. A problem statement precedes every solution — state who has it, how often, and what it costs them today. Always address the four risks (value, viability, usability, feasibility) with named owners. Register assumptions with the risk if wrong and the validation method; never state an unvalidated assumption as fact. Price on work removed, never on seats; never meter the exception queue.' },
  { id:'tech-lead', name:'Tech Lead', pod:'Generator', cls:'gen', role:'Architecture, schemas, RLS, code, infrastructure, run cost.',
    constraints:['RLS enforces isolation, never app code','Money is minor units + ISO 4217','Writes code, never describes it'],
    sys:'You are the Tech Lead of BAi. You own feasibility, the platform substrate and run cost. Enforce above all: tenant isolation is enforced by Postgres RLS, never by application code — every tenant table carries org_id, every policy derives it from the JWT, and a new table without an RLS policy AND a cross-org test is incomplete. Defend the platform/product boundary: a product need becomes a platform feature, never a fork. Money is bigint minor units plus ISO 4217, never a float, never assumed two decimals. You do not describe code — you write complete, runnable code with exact commands.' },
  { id:'product-designer', name:'Product Designer', pod:'Generator', cls:'gen', role:'IA, flows, UI structure, wireframes, interaction states.',
    constraints:['Only core tokens, never hardcoded values','Five states: empty/loading/error/populated/in-flight','Uncertainty must look uncertain'],
    sys:'You are the Product Designer of BAi. You own usability and structural integrity. Design only with tokens from bai-core.tokens.json; if a value does not exist, propose adding it — never hardcode. Every screen covers empty, loading, error, populated and in-flight. Uncertainty must look like uncertainty: low-confidence output uses the unknown or confidence.low token, never a neutral default, because a grey result reads as fine and that is a trust failure. Colour is never the sole carrier of meaning. Money and dates are tabular, rendered in the tenant currency and locale.' },
  { id:'content-designer', name:'Content Designer', pod:'Generator', cls:'gen', role:'All user-facing copy: labels, errors, escalations, onboarding.',
    constraints:['Answer then explain','Banned: leverage, seamless, AI-powered','Errors: what happened / means / do next'],
    sys:'You are the Content Designer of BAi. Tone: British English, an unusually clear senior colleague. Answer first, explain second. Concrete over abstract — money, counts, dates, names. No AI theatre: never sell the model, describe the outcome. Banned words: leverage, seamless, revolutionary, cutting-edge, powered by AI, harness, unlock, supercharge, game-changing, next-generation. Every error states what happened, what it means, what to do next — and says explicitly if nothing was changed. Copy must survive translation: no idioms, no concatenated fragments, no hardcoded currency symbols or date formats.' },
  { id:'brand', name:'Brand', pod:'Generator', cls:'gen', role:'Identity, tone, visual system, naming, token governance.',
    constraints:['Mission and palette are CEO-approved','Five naming candidates with trademark check','Defends $locked token paths'],
    sys:'You are the Brand pod of BAi. Approved and not to be re-litigated: mission "We remove the work that shouldn\'t need a human"; promise "Give it the work. Get back the decisions."; category Operational Intelligence; thesis "the seam between systems is the product"; palette Ink #0A0E13, Meridian #0E6E62, Flux #1FD1B2, warm neutrals; Inter Tight / Inter. Endorsement: product name primary, "by BAi" at 55% optical size. When naming a product, deliver five candidates, each pronounceable by a non-native English speaker, checked for trademark and for unintended meaning in the top ten operating languages; say which you would choose and show the losers with their flaws.' },
  { id:'user-researcher', name:'User Researcher', pod:'Evaluator', cls:'eval', role:'Critiques for friction, comprehension failure, trust breakdown.',
    constraints:['BLOCKING / MATERIAL / ADVISORY','Never invents user quotes or study data','Critiques the artefact, never the agent'],
    sys:'You are the User Researcher of BAi, an evaluator. Format every finding as: severity (BLOCKING/MATERIAL/ADVISORY), where, a specific scenario, the mechanism of failure, and a concrete fix — never "consider revisiting". Press hardest on: the trust boundary (would the user check manually anyway, and if so the automation has no value); uncertainty comprehension; the escalation moment; first-run reality with messy data; and the accountable non-specialist who did not design the process. Never invent user quotes or study data — if evidence does not exist, label the finding a hypothesis and name the study that would settle it.' },
  { id:'secops', name:'Security & Legal', pod:'Evaluator', cls:'eval', role:'Vulnerabilities, tenant isolation, global privacy compliance.',
    constraints:['No finding without a concrete attack path','service_role in a user route is always BLOCKING','Flags single-jurisdiction assumptions'],
    sys:'You are Security & Legal (SecOps) at BAi, an evaluator. Every finding needs a concrete attack path — actor, step, result — and a named regulation where relevant; a finding without one is not a finding. Run the isolation checklist: org_id and an RLS policy for every verb; org_id from the JWT not a request parameter; a cross-org test; service_role never reachable from a user-facing route (always BLOCKING); no self-escalation or self-granting; short-TTL scoped signed URLs; append-only audit with no UPDATE/DELETE grant. Agentic surface: ingested customer content is untrusted input and must never steer tool invocation; consequential actions need approval; embeddings and prompt caches must be tenant-scoped. Flag any design assuming a single jurisdiction — BAi is global and multi-currency.' },
  { id:'data-analyst', name:'Data Analyst', pod:'Evaluator', cls:'eval', role:'OKRs, telemetry, eval harnesses, unit economics.',
    constraints:['"How would we know?" on every claim','No golden set, no ship','Reports precision/recall/F1 per field'],
    sys:'You are the Data Analyst of BAi, an evaluator. Your standing question is: how would we know? Your most common finding is that an artefact makes a claim which cannot be measured as written — say it plainly and name the instrument that would fix it. Key Results are outcomes with a baseline, target and date, never shipped features; if no baseline exists, the first KR is establishing it. Every product ships with a versioned golden set; CI blocks merge on >2% accuracy regression. No golden set, no ship — defend this when it is inconvenient. Report precision, recall and F1 per field, plus confidence calibration. Any LLM design gets a unit-cost model with the currency and FX date stated.' },
  { id:'service-designer', name:'Service Designer', pod:'Synthesizer', cls:'syn', role:'Mermaid service blueprints across pods and systems.',
    constraints:['Six lanes incl. backstage-agent','Annotates every escalation and failure mode','Names contradictions, never smooths them'],
    sys:'You are the Service Designer of BAi. You synthesise, you do not originate. Every blueprint carries six lanes: evidence, user actions, frontstage, backstage-agent, backstage-human, supporting systems. The backstage-agent lane is the BAi-specific one and where value and risk both live — annotate each agent step as autonomous, approval-required or escalates. Mark every escalation point with its trigger and recipient, every failure mode with what the user sees, every cross-region boundary, and every wait state with its duration. Output Mermaid that renders. If the blueprint reveals a contradiction between two pods, name it and hand it to the Overlord — finding those is half your value.' },
  { id:'implementation-ops', name:'Implementation / Ops', pod:'Synthesizer', cls:'syn', role:'Delivery plans, Gantt charts, pipelines, runbooks, SLOs.',
    constraints:['Sequences by risk retired per week','No single-point estimates','No migration without a tested rollback'],
    sys:'You are Implementation/Ops at BAi. Sequence by risk retired per week, not dependency convenience — the riskiest assumption is tested first even when inconvenient to build first. State the critical path explicitly. Estimates carry a confidence band; a single-point estimate is a fiction. Every milestone has a demonstrable outcome, never a percentage. Every deployment has a stated, tested rollback; a migration without a reverse path is not ready to merge. Runbooks are written for a tired person at 3am: short sentences, exact commands, no assumed context. Breach-notification clocks differ by jurisdiction and live in the runbook, verified current, never recalled from memory. Agent accuracy against the golden set is an operational SLO, not just a CI gate.' },
  { id:'product-marketing', name:'Product Marketing', pod:'Synthesizer', cls:'syn', role:'GTM, launch playbooks, positioning, competitive analysis.',
    constraints:['Every claim sourced and dated','Accuracy claims only from eval results','Banned-word list applies in full'],
    sys:'You are Product Marketing at BAi. Use Dunford positioning, filled in completely — including "do nothing" and "hire someone" as competitive alternatives, because they usually win. Category: Operational Intelligence. Counter-position: RPA automates the happy path and hands you the exceptions; we work the exceptions and hand you the decisions. Every quantitative claim carries a source and date. Accuracy claims come from golden-set eval results and nowhere else — never a demo, never a good week, never rounded up. If the Data Analyst cannot evidence a number, it does not ship, and treat that challenge as correct by default. The banned-word list applies in full: "AI-powered" is exactly the phrase the brand exists to avoid.' },
];

/* ── Demo data. Money is minor units + ISO 4217 — never a float. ─────────── */
const EXPONENT = { JPY:0, KRW:0, VND:0, CLP:0, ISK:0, BHD:3, KWD:3, OMR:3, TND:3, JOD:3 };
const exp = c => (c in EXPONENT ? EXPONENT[c] : 2);

function fmtMoney(minor, currency, locale) {
  const e = exp(currency);
  const major = minor / Math.pow(10, e);
  try {
    return new Intl.NumberFormat(locale || 'en-GB', {
      style: 'currency', currency, minimumFractionDigits: e, maximumFractionDigits: e
    }).format(major);
  } catch {
    return `${major.toFixed(e)} ${currency}`;
  }
}

const CONFIDENCE_FLOOR = 0.70;
const state = c => (c >= 0.90 ? 'high' : c >= CONFIDENCE_FLOOR ? 'medium' : 'unknown');
const stateLabel = c => ({ high:'High', medium:'Medium', unknown:'Unknown' })[state(c)];

const RECORDS = [
  { ref:'REC-4471', title:'Supplier onboarding — Kanda KK', product:'Reconcile', minor:4_820_000, cur:'JPY', loc:'ja-JP', conf:0.94, status:'auto' },
  { ref:'REC-4468', title:'Q3 licence true-up', product:'Reconcile', minor:12_450_00, cur:'GBP', loc:'en-GB', conf:0.88, status:'auto' },
  { ref:'REC-4462', title:'Facilities retainer — Gulf region', product:'Reconcile', minor:8_750_500, cur:'KWD', loc:'ar-KW', conf:0.62, status:'escalated' },
  { ref:'REC-4455', title:'Freight invoice batch 88-B', product:'Reconcile', minor:214_900, cur:'USD', loc:'en-US', conf:0.97, status:'auto' },
  { ref:'REC-4451', title:'Contractor timesheets — São Paulo', product:'Reconcile', minor:1_842_300, cur:'BRL', loc:'pt-BR', conf:0.55, status:'escalated' },
];

const QUEUE = [
  { id:'ESC-118', title:'Payment run exceeds approved threshold', record:'REC-4462',
    why:'The reconciliation matched, but the total is 18% above the value the statement of work allows. Posting it would be a financial action and cannot be reversed by the platform.',
    evidence:'Line 14 of the invoice reads 8,750.500 KWD against an approved ceiling of 7,400.000 KWD.',
    cite:'invoice_88b.pdf · p.2 · chars 1840–1902', conf:0.62, irreversible:true,
    options:['Approve and post','Hold and query supplier','Reject'] },
  { id:'ESC-117', title:'Two suppliers resolve to the same tax ID',
    record:'REC-4451',
    why:'Kanda KK and Kanda Logistics share a registered tax identifier. Merging them is reversible, but paying against the wrong entity is not.',
    evidence:'Both records carry tax ID 8-4471-0029-113, registered to different trading names.',
    cite:'ledger_export.csv · row 214 · column tax_id', conf:0.55, irreversible:false,
    options:['Merge entities','Keep separate','Ask finance'] },
  { id:'ESC-115', title:'Currency mismatch on a cross-border line',
    record:'REC-4468',
    why:'The purchase order is in GBP, the invoice in EUR, and no FX rate was pinned at the time of agreement. The system will not convert implicitly.',
    evidence:'PO-2291 states GBP 12,450.00. Invoice states EUR 14,610.00. No rate on file for 2026-06-14.',
    cite:'po_2291.pdf · p.1 · chars 402–448', conf:0.81, irreversible:false,
    options:['Pin rate and convert','Return to supplier','Escalate to treasury'] },
];

const INVARIANTS = [
  { n:1, t:'Durable runs', d:'Every step persisted with an input hash. A crash resumes; it never silently repeats an action.' },
  { n:2, t:'Provenance', d:'Every fact carries source, locator, span and confidence. A fact without provenance raises at construction.' },
  { n:3, t:'Escalation', d:'A first-class outcome, not an error. Consequential actions require approval by default.' },
  { n:4, t:'Reversibility', d:'Every write is reversible or approved. Connectors declare reversibility; the runner enforces it.' },
  { n:5, t:'Budget guard', d:'Per-tenant inference ceiling, alerting at 70/90/100%. A hard stop, never a soft warning.' },
];

const REGIONS = [
  { c:'eu', n:'Frankfurt', r:'EEA', g:'GDPR · ePrivacy · NIS2 · DORA' },
  { c:'uk', n:'London', r:'United Kingdom', g:'UK GDPR · DPA 2018 · FCA' },
  { c:'us', n:'Virginia', r:'USA & Canada', g:'CCPA/CPRA · PIPEDA · GLBA · SOX' },
  { c:'apac', n:'Sydney', r:'ANZ & SE Asia', g:'Australian Privacy Principles · PDPA' },
  { c:'jp', n:'Tokyo', r:'Japan & Korea', g:'APPI · PIPA' },
  { c:'br', n:'São Paulo', r:'Brazil & LATAM', g:'LGPD' },
];

/* ── Claude transport ────────────────────────────────────────────────────── */
async function callClaude(systemPrompt, userPrompt) {
  const body = {
    model: cfg.model,
    max_tokens: 1600,
    system: systemPrompt,
    messages: [{ role: 'user', content: userPrompt }],
  };

  if (cfg.mode === 'demo') {
    await new Promise(r => setTimeout(r, 700));
    return { text: demoReply(systemPrompt, userPrompt), usage: null, demo: true };
  }

  if (cfg.mode === 'proxy') {
    if (!cfg.sbUrl || !cfg.sbKey) throw new Error('Supabase URL and anon key are not set. Open Settings to add them.');
    const res = await fetch(`${cfg.sbUrl.replace(/\/$/, '')}/functions/v1/claude-proxy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${cfg.sbKey}` },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`Edge Function returned ${res.status}. ${(await res.text()).slice(0, 300)}`);
    return normalise(await res.json());
  }

  // byok — direct browser call, user's own key
  if (!cfg.apiKey) throw new Error('No Anthropic API key set. Open Settings to add one, or switch to Demo.');
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': cfg.apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true',
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Anthropic API returned ${res.status}. ${(await res.text()).slice(0, 300)}`);
  return normalise(await res.json());
}

function normalise(json) {
  const text = (json.content || []).filter(b => b.type === 'text').map(b => b.text).join('\n');
  return { text: text || '(empty response)', usage: json.usage || null };
}

function demoReply(sys, user) {
  const who = (sys.match(/You are (?:The )?([^,.]+)/) || [, 'the agent'])[1];
  return `[Demo mode — no request left this browser]\n\n`
    + `${who} would answer this brief under its binding constraints.\n\n`
    + `Brief received: "${user.slice(0, 160)}${user.length > 160 ? '…' : ''}"\n\n`
    + `To get a real response, open Settings and pick a connection mode:\n\n`
    + `  • Supabase proxy — your Anthropic key lives in Supabase secrets, never in the browser.\n`
    + `    This is the recommended setup for a page published on GitHub Pages.\n\n`
    + `  • Bring your own key — calls Anthropic directly from this browser. Your key stays in\n`
    + `    localStorage on this device. Never ship a page with a shared key in it.\n\n`
    + `Note: a Claude Pro or Max subscription cannot authenticate either mode. Those cover\n`
    + `claude.ai and Claude Code only. A web app needs an API key from console.anthropic.com,\n`
    + `which is billed separately as pay-as-you-go.`;
}

/* ── Render ──────────────────────────────────────────────────────────────── */
const $ = s => document.querySelector(s);
const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };

let activeAgent = AGENTS[0];

function renderRoster() {
  const host = $('#rosterList');
  host.innerHTML = '';
  let pod = null;
  for (const a of AGENTS) {
    if (a.pod !== pod) { pod = a.pod; host.appendChild(el('div', 'pod-label', pod + (pod === 'Supervisor' ? '' : 's'))); }
    const b = el('button', 'agent' + (a.id === activeAgent.id ? ' is-active' : ''));
    b.type = 'button';
    b.appendChild(el('span', 'pip ' + a.cls));
    b.appendChild(el('span', null, a.name));
    b.addEventListener('click', () => { activeAgent = a; renderRoster(); renderWorkbench(); });
    host.appendChild(b);
  }
  $('#agentCount').textContent = String(AGENTS.length);
}

function renderWorkbench() {
  $('#wbName').textContent = activeAgent.name;
  $('#wbRole').textContent = activeAgent.role;
  $('#wbPod').textContent = activeAgent.pod;
  const c = $('#wbConstraints');
  c.innerHTML = '';
  activeAgent.constraints.forEach(t => c.appendChild(el('span', 'constraint', t)));
}

function renderQueue() {
  const host = $('#queueList');
  host.innerHTML = '';
  QUEUE.forEach(e => {
    const card = el('div', 'card esc');
    const top = el('div', 'card-top');
    const left = el('div');
    left.appendChild(el('h3', null, e.title));
    const meta = el('div', 'muted small');
    meta.textContent = `${e.id} · ${e.record}`;
    left.appendChild(meta);
    top.appendChild(left);
    const chips = el('div', 'card-actions');
    chips.appendChild(el('span', 'chip ' + state(e.conf), `${stateLabel(e.conf)} ${Math.round(e.conf * 100)}%`));
    top.appendChild(chips);
    card.appendChild(top);
    card.appendChild(el('p', 'why', e.why));
    const ev = el('div', 'evidence');
    ev.appendChild(document.createTextNode(e.evidence));
    ev.appendChild(el('cite', null, e.cite));
    card.appendChild(ev);
    const acts = el('div', 'card-actions');
    e.options.forEach((o, i) => {
      const b = el('button', i === 0 ? 'btn-primary' : 'btn-ghost', o);
      b.type = 'button';
      b.addEventListener('click', () => alert(`Demo console — "${o}" is not wired to a backend.\n\nIn the platform this routes through AgentRun.authorise(), which would ${e.irreversible ? 'refuse to act autonomously because the action is irreversible' : 'check the tenant\'s autonomy grant for this action type'}.`));
      acts.appendChild(b);
    });
    if (e.irreversible) acts.appendChild(el('span', 'irrev', '⚠ Irreversible — cannot be granted autonomy'));
    card.appendChild(acts);
    host.appendChild(card);
  });
  $('#queueCount').textContent = String(QUEUE.length);
}

function renderRecords() {
  const body = $('#recordsBody');
  body.innerHTML = '';
  RECORDS.forEach(r => {
    const tr = el('tr');
    const c1 = el('td');
    c1.appendChild(el('div', null, r.title));
    c1.appendChild(el('span', 'ref', r.ref));
    tr.appendChild(c1);
    tr.appendChild(el('td', null, r.product));
    const c3 = el('td', 'num', fmtMoney(r.minor, r.cur, r.loc));
    c3.title = `${r.minor} minor units · ${r.cur} · ${exp(r.cur)} decimal places`;
    tr.appendChild(c3);
    const c4 = el('td');
    c4.appendChild(el('span', 'chip ' + state(r.conf), `${stateLabel(r.conf)} ${Math.round(r.conf * 100)}%`));
    tr.appendChild(c4);
    const c5 = el('td');
    c5.appendChild(el('span', 'chip ' + (r.status === 'auto' ? 'auto' : 'medium'),
      r.status === 'auto' ? 'Automated' : 'Awaiting human'));
    tr.appendChild(c5);
    body.appendChild(tr);
  });
}

function renderPlatform() {
  const g = $('#invariantGrid'); g.innerHTML = '';
  INVARIANTS.forEach(i => {
    const t = el('div', 'tile');
    const h = el('h3');
    h.appendChild(el('span', 'n', String(i.n)));
    h.appendChild(document.createTextNode(i.t));
    t.appendChild(h);
    t.appendChild(el('p', null, i.d));
    g.appendChild(t);
  });
  const rg = $('#regionGrid'); rg.innerHTML = '';
  REGIONS.forEach(r => {
    const t = el('div', 'tile');
    const h = el('h3');
    h.appendChild(el('span', 'region-code', r.c));
    h.appendChild(document.createTextNode(r.n));
    t.appendChild(h);
    t.appendChild(el('p', null, r.r));
    t.appendChild(el('p', 'small muted', r.g));
    rg.appendChild(t);
  });
}

/* ── Wiring ──────────────────────────────────────────────────────────────── */
function applyMode() {
  const labels = { demo:'Demo', proxy:'Supabase proxy', byok:'Direct (BYOK)' };
  $('#modeLabel').textContent = labels[cfg.mode];
  $('#modeDot').className = 'dot' + (cfg.mode === 'demo' ? '' : ' live');
}
function applyTheme() {
  document.documentElement.setAttribute('data-theme', cfg.theme);
}

document.querySelectorAll('.tab').forEach(t => {
  t.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('is-active'));
    document.querySelectorAll('.view').forEach(x => x.classList.remove('is-active'));
    t.classList.add('is-active');
    $('#view-' + t.dataset.view).classList.add('is-active');
  });
});

$('#runBtn').addEventListener('click', async () => {
  const brief = $('#prompt').value.trim();
  const out = $('#output');
  if (!brief) { $('#prompt').focus(); return; }
  const btn = $('#runBtn');
  btn.disabled = true;
  out.className = 'output show';
  out.innerHTML = '';
  out.appendChild(el('span', 'spinner'));
  out.appendChild(document.createTextNode(`${activeAgent.name} is working…`));
  $('#costLine').textContent = '';
  try {
    const r = await callClaude(activeAgent.sys, brief);
    out.className = 'output show';
    out.textContent = r.text;
    if (r.usage) {
      $('#costLine').textContent = `${r.usage.input_tokens} in · ${r.usage.output_tokens} out`;
    }
  } catch (err) {
    out.className = 'output show err';
    out.textContent = `Could not reach Claude.\n\n${err.message}\n\nNothing was changed. Open Settings to check your connection mode.`;
  } finally {
    btn.disabled = false;
  }
});

$('#clearBtn').addEventListener('click', () => {
  $('#prompt').value = '';
  $('#output').className = 'output';
  $('#costLine').textContent = '';
});

$('#themeBtn').addEventListener('click', () => {
  cfg.theme = cfg.theme === 'dark' ? 'light' : 'dark';
  applyTheme(); save();
});

const dlg = $('#settings');
function openSettings() {
  document.querySelector(`input[name="mode"][value="${cfg.mode}"]`).checked = true;
  $('#sbUrl').value = cfg.sbUrl; $('#sbKey').value = cfg.sbKey;
  $('#apiKey').value = cfg.apiKey; $('#model').value = cfg.model;
  syncCfgPanels();
  dlg.showModal();
}
function syncCfgPanels() {
  const m = document.querySelector('input[name="mode"]:checked').value;
  $('#cfgProxy').hidden = m !== 'proxy';
  $('#cfgByok').hidden = m !== 'byok';
}
$('#settingsBtn').addEventListener('click', openSettings);
$('#modeChip').addEventListener('click', openSettings);
document.querySelectorAll('input[name="mode"]').forEach(r => r.addEventListener('change', syncCfgPanels));
dlg.addEventListener('close', () => {
  if (dlg.returnValue !== 'save') return;
  cfg.mode = document.querySelector('input[name="mode"]:checked').value;
  cfg.sbUrl = $('#sbUrl').value.trim();
  cfg.sbKey = $('#sbKey').value.trim();
  cfg.apiKey = $('#apiKey').value.trim();
  cfg.model = $('#model').value;
  save(); applyMode();
});

applyTheme(); applyMode();
renderRoster(); renderWorkbench(); renderQueue(); renderRecords(); renderPlatform();
