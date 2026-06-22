const API_BASE = location.protocol === "file:" ? "http://127.0.0.1:8080" : "";

const jobForm = document.getElementById("jobForm");
const clarificationForm = document.getElementById("clarificationForm");
const clarificationBox = document.getElementById("clarificationBox");
const submitClarificationsBtn = document.getElementById("submitClarifications");
const eventsEl = document.getElementById("events");
const statusEl = document.getElementById("jobStatus");
const jobIdEl = document.getElementById("jobId");
const solutionEl = document.getElementById("solution");
const learningEl = document.getElementById("learning");
const startBtn = document.getElementById("startBtn");
const activeCountEl = document.getElementById("activeCount");
const doneCountEl = document.getElementById("doneCount");
const eventCountEl = document.getElementById("eventCount");
const progressTrackEl = document.getElementById("progressTrack");
const resultBadgeEl = document.getElementById("resultBadge");
const jumpToResultBtn = document.getElementById("jumpToResult");
const resultAnchorEl = document.getElementById("resultAnchor");
const resultBlockEl = document.querySelector(".result-block");
const flowCanvasEl = document.getElementById("diaphragm");
const resultModalEl = document.getElementById("resultModal");
const resultModalTextEl = document.getElementById("resultModalText");
const openResultBtn = document.getElementById("openResultBtn");
const closeResultBtn = document.getElementById("closeResultBtn");
const clarificationChatEl = document.getElementById("clarificationChat");
const freeClarificationEl = document.getElementById("freeClarification");
const clarificationFilesEl = document.getElementById("clarificationFiles");
const updateContextBtn = document.getElementById("updateContextBtn");
const promptInput = document.getElementById("prompt");
const requirementsInput = document.getElementById("requirements");
const filesInput = document.getElementById("files");
const filesLabelEl = document.getElementById("filesLabel");
const sourceHelpEl = document.getElementById("sourceHelp");
const sourceButtons = Array.from(document.querySelectorAll(".source-option[data-source]"));
const dbConnectorPanel = document.getElementById("dbConnectorPanel");
const dbConnectionStringEl = document.getElementById("dbConnectionString");
const testDbConnectionBtn = document.getElementById("testDbConnectionBtn");
const dbConnectionStatusEl = document.getElementById("dbConnectionStatus");
const dbSchemaPreviewEl = document.getElementById("dbSchemaPreview");
const dbQueryRequestEl = document.getElementById("dbQueryRequest");
const runDbQueryBtn = document.getElementById("runDbQueryBtn");
const dbQueryResultEl = document.getElementById("dbQueryResult");
const useCaseButtons = Array.from(document.querySelectorAll(".case[data-case]"));
const useCaseTitleEl = document.getElementById("useCaseTitle");
const useCaseDescriptionEl = document.getElementById("useCaseDescription");
const useCaseActionsEl = document.getElementById("useCaseActions");
const useCaseOutputEl = document.getElementById("useCaseOutput");
const decisionNodeLabelEl = document.getElementById("decisionNodeLabel");
const topActionNodeLabelEl = document.getElementById("topActionNodeLabel");
const bottomActionNodeLabelEl = document.getElementById("bottomActionNodeLabel");

let currentJobId = null;
let socket = null;
let latestQuestions = [];
let snapshotPoll = null;
let eventCount = 0;
const seenEvents = new Set();
let lastQuestionsKey = "";
let resultShown = false;
let selectedUseCase = "it_ops";
let latestConversation = [];
let selectedSource = "csv";
let verifiedDbConnectionId = "";

const activeAgents = new Set();
const doneAgents = new Set();
const STATUS_ORDER = ["intake", "awaiting_clarification", "running", "completed"];
const LINK_MAP = {
  "discovery-agent": [".node.trigger", ".node.core"],
  "clarification-agent": [".node.core", ".node.decision"],
  "analysis-agent": [".node.decision", ".node.action.top"],
  "ops-agent": [".node.decision", ".node.action.bottom"],
  "solution-agent": [".node.core", ".node.action.top"],
  "data-intake-agent": [".node.core", ".node.r1"],
  "governance-agent": [".node.core", ".node.r2"],
  "learning-agent": [".node.core", ".node.r3"],
};

const USE_CASES = {
  it_ops: {
    label: "IT Ops",
    description: "Specializzato in processi IT operativi: ticket, onboarding, standardizzazione runbook e riduzione tempi di delivery.",
    actions: [
      "Scompone la richiesta in runbook e checklist operative.",
      "Definisce SLA, ownership e automazioni ripetibili.",
      "Propone controlli di qualità prima del rilascio.",
    ],
    outputs: [
      "Piano operativo con milestone e owner.",
      "Mappa rischi/blocchi operativi con mitigazioni.",
      "Next best action per ottimizzare throughput e tempi.",
    ],
    promptPlaceholder: "Esempio: ridurre il tempo di onboarding IT da 5 giorni a 2 con workflow e controlli automatici.",
    requirementsPlaceholder: "Inserisci policy IT, stack tecnico, vincoli di sicurezza, SLA e deadline.",
    presetRequirements: [
      "Dominio: IT Operations",
      "Focus KPI: lead time, SLA compliance, tasso incident post-rilascio",
      "Output richiesto: runbook operativo + roadmap di automazione",
    ],
    diagram: {
      decision: "SLA e prerequisiti chiari?",
      actionTop: "Deploy Runbook",
      actionBottom: "Richiedi asset mancanti",
    },
  },
  sec_ops: {
    label: "Sec Ops",
    description: "Orientato a triage, risposta incident e controllo compliance con priorità su rischio e impatto.",
    actions: [
      "Classifica minacce per severità e business impact.",
      "Costruisce piano di risposta con escalation e owner.",
      "Traccia gap di compliance e remediation prioritaria.",
    ],
    outputs: [
      "Incident response plan con priorità e tempi target.",
      "Risk register con severità/probabilità/mitigazioni.",
      "Next best action per ridurre esposizione e tempi di detection.",
    ],
    promptPlaceholder: "Esempio: definire workflow di triage per incidenti phishing con SLA e policy di escalation.",
    requirementsPlaceholder: "Inserisci policy security, standard compliance (ISO, SOC2, GDPR), RTO/RPO e vincoli.",
    presetRequirements: [
      "Dominio: Security Operations",
      "Focus KPI: MTTD, MTTR, incident recurrence, compliance closure rate",
      "Output richiesto: playbook di incident response + piano remediation",
    ],
    diagram: {
      decision: "Rischio classificato?",
      actionTop: "Esegui Response Plan",
      actionBottom: "Escalate & Gather Evidence",
    },
  },
  rev_ops: {
    label: "Rev Ops",
    description: "Pensato per richieste commerciali/data-driven: forecast, conversion funnel e ottimizzazione ricavi.",
    actions: [
      "Analizza funnel e segmenti con impatto su revenue.",
      "Definisce ipotesi su conversione, CAC e retention.",
      "Produce piano azioni con priorità economica.",
    ],
    outputs: [
      "Analisi pipeline e forecast con scenari.",
      "Piano di ottimizzazione conversione/retention.",
      "Next best action basate su impatto economico atteso.",
    ],
    promptPlaceholder: "Esempio: aumentare conversione SQL->Deal del 15% nei prossimi 2 trimestri.",
    requirementsPlaceholder: "Inserisci target ricavi, segmenti, vincoli di budget, canali e baseline KPI.",
    presetRequirements: [
      "Dominio: Revenue Operations",
      "Focus KPI: conversion rate, CAC payback, churn, net revenue retention",
      "Output richiesto: piano di crescita + backlog di esperimenti",
    ],
    diagram: {
      decision: "Funnel e dati affidabili?",
      actionTop: "Build Growth Plan",
      actionBottom: "Richiedi segmentazione dati",
    },
  },
  strategy: {
    label: "Strategy",
    description: "Preset executive per business plan e decisioni di investimento: mercato, unit economics, rischi e roadmap.",
    actions: [
      "Converte la richiesta in struttura di business plan pronta per stakeholder.",
      "Costruisce scenari economici (base/prudente/aggressivo).",
      "Definisce decisioni go/no-go con KPI e checkpoint temporali.",
    ],
    outputs: [
      "Business Plan completo con sezioni executive.",
      "Ipotesi economiche e rischi con mitigazioni.",
      "Next best action orientate a execution e validazione mercato.",
    ],
    promptPlaceholder: "Esempio: prepara un business plan per un prodotto AI B2B con focus su PMF e scalabilità.",
    requirementsPlaceholder: "Inserisci budget, timeline, target mercato, assunzioni economiche e vincoli.",
    presetRequirements: [
      "Dominio: Strategic Planning",
      "Focus KPI: ARR, gross margin, CAC payback, burn multiple, NRR",
      "Output richiesto: business plan + roadmap 12 mesi + piano rischi",
    ],
    diagram: {
      decision: "Business case validato?",
      actionTop: "Finalize Business Plan",
      actionBottom: "Rivedi assunzioni critiche",
    },
  },
};

const DATA_SOURCES = {
  csv: {
    label: "File CSV",
    accept: ".csv",
    help: "Carica uno o più file CSV da analizzare.",
  },
  excel: {
    label: "File Excel",
    accept: ".xlsx,.xls",
    help: "Carica uno o più file Excel. Il sistema leggerà fogli, colonne e metriche principali.",
  },
  database: {
    label: "Database SQLite",
    accept: ".db,.sqlite,.sqlite3",
    help: "Carica un database SQLite: verranno letti schema, tabelle, colonne e relazioni. Potrai chiedere estrazioni in linguaggio naturale.",
  },
  document: {
    label: "Documenti / requirement",
    accept: ".txt,.md,.csv,.xlsx,.xls,.db,.sqlite,.sqlite3",
    help: "Carica documenti di requirement o fonti miste. Puoi combinare testo, dati tabellari e database locali.",
  },
};

function apiUrl(path) {
  return `${API_BASE}${path}`;
}

function renderUseCasePanel(caseId) {
  const profile = USE_CASES[caseId] || USE_CASES.it_ops;
  if (useCaseTitleEl) useCaseTitleEl.textContent = profile.label;
  if (useCaseDescriptionEl) useCaseDescriptionEl.textContent = profile.description;

  if (useCaseActionsEl) {
    useCaseActionsEl.innerHTML = "";
    for (const item of profile.actions) {
      const li = document.createElement("li");
      li.textContent = item;
      useCaseActionsEl.appendChild(li);
    }
  }

  if (useCaseOutputEl) {
    useCaseOutputEl.innerHTML = "";
    for (const item of profile.outputs) {
      const li = document.createElement("li");
      li.textContent = item;
      useCaseOutputEl.appendChild(li);
    }
  }

  if (promptInput) promptInput.placeholder = profile.promptPlaceholder;
  if (requirementsInput) requirementsInput.placeholder = profile.requirementsPlaceholder;
  if (decisionNodeLabelEl) decisionNodeLabelEl.textContent = profile.diagram.decision;
  if (topActionNodeLabelEl) topActionNodeLabelEl.textContent = profile.diagram.actionTop;
  if (bottomActionNodeLabelEl) bottomActionNodeLabelEl.textContent = profile.diagram.actionBottom;
}

function selectUseCase(caseId, shouldSeedFields = false) {
  selectedUseCase = USE_CASES[caseId] ? caseId : "it_ops";
  useCaseButtons.forEach((button) => {
    const isActive = button.dataset.case === selectedUseCase;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
  renderUseCasePanel(selectedUseCase);

  if (!shouldSeedFields) return;
  const profile = USE_CASES[selectedUseCase];
  if (promptInput && !promptInput.value.trim()) {
    promptInput.value = profile.promptPlaceholder.replace("Esempio: ", "");
  }
  if (requirementsInput && !requirementsInput.value.trim()) {
    requirementsInput.value = profile.presetRequirements.join("\n");
  }
  layoutLinks();
}

function selectDataSource(sourceId) {
  selectedSource = DATA_SOURCES[sourceId] ? sourceId : "csv";
  const source = DATA_SOURCES[selectedSource];

  sourceButtons.forEach((button) => {
    const isActive = button.dataset.source === selectedSource;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });

  if (filesLabelEl) filesLabelEl.textContent = source.label;
  if (sourceHelpEl) sourceHelpEl.textContent = source.help;
  if (filesInput) {
    filesInput.accept = source.accept;
    filesInput.value = "";
  }
  const isDatabase = selectedSource === "database";
  dbConnectorPanel?.classList.toggle("hidden", !isDatabase);
  filesLabelEl?.classList.toggle("hidden", isDatabase);
  filesInput?.classList.toggle("hidden", isDatabase);
}

function summarizeDbSchema(schema) {
  const tables = Array.isArray(schema?.tables) ? schema.tables : [];
  const rels = [
    ...(Array.isArray(schema?.relationships) ? schema.relationships : []),
    ...(Array.isArray(schema?.inferred_relationships) ? schema.inferred_relationships : []),
  ];
  const lines = [
    `Tabelle: ${tables.length}`,
    ...tables.slice(0, 10).map((table) => {
      const cols = Array.isArray(table.columns) ? table.columns.map((col) => col.name).join(", ") : "";
      return `- ${table.name} (${table.row_count} righe): ${cols}`;
    }),
  ];
  if (rels.length) {
    lines.push("Relazioni:");
    rels.slice(0, 10).forEach((rel) => {
      lines.push(`- ${rel.from_table}.${rel.from_column} -> ${rel.to_table}.${rel.to_column}`);
    });
  }
  return lines.join("\n");
}

function renderDbQueryResult(response) {
  if (!dbQueryResultEl) return;
  const result = response?.result || {};
  const rows = Array.isArray(result.rows) ? result.rows : [];
  const payload = {
    mode: response?.mode,
    answer: result.answer || response?.error || "N/D",
    sql: result.sql || null,
    rows: rows.slice(0, 20),
  };
  dbQueryResultEl.textContent = JSON.stringify(payload, null, 2);
}

function resetView() {
  activeAgents.clear();
  doneAgents.clear();
  eventCount = 0;
  seenEvents.clear();
  lastQuestionsKey = "";
  resultShown = false;
  latestConversation = [];
  if (freeClarificationEl) freeClarificationEl.value = "";
  if (clarificationFilesEl) clarificationFilesEl.value = "";
  renderClarificationConversation([]);
  updateMetrics();
  setStatus("Idle", "default");
  if (resultBadgeEl) {
    resultBadgeEl.classList.remove("ready");
    resultBadgeEl.textContent = "Risultato finale: in attesa";
  }
  resultBlockEl?.classList.remove("focus");

  document.querySelectorAll(".node").forEach((node) => {
    node.classList.remove("active", "done");
    node.classList.add("queued");
  });
  document.querySelectorAll(".links path").forEach((path) => {
    path.classList.remove("active", "done");
  });

  updateProgressTrack("intake");
  layoutLinks();
}

function showResultModal(solutionText) {
  if (!resultModalEl) return;
  const preview = (solutionText || "").replace(/\s+/g, " ").trim().slice(0, 180);
  if (resultModalTextEl) {
    resultModalTextEl.textContent = preview
      ? `Anteprima: ${preview}${solutionText.length > 180 ? "..." : ""}`
      : "La pipeline ha completato l'elaborazione.";
  }
  resultModalEl.classList.remove("hidden");
}

function hideResultModal() {
  resultModalEl?.classList.add("hidden");
}

function setStatus(text, tone = "default") {
  statusEl.textContent = text;
  statusEl.style.background = "#123043";
  statusEl.style.borderColor = "#2f4f69";

  if (tone === "ok") {
    statusEl.style.background = "rgba(80,227,143,0.2)";
    statusEl.style.borderColor = "#50e38f";
  }
  if (tone === "warn") {
    statusEl.style.background = "rgba(255,199,103,0.2)";
    statusEl.style.borderColor = "#ffc767";
  }
  if (tone === "err") {
    statusEl.style.background = "rgba(255,126,140,0.2)";
    statusEl.style.borderColor = "#ff7e8c";
  }
}

function updateMetrics() {
  activeCountEl.textContent = String(activeAgents.size);
  doneCountEl.textContent = String(doneAgents.size);
  eventCountEl.textContent = String(eventCount);
}

function updateProgressTrack(status) {
  const normalized = status.startsWith("completed") ? "completed" : status;
  const currentIdx = STATUS_ORDER.indexOf(normalized);

  progressTrackEl.querySelectorAll("li").forEach((li) => {
    li.classList.remove("current", "done");
    const idx = STATUS_ORDER.indexOf(li.dataset.step);
    if (idx < currentIdx) li.classList.add("done");
    if (idx === currentIdx) li.classList.add("current");
    if (status.startsWith("completed") && idx === STATUS_ORDER.length - 1) {
      li.classList.remove("current");
      li.classList.add("done");
    }
  });
}

function setAgentNodeState(agent, state) {
  const node = document.querySelector(`.node[data-agent="${agent}"]`);
  const link = document.querySelector(`.links path[data-link="${agent}"]`);
  if (!node) return;

  node.classList.remove("queued", "active", "done");
  link?.classList.remove("active", "done");
  if (link) {
    link.setAttribute("marker-end", "url(#arrow-default)");
  }

  if (state === "active") {
    node.classList.add("active");
    link?.classList.add("active");
    link?.setAttribute("marker-end", "url(#arrow-active)");
  } else if (state === "done") {
    node.classList.add("done");
    link?.classList.add("done");
    link?.setAttribute("marker-end", "url(#arrow-done)");
  } else {
    node.classList.add("queued");
  }
}

function activateAgent(agent) {
  if (!document.querySelector(`.node[data-agent="${agent}"]`)) return;
  activeAgents.add(agent);
  doneAgents.delete(agent);
  setAgentNodeState(agent, "active");
  updateMetrics();
}

function completeAgent(agent) {
  if (!document.querySelector(`.node[data-agent="${agent}"]`)) return;
  activeAgents.delete(agent);
  doneAgents.add(agent);
  setAgentNodeState(agent, "done");
  updateMetrics();
}

function failAgent(agent) {
  if (!document.querySelector(`.node[data-agent="${agent}"]`)) return;
  activeAgents.delete(agent);
  setAgentNodeState(agent, "active");
  const node = document.querySelector(`.node[data-agent="${agent}"]`);
  if (node) {
    node.style.borderColor = "#ff7e8c";
    node.style.boxShadow = "0 0 0 6px rgba(255,126,140,0.15)";
  }
  updateMetrics();
}

function addEvent(event) {
  const key = `${event.timestamp || ""}|${event.agent || ""}|${event.phase || ""}|${event.message || ""}`;
  if (seenEvents.has(key)) return;
  seenEvents.add(key);
  if (seenEvents.size > 3000) {
    const first = seenEvents.values().next();
    if (!first.done) seenEvents.delete(first.value);
  }

  eventCount += 1;
  updateMetrics();

  const row = document.createElement("div");
  row.className = `event ${event.level || ""}`;

  const ts = new Date(event.timestamp || Date.now()).toLocaleTimeString("it-IT", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  row.innerHTML = `
    <div class="meta"><span>${ts}</span><span>${event.phase}</span></div>
    <div><b>${event.agent}</b> - ${event.message}</div>
  `;

  eventsEl.prepend(row);
}

function layoutLinks() {
  if (!flowCanvasEl) return;
  const canvasRect = flowCanvasEl.getBoundingClientRect();
  const svgEl = flowCanvasEl.querySelector(".links");
  if (svgEl) {
    const w = Math.max(1, Math.round(canvasRect.width));
    const h = Math.max(1, Math.round(canvasRect.height));
    svgEl.setAttribute("viewBox", `0 0 ${w} ${h}`);
    svgEl.setAttribute("width", String(w));
    svgEl.setAttribute("height", String(h));
  }
  const paths = flowCanvasEl.querySelectorAll(".links path[data-link]");

  function center(rect) {
    return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
  }

  function edgeAnchors(sourceRect, targetRect) {
    const s = center(sourceRect);
    const t = center(targetRect);
    const dx = t.x - s.x;
    const dy = t.y - s.y;
    const absDx = Math.abs(dx);
    const absDy = Math.abs(dy);
    const pad = 8;

    if (absDx >= absDy) {
      const dir = dx >= 0 ? 1 : -1;
      return {
        start: { x: s.x + dir * (sourceRect.width / 2 + pad), y: s.y },
        end: { x: t.x - dir * (targetRect.width / 2 + pad), y: t.y },
      };
    }

    const dir = dy >= 0 ? 1 : -1;
    return {
      start: { x: s.x, y: s.y + dir * (sourceRect.height / 2 + pad) },
      end: { x: t.x, y: t.y - dir * (targetRect.height / 2 + pad) },
    };
  }

  paths.forEach((path) => {
    const key = path.getAttribute("data-link");
    const pair = key ? LINK_MAP[key] : null;
    if (!pair) return;

    const fromEl = flowCanvasEl.querySelector(pair[0]);
    const toEl = flowCanvasEl.querySelector(pair[1]);
    if (!fromEl || !toEl) return;

    const a = fromEl.getBoundingClientRect();
    const b = toEl.getBoundingClientRect();
    const anchors = edgeAnchors(a, b);
    const start = anchors.start;
    const end = anchors.end;
    const x1 = start.x - canvasRect.left;
    const y1 = start.y - canvasRect.top;
    const x2 = end.x - canvasRect.left;
    const y2 = end.y - canvasRect.top;
    const dx = Math.max(40, Math.abs(x2 - x1) * 0.42);
    const d = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
    path.setAttribute("d", d);
    if (!path.getAttribute("marker-end")) {
      path.setAttribute("marker-end", "url(#arrow-default)");
    }
  });
}

function ingestEvents(events) {
  if (!Array.isArray(events)) return;
  for (const ev of events) {
    addEvent(ev);
    if (["start", "resume", "info"].includes(ev.phase)) activateAgent(ev.agent);
    if (ev.phase === "complete") completeAgent(ev.agent);
    if (ev.phase === "error") failAgent(ev.agent);
  }
}

function renderQuestions(questions) {
  latestQuestions = questions || [];
  const currentKey = JSON.stringify(latestQuestions);
  const wasVisible = !clarificationBox.classList.contains("hidden");
  if (currentKey === lastQuestionsKey && wasVisible) {
    return;
  }

  const previousAnswers = {};
  clarificationForm.querySelectorAll("input[name^='q_']").forEach((input, idx) => {
    if (latestQuestions[idx]) previousAnswers[latestQuestions[idx]] = input.value;
  });

  clarificationForm.innerHTML = "";

  if (!latestQuestions.length) {
    clarificationBox.classList.add("hidden");
    lastQuestionsKey = "";
    return;
  }

  latestQuestions.forEach((q, idx) => {
    const label = document.createElement("label");
    label.textContent = `${idx + 1}. ${q}`;

    const input = document.createElement("input");
    input.type = "text";
    input.name = `q_${idx}`;
    input.placeholder = "Risposta";
    input.value = previousAnswers[q] || "";

    clarificationForm.appendChild(label);
    clarificationForm.appendChild(input);
  });

  clarificationBox.classList.remove("hidden");
  lastQuestionsKey = currentKey;
  const firstInput = clarificationForm.querySelector("input");
  if (firstInput && !wasVisible) {
    firstInput.focus();
  }
  setStatus("Azione richiesta: compila chiarimenti", "warn");
  if (!wasVisible) clarificationBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderClarificationConversation(conversation = []) {
  latestConversation = Array.isArray(conversation) ? conversation : [];
  if (!clarificationChatEl) return;

  clarificationChatEl.innerHTML = "";
  if (!latestConversation.length) {
    const empty = document.createElement("div");
    empty.className = "chat-message system";
    empty.textContent = "Aggiungi dettagli, query o file se vuoi riorientare l'analisi prima dell'esecuzione.";
    clarificationChatEl.appendChild(empty);
    return;
  }

  for (const turn of latestConversation) {
    const row = document.createElement("div");
    row.className = `chat-message ${turn.role || "user"}`;
    const files = Array.isArray(turn.files) && turn.files.length ? `\nFile: ${turn.files.join(", ")}` : "";
    row.textContent = `${turn.message || "Contesto aggiornato."}${files}`;
    clarificationChatEl.appendChild(row);
  }
  clarificationChatEl.scrollTop = clarificationChatEl.scrollHeight;
}

async function fetchSnapshot() {
  if (!currentJobId) return;
  const res = await fetch(apiUrl(`/api/jobs/${currentJobId}`));
  if (!res.ok) {
    if (res.status === 404) {
      if (snapshotPoll) clearInterval(snapshotPoll);
      currentJobId = null;
      setStatus("Job non trovato. Avvia un nuovo flow.", "warn");
      jobIdEl.textContent = "Nessun job";
    }
    return;
  }

  const snap = await res.json();
  const tone = snap.status.includes("failed")
    ? "err"
    : (snap.status.includes("review") || snap.status === "awaiting_clarification")
      ? "warn"
      : "ok";
  setStatus(snap.status, tone);
  jobIdEl.textContent = `Job: ${snap.job_id}`;
  updateProgressTrack(snap.status);
  ingestEvents(snap.events || []);

  if (snap.status === "awaiting_clarification") {
    renderQuestions(snap.clarification_questions || []);
    renderClarificationConversation(snap.artifacts?.clarification_conversation || []);
  } else {
    clarificationBox.classList.add("hidden");
    lastQuestionsKey = "";
  }

  if (snap.artifacts?.final_solution_markdown) {
    solutionEl.textContent = snap.artifacts.final_solution_markdown;
    if (resultBadgeEl) {
      resultBadgeEl.classList.add("ready");
      resultBadgeEl.textContent = "Risultato finale pronto";
    }
    resultBlockEl?.classList.add("focus");
    if (!resultShown) {
      resultShown = true;
      showResultModal(snap.artifacts.final_solution_markdown || "");
      resultAnchorEl?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }
  if (snap.artifacts?.learning_report) {
    learningEl.textContent = JSON.stringify(snap.artifacts.learning_report, null, 2);
  }
}

function connectSocket(jobId) {
  if (socket) socket.close();

  const base = API_BASE || `${location.protocol}//${location.host}`;
  const wsUrl = base.replace("http://", "ws://").replace("https://", "wss://") + `/api/jobs/${jobId}/stream`;
  socket = new WebSocket(wsUrl);

  socket.onmessage = async (msg) => {
    const payload = JSON.parse(msg.data);

    if (payload.type === "snapshot") {
      await fetchSnapshot();
      return;
    }

    if (payload.type === "event") {
      const ev = payload.data;
      addEvent(ev);

      if (["start", "resume", "info"].includes(ev.phase)) activateAgent(ev.agent);
      if (ev.phase === "complete") completeAgent(ev.agent);
      if (ev.phase === "error") failAgent(ev.agent);

      if (["complete", "pause", "resume", "error"].includes(ev.phase)) {
        await fetchSnapshot();
      }
    }
  };

  socket.onerror = () => {
    // Keep polling fallback active.
  };

  socket.onclose = () => {
    // Keep polling fallback active.
  };
}

jobForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  if (snapshotPoll) clearInterval(snapshotPoll);
  resetView();
  eventsEl.innerHTML = "";
  solutionEl.textContent = "Elaborazione in corso...";
  learningEl.textContent = "In elaborazione...";

  startBtn.disabled = true;
  startBtn.textContent = "Running...";

  const profile = USE_CASES[selectedUseCase] || USE_CASES.it_ops;
  const promptText = promptInput.value.trim();
  const requirementsText = requirementsInput.value.trim();
  const contextualPrompt = `${promptText}\n\n[USE_CASE]\n${profile.label}\n\n[OBIETTIVO PRESET]\n${profile.description}`;
  const contextualRequirements = [
    requirementsText,
    "[PRESET REQUIREMENTS]",
    ...profile.presetRequirements,
  ]
    .filter(Boolean)
    .join("\n");

  const formData = new FormData();
  formData.append("prompt", contextualPrompt);
  formData.append("business_requirements", contextualRequirements);
  if (selectedSource === "database") {
    if (!verifiedDbConnectionId) {
      setStatus("Verifica prima la connessione DB", "warn");
      startBtn.disabled = false;
      startBtn.textContent = "Esegui Flow";
      return;
    }
    formData.append("db_connection_id", verifiedDbConnectionId);
  }

  if (selectedSource !== "database") {
    for (const file of filesInput.files) formData.append("files", file);
  }

  const res = await fetch(apiUrl("/api/jobs"), {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    setStatus("Errore creazione job", "err");
    startBtn.disabled = false;
    startBtn.textContent = "Esegui Flow";
    return;
  }

  const data = await res.json();
  currentJobId = data.job_id;
  jobIdEl.textContent = `Job: ${currentJobId}`;
  setStatus(data.status, "warn");
  updateProgressTrack(data.status);
  renderQuestions(data.clarification_questions || []);

  connectSocket(currentJobId);
  snapshotPoll = setInterval(fetchSnapshot, 2500);

  startBtn.disabled = false;
  startBtn.textContent = "Esegui Flow";
});

submitClarificationsBtn.addEventListener("click", async () => {
  if (!currentJobId) return;

  submitClarificationsBtn.disabled = true;
  submitClarificationsBtn.textContent = "Invio...";

  const answers = {};
  latestQuestions.forEach((q, idx) => {
    const input = clarificationForm.querySelector(`input[name="q_${idx}"]`);
    answers[q] = input?.value?.trim() || "N/D";
  });
  const freeContext = freeClarificationEl?.value?.trim() || "";

  const res = await fetch(apiUrl(`/api/jobs/${currentJobId}/clarifications`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers, free_context: freeContext }),
  });

  if (!res.ok) {
    setStatus("Errore invio chiarimenti", "err");
    submitClarificationsBtn.disabled = false;
    submitClarificationsBtn.textContent = "Avvia elaborazione";
    return;
  }

  clarificationBox.classList.add("hidden");
  if (freeClarificationEl) freeClarificationEl.value = "";
  if (clarificationFilesEl) clarificationFilesEl.value = "";
  setStatus("Pipeline in esecuzione", "ok");
  submitClarificationsBtn.disabled = false;
  submitClarificationsBtn.textContent = "Avvia elaborazione";
  await fetchSnapshot();
});

updateContextBtn?.addEventListener("click", async () => {
  if (!currentJobId) return;

  const message = freeClarificationEl?.value?.trim() || "";
  const hasFiles = Boolean(clarificationFilesEl?.files?.length);
  if (!message && !hasFiles) {
    setStatus("Scrivi una richiesta o allega un file", "warn");
    return;
  }

  updateContextBtn.disabled = true;
  updateContextBtn.textContent = "Aggiorno...";

  const formData = new FormData();
  formData.append("message", message);
  if (clarificationFilesEl) {
    for (const file of clarificationFilesEl.files) formData.append("files", file);
  }

  const res = await fetch(apiUrl(`/api/jobs/${currentJobId}/clarification-turn`), {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    setStatus("Errore aggiornamento contesto", "err");
    updateContextBtn.disabled = false;
    updateContextBtn.textContent = "Aggiorna contesto";
    return;
  }

  const snap = await res.json();
  if (freeClarificationEl) freeClarificationEl.value = "";
  if (clarificationFilesEl) clarificationFilesEl.value = "";
  renderQuestions(snap.clarification_questions || []);
  renderClarificationConversation(snap.artifacts?.clarification_conversation || []);
  ingestEvents(snap.events || []);
  setStatus("Contesto aggiornato, puoi continuare o avviare", "warn");
  updateContextBtn.disabled = false;
  updateContextBtn.textContent = "Aggiorna contesto";
});

useCaseButtons.forEach((button) => {
  button.addEventListener("click", () => {
    selectUseCase(button.dataset.case || "it_ops", true);
  });
});

sourceButtons.forEach((button) => {
  button.addEventListener("click", () => {
    selectDataSource(button.dataset.source || "csv");
  });
});

dbConnectionStringEl?.addEventListener("input", () => {
  verifiedDbConnectionId = "";
  if (dbConnectionStatusEl) {
    dbConnectionStatusEl.textContent = "Non verificata";
    dbConnectionStatusEl.classList.remove("ok", "err");
  }
  if (dbSchemaPreviewEl) dbSchemaPreviewEl.textContent = "Schema non caricato";
});

testDbConnectionBtn?.addEventListener("click", async () => {
  const connectionString = dbConnectionStringEl?.value?.trim() || "";
  if (!connectionString) {
    setStatus("Inserisci una stringa di connessione DB", "warn");
    return;
  }

  testDbConnectionBtn.disabled = true;
  testDbConnectionBtn.textContent = "Verifico...";
  if (dbConnectionStatusEl) {
    dbConnectionStatusEl.textContent = "Verifica...";
    dbConnectionStatusEl.classList.remove("ok", "err");
  }

  const res = await fetch(apiUrl("/api/db/test"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ connection_string: connectionString }),
  });
  const data = await res.json();

  if (!res.ok || data.status !== "ok") {
    verifiedDbConnectionId = "";
    if (dbConnectionStatusEl) {
      dbConnectionStatusEl.textContent = "Errore";
      dbConnectionStatusEl.classList.add("err");
    }
    if (dbSchemaPreviewEl) dbSchemaPreviewEl.textContent = data.error || "Connessione fallita";
    setStatus("Connessione DB non valida", "err");
  } else {
    verifiedDbConnectionId = data.connection_id;
    if (dbConnectionStatusEl) {
      dbConnectionStatusEl.textContent = "Verificata";
      dbConnectionStatusEl.classList.add("ok");
      dbConnectionStatusEl.classList.remove("err");
    }
    if (dbSchemaPreviewEl) dbSchemaPreviewEl.textContent = summarizeDbSchema(data.db_schema);
    setStatus("Connessione DB verificata", "ok");
  }

  testDbConnectionBtn.disabled = false;
  testDbConnectionBtn.textContent = "Verifica connessione";
});

runDbQueryBtn?.addEventListener("click", async () => {
  const request = dbQueryRequestEl?.value?.trim() || "";
  if (!verifiedDbConnectionId) {
    setStatus("Verifica prima la connessione DB", "warn");
    return;
  }
  if (!request) {
    setStatus("Inserisci SQL o richiesta in linguaggio naturale", "warn");
    return;
  }

  runDbQueryBtn.disabled = true;
  runDbQueryBtn.textContent = "Eseguo...";
  const res = await fetch(apiUrl("/api/db/query"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ connection_id: verifiedDbConnectionId, request }),
  });
  const data = await res.json();
  renderDbQueryResult(data);
  setStatus(data.error ? "Query DB con errore" : "Query DB eseguita", data.error ? "err" : "ok");
  runDbQueryBtn.disabled = false;
  runDbQueryBtn.textContent = "Esegui su DB";
});

resetView();
selectUseCase("it_ops", false);
selectDataSource("csv");
if (location.protocol === "file:") setStatus("Mode file://, usa backend localhost", "warn");

jumpToResultBtn?.addEventListener("click", () => {
  resultAnchorEl?.scrollIntoView({ behavior: "smooth", block: "start" });
});

openResultBtn?.addEventListener("click", () => {
  hideResultModal();
  resultAnchorEl?.scrollIntoView({ behavior: "smooth", block: "start" });
});

closeResultBtn?.addEventListener("click", () => {
  hideResultModal();
});

window.addEventListener("resize", layoutLinks);
window.addEventListener("load", layoutLinks);
setTimeout(layoutLinks, 120);
