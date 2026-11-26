
let editingNoteId = null;

/* Patient Workspace — HealthSphere frontend. */

const $ = (s, r = document) => r.querySelector(s);

const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'
}[c]));

const NOW = new Date('2026-11-23T00:00:00Z');

const age = d => {
  if (!d) return '—';
  const b = new Date(d);
  let a = NOW.getUTCFullYear() - b.getUTCFullYear();
  if (NOW < Date.UTC(NOW.getUTCFullYear(), b.getUTCMonth(), b.getUTCDate())) a--;
  return a;
};

const fd = d => {
  if (!d || d === 'Not available') return 'Not available';
  return new Date(d).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'
  });
};

const ini = n => (n || '?').split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase();

const sv = (d, w = 20, h = 20) =>
  `<svg width="${w}" height="${h}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;

const ic = {
  search: sv('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>'),
  plus: sv('<path d="M12 5v14M5 12h14"/>'),
  up: sv('<path d="M12 16V4M6 10l6-6 6 6M5 20h14"/>'),
  back: sv('<path d="m15 6-6 6 6 6"/>'),
  arrow: sv('<path d="M5 12h14M13 6l6 6-6 6"/>', 24, 24)
};

/* ---------- Patient API Integration ---------- */

function formatPatientDate(value) {
  if (!value) return 'Not available';
  return new Date(value).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric'
  });
}

function getRelativeDate(value) {
  if (!value) return 'Not available';
  const date = new Date(value);
  const days = Math.floor((Date.now() - date.getTime()) / 86400000);
  if (days <= 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} mo ago`;
  return `${Math.floor(months / 12)} yr ago`;
}

function chatStorageKey(patientId) {
  return `hs_chat_${patientId}`;
}

async function loadPatients() {
  const result = await apiRequest('/api/patients/');
  const patients = (result.patients || []).map(patient => ({
    id: String(patient.id),
    name: patient.full_name || '',
    dob: patient.date_of_birth || '',
    sex: patient.gender || 'Not specified',
    bg: patient.blood_group || 'Not specified',
    since: formatPatientDate(patient.created_at),
    upd: getRelativeDate(patient.updated_at || patient.created_at),
    phone: patient.phone || '',
    email: patient.email || '',
    doc: 'Not specified',
    emerg: 'Not provided',
    allergies: Array.isArray(patient.allergies) ? patient.allergies : [],
    cond: Array.isArray(patient.medical_conditions) ? patient.medical_conditions : [],
    meds: [], notes: [], files: [], chat: [],
    conversationId: null,
    chatHistoryLoaded: false,
    tab: 'ask'
  }));
  P.splice(0, P.length, ...patients);
  console.log('Patients loaded:', P.length);
  return patients;
}

function mapBackendDocument(doc) {
  const fileName = doc.file_name || 'Untitled document';
  const extension = fileName.includes('.')
    ? fileName.split('.').pop().toUpperCase().slice(0, 4) : 'FILE';
  const mimeType = doc.mime_type || '';
  const sizeBytes = Number(doc.file_size || 0);
  let documentType = 'Document';
  if (mimeType === 'application/pdf') documentType = 'Lab report';
  else if (mimeType.startsWith('image/')) documentType = 'Image';
  let fileSize = '—';
  if (sizeBytes > 0) {
    fileSize = sizeBytes >= 1048576
      ? (sizeBytes / 1048576).toFixed(1) + ' MB'
      : Math.max(1, Math.round(sizeBytes / 1024)) + ' KB';
  }
  return {
    id: String(doc.id), name: fileName, type: documentType,
    ext: extension, date: doc.created_at ? doc.created_at.slice(0, 10) : '',
    size: fileSize, mime_type: mimeType, file_size: sizeBytes
  };
}

async function loadPatientDetails(patientId) {
  const result = await apiRequest(`/api/patients/${encodeURIComponent(patientId)}`);
  const patient = result.patient || result;
  const notesResult = await apiRequest(`/api/patients/${encodeURIComponent(patientId)}/notes/`);
  const documentsResult = await apiRequest(`/api/patients/${encodeURIComponent(patientId)}/documents`);
  const backendDocuments = documentsResult.documents || documentsResult.data || [];
  const patientFiles = backendDocuments.map(mapBackendDocument);
  const visitNotes = (notesResult.notes || []).map(note => ({
    id: String(note.id), title: note.title || '',
    date: note.visit_date || '', doctor: note.doctor || '', body: note.body || ''
  }));

  const patientRecord = {
    id: String(patient.id), name: patient.full_name || '',
    dob: patient.date_of_birth || '', sex: patient.gender || 'Not specified',
    bg: patient.blood_group || 'Not specified',
    since: formatPatientDate(patient.created_at),
    upd: getRelativeDate(patient.updated_at || patient.created_at),
    phone: patient.phone || '', email: patient.email || '',
    doc: patient.primary_physician || 'Not specified',
    emerg: patient.emergency_contact_name || 'Not provided',
    ephone: patient.emergency_contact_phone || '',
    address: patient.address || '',
    allergies: Array.isArray(patient.allergies) ? patient.allergies : [],
    cond: Array.isArray(patient.medical_conditions) ? patient.medical_conditions : [],
    meds: Array.isArray(patient.medications) ? patient.medications : [],
    notes: visitNotes, files: patientFiles, chat: [],
    conversationId: sessionStorage.getItem(chatStorageKey(String(patient.id))) || null,
    chatHistoryLoaded: false, tab: 'ask'
  };

  const existingIndex = P.findIndex(p => p.id === patientRecord.id);
  if (existingIndex !== -1) P[existingIndex] = patientRecord;
  else P.push(patientRecord);

  console.log('Patient details loaded:', patientRecord);
  console.log('Visit notes loaded:', visitNotes.length);
  console.log('Documents loaded:', patientFiles.length);
  return patientRecord;
}

const P = [];

const src = p => [
  ...p.notes.map(n => ({ ...n, kind: 'NOTE', sub: 'Visit note', name: n.title })),
  ...p.files.map(f => ({ ...f, kind: f.ext, sub: f.type }))
].sort((a, b) => b.date.localeCompare(a.date));

const tint = p => 't' + (P.indexOf(p) % 4);

/* ---------- Home ---------- */

const card = p => `<article class="card">
  <a class="card-link" href="#/patient/${encodeURIComponent(p.id)}">
    <div class="who">
      <span class="av ${tint(p)}">${ini(p.name)}</span>
      <div><b>${esc(p.name)}</b>
        <div class="mut">${age(p.dob)} yrs &middot; ${esc(p.sex)} &middot; Blood ${esc(p.bg)}</div>
      </div>
    </div>
    <p class="cond">${esc(p.cond.join(', ') || 'No conditions recorded')}</p>
    <div class="foot"><span>${p.files.length} files &middot; ${p.notes.length} visits</span>
      <span>Updated ${esc(p.upd)}</span>
    </div>
  </a>
  <div class="card-actions">
    <button class="btn danger" data-act="deletepatient" data-id="${esc(p.id)}">
      Delete patient
    </button>
  </div>
</article>`;

function showDeletePatientConfirmation(patientId) {
  const patient = P.find(item => item.id === patientId);

  if (!patient) {
    toast('Patient not found');
    return;
  }

  open(`
    <header>
      <h2>Delete patient?</h2>
    </header>
    <div class="body">
      <p>You are about to permanently delete:</p>
      <p><strong>${esc(patient.name)}</strong></p>
      <p>This will also delete their uploaded document records, visit notes,
      AI analyses, chat history and associated database data.</p>
      <p><strong>This action cannot be undone.</strong></p>
    </div>
    <footer>
      <button class="btn" data-act="close">Cancel</button>
      <button class="btn danger" data-act="confirmdeletepatient"
        data-id="${esc(patient.id)}">Delete permanently</button>
    </footer>
  `);
}

async function deletePatient(patientId, button) {
  const patient = P.find(item => item.id === patientId);

  if (!patient) {
    toast('Patient not found');
    return;
  }

  if (button) {
    button.disabled = true;
    button.textContent = 'Deleting...';
  }

  try {
    const result = await apiRequest(
      `/api/patients/${encodeURIComponent(patientId)}`,
      { method: 'DELETE' }
    );

    const index = P.findIndex(item => item.id === patientId);
    if (index !== -1) P.splice(index, 1);

    close();
    drawList();

    if (result.storage_cleanup_warning) {
      toast('Patient deleted, but some stored files need cleanup');
    } else {
      toast('Patient deleted successfully');
    }
  } catch (error) {
    if (button) {
      button.disabled = false;
      button.textContent = 'Delete permanently';
    }

    toast(error.message || 'Unable to delete patient');
  }
}

function drawList() {
  const q = ($('#q')?.value || '').toLowerCase();
  const r = P.filter(p => [p.name, p.phone, ...p.cond].join(' ').toLowerCase().includes(q));
  $('#list').innerHTML = r.map(card).join('') ||
    '<p class="empty">No patients match your search. Try a name, condition or phone number.</p>';
}

function home() {
  $('#app').innerHTML = `<section class="wrap">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
      <h1 class="h1">Patients</h1>
      <button class="btn" data-act="logout">Logout</button>
    </div>
    <div class="bar">
      <p class="sub">Each patient is a private workspace — their files, visit notes and an assistant that answers only from that record.</p>
      <div class="tools">
        <label class="search">${ic.search}<input id="q" type="search" placeholder="Search name, condition, phone" aria-label="Search patients"></label>
        <button class="btn pri" data-act="new">${ic.plus} New patient</button>
      </div>
    </div>
    <div class="grid" id="list"></div>
  </section>
  <button class="fab" data-act="new" aria-label="New patient">+</button>`;
  drawList();
}

/* ---------- Detail ---------- */

function detail(p) {
  const S = src(p);
  const tabs = [
    ['ask', 'Ask'], ['visits', 'Visits & notes', p.notes.length],
    ['files', 'Files', p.files.length], ['profile', 'Profile']
  ];

  $('#app').innerHTML = `<section class="wrap">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px">
      <a class="back" href="#/">${ic.back} All patients</a>
      <button class="btn" data-act="logout">Logout</button>
    </div>
    <div class="phead">
      <span class="av big ${tint(p)}">${ini(p.name)}</span>
      <div class="pinfo">
        <h1 class="nm">${esc(p.name)}</h1>
        <p class="mut" style="margin:4px 0 0">${age(p.dob)} yrs · ${esc(p.sex)} · Blood ${esc(p.bg)} · Patient since ${fd(p.since)}</p>
      </div>
      <div class="acts">
        <button class="btn" data-act="upload">${ic.up} Upload files</button>
        <button class="btn pri" data-act="addnote">${ic.plus} Add visit note</button>
      </div>
    </div>
    <div class="tabs" role="tablist">
      ${tabs.map(t => `<button class="tab" role="tab" id="t-${t[0]}" aria-selected="${p.tab === t[0]}" tabindex="${p.tab === t[0] ? 0 : -1}" data-act="tab" data-v="${t[0]}">${t[1]}${t[2] !== undefined ? `<span class="cnt">${t[2]}</span>` : ''}</button>`).join('')}
    </div>
    <div id="pane" role="tabpanel">${pane(p, S)}</div>
  </section>`;

  $('.tab[aria-selected=true]')?.scrollIntoView({ inline: 'center', block: 'nearest' });
  if (p.tab === 'ask') {
    drawChat(p);
    restoreChatHistory(p);
  }
}

const row = s => `<button class="src" data-act="src" data-id="${esc(s.id)}" data-k="${esc(s.kind)}">
  <span class="bdg">${esc(s.kind)}</span>
  <span class="sbody"><b>${esc(s.name)}</b><span>${esc(s.sub)} · ${fd(s.date)}</span></span>
</button>`;

function pane(p, S) {
if (p.tab === 'ask') {
  return `<div class="ask">
    <div class="chat">
      <div class="msgs" id="msgs" aria-live="polite"></div>
      <div class="inp">
        <div class="row">
          <textarea id="ta" rows="1" placeholder="e.g. How has HbA1c changed since the last three visits?" aria-label="Ask a question about this patient"></textarea>
          <button class="send" data-act="send" aria-label="Send question">${ic.arrow}</button>
        </div>
        <p class="fine">Grounded in this patient's record only. Always verify against source documents before clinical decisions.</p>
      </div>
    </div>

    <aside class="side">
      <div class="box" style="margin:0">
        <h3 class="lbl">Knowledge <small>${p.files.length} files · ${p.notes.length} notes</small></h3>
        <div class="klist">${S.map(row).join('') || '<p class="mut">No files or notes yet. Add a visit note or upload a report to get started.</p>'}</div>
        <div class="pair">
          <button class="btn" data-act="upload">Add files</button>
          <button class="btn" data-act="addnote">Add note</button>
        </div>
      </div>
    </aside>
  </div>`;
}


  if (p.tab === 'visits') {
    return `<div class="tl">${p.notes.map(n => `<details>
      <summary>${esc(n.title)}<small>${fd(n.date)}${n.doctor ? ' · ' + esc(n.doctor) : ''}</small></summary>
      <p>${esc(n.body)}</p>
      <div class="pair" style="margin:12px 0">
        <button class="btn" data-act="editnote" data-id="${esc(n.id)}">Edit</button>
        <button class="btn" data-act="deletenote" data-id="${esc(n.id)}">Delete</button>
      </div>
    </details>`).join('') || '<p class="mut">No visit notes yet.</p>'}</div>`;
  }

  if (p.tab === 'files') {
    return `<div class="box" style="margin-top:24px">
      ${p.files.map(f => `<div class="frow">
        <span class="bdg">${esc(f.ext)}</span>
        <b style="font-weight:500;overflow-wrap:anywhere">${esc(f.name)}</b>
        <span class="meta">${esc(f.type)} · ${fd(f.date)}</span>
        <span class="meta">${esc(f.size)}</span>
        <button class="btn" data-act="analyze" data-id="${esc(f.id)}">Analyze</button>
        <button class="btn" data-act="history" data-id="${esc(f.id)}">History</button>
        <button class="btn" data-act="src" data-id="${esc(f.id)}" data-k="${esc(f.ext)}">Preview</button>
      </div>`).join('') || '<p class="mut">No files yet.</p>'}
      <div class="drop">Drag files here or <button class="btn" data-act="upload" style="margin-left:6px">Tap to upload</button></div>
    </div>`;
  }

  const kv = o => `<dl class="kv">${o.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v || '\u2014')}</dd>`).join('')}</dl>`;
  return `<div style="display:flex;justify-content:flex-end;margin-bottom:12px">
    <button class="btn pri" data-act="editpatient">Edit patient</button>
  </div>
  <div class="pg">
    <div class="box"><h3 class="lbl">Identity</h3>${kv([['Name', p.name], ['Born', fd(p.dob)], ['Sex', p.sex], ['Blood group', p.bg]])}</div>
    <div class="box"><h3 class="lbl">Contact</h3>${kv([['Phone', p.phone], ['Email', p.email], ['Address', p.address]])}</div>
    <div class="box"><h3 class="lbl">Emergency contact</h3>${kv([['Name', p.emerg], ['Phone', p.ephone]])}</div>
    <div class="box"><h3 class="lbl">Medical baseline</h3>${kv([['Allergies', p.allergies.join(', ')], ['Conditions', p.cond.join(', ')], ['Medications', p.meds.join('; ')]])}</div>
    <div class="box"><h3 class="lbl">Primary physician</h3>${kv([['Doctor', p.doc]])}</div>
  </div>`;
}

/* ---------- RAG Chatbot and citations ---------- */

const CHIPS = [
  'Summarise this patient’s history',
  'What medications are they on?',
  'Any known allergies?',
  'What happened at the last visit?',
  'Show the latest lab results',
  'How has blood pressure changed?'
];

/*
 * Normalize the complete citation structure returned by the backend.
 * Keep document and chunk metadata so citations survive chat restoration.
 */

function normalizeChatSources(sources) {
  if (!Array.isArray(sources)) return [];

  const normalized = sources.map((source, index) => ({
    source_index: Number(source.source_index || index + 1),
    document_id: String(source.document_id || source.id || ''),
    file_name: source.file_name || source.name || 'Source document',
    similarity: source.similarity ?? null,
    chunks: Array.isArray(source.chunks)
      ? source.chunks.map(chunk => ({
          chunk_id: String(chunk.chunk_id || ''),
          chunk_index: Number(chunk.chunk_index ?? 0),
          similarity: chunk.similarity ?? null,
          matched_content: String(chunk.matched_content || '')
        }))
      : []
  }));

  const unique = new Map();
  normalized.forEach(source => {
    const key = source.document_id || `${source.source_index}-${source.file_name}`;
    if (!unique.has(key)) unique.set(key, source);
  });

  return [...unique.values()];
}

/* Find a source by its source number and chunk number. */

function findCitationSource(sources, sourceIndex, chunkIndex) {
  const source = (sources || []).find(
    item => Number(item.source_index) === Number(sourceIndex)
  );

  if (!source) return null;

  const chunk = (source.chunks || []).find(
    item => Number(item.chunk_index) === Number(chunkIndex)
  );

  if (!chunk) return null;

  return { source, chunk };
}

/*
 * Convert only recognized citation markers into buttons.
 * All other answer text is HTML-escaped before it is displayed.
 */


/* Render Markdown safely and convert recognized citations into inline buttons. */

function renderChatAnswer(answer, sources) {
  const text = String(answer || "");
  const citationPattern = /\[Source\s+(\d+)\s*,\s*chunk\s+(\d+)\]/gi;
  const citations = [];

  // Replace citations temporarily so Markdown cannot interpret them as links.
  const markdown = text.replace(citationPattern, (original, source, chunk) => {
    const sourceIndex = Number(source);
    const chunkIndex = Number(chunk);
    const found = findCitationSource(sources, sourceIndex, chunkIndex);
    const token = `HEALTHSPHERECITATIONTOKEN${citations.length}END`;

    citations.push({
      token,
      sourceIndex,
      chunkIndex,
      available: Boolean(found)
    });

    return token;
  });

  let html;

  if (window.marked && window.DOMPurify) {
    html = window.marked.parse(markdown, {
      gfm: true,
      breaks: false
    });

    // Never insert unsanitized model-generated HTML.
    html = window.DOMPurify.sanitize(html, {
      USE_PROFILES: { html: true }
    });
  } else {
    html = `<p>${esc(markdown)}</p>`;
  }

  // Restore citations as small, clickable references.
  citations.forEach(citation => {
    const button = citation.available
      ? `<button type="button" class="inline-citation"
          data-act="chunkcite"
          data-source="${citation.sourceIndex}"
          data-chunk="${citation.chunkIndex}"
          title="View cited source">
          [${citation.sourceIndex}]
        </button>`
      : `<span class="citation-unavailable">[${citation.sourceIndex}]</span>`;

    html = html.replace(citation.token, button);
  });

  return `<div class="answer-text">${html}</div>`;
}


/* Render a clean source list below the assistant answer. */

function renderChatSources(sources) {
  const uniqueSources = normalizeChatSources(sources);
  if (!uniqueSources.length) return "";

  return `
    <section class="cites" aria-label="Answer sources">
      <div class="citation-heading">Sources</div>
      <div class="cite-list">
        ${uniqueSources.map(source => `
          <article class="cite-card">
            <div class="cite-card-main">
              <span class="cite-number">${source.source_index}</span>
              <span class="cite-filename">${esc(source.file_name)}</span>
            </div>
            ${source.document_id ? `
              <button type="button" class="cite-open"
                data-act="cite"
                data-id="${esc(source.document_id)}"
                data-name="${esc(source.file_name)}">
                View source
              </button>
            ` : ""}
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

/* Show the exact retrieved chunk in a citation detail modal. */

function showChunkCitation(p, sources, sourceIndex, chunkIndex) {
  const found = findCitationSource(sources, sourceIndex, chunkIndex);

  if (!found) {
    toast('Citation details are unavailable');
    return;
  }

  const { source, chunk } = found;
  const content = chunk.matched_content || 'Matched text was not returned by the API.';

  open(`<header>
      <h2>Source ${source.source_index}, chunk ${chunk.chunk_index}</h2>
      <p class="mut">${esc(source.file_name)}</p>
    </header>
    <div class="body">
      <div class="box" style="margin:0 0 16px">
        <h3 class="lbl">Retrieved source text</h3>
        <div style="white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.7">${esc(content)}</div>
      </div>
      <p class="note">This is the text retrieved from the indexed document for this answer. Verify clinical details against the original document.</p>
    </div>
    <footer>
      <button class="btn" data-act="close">Close</button>
      ${source.document_id ? `<button class="btn pri" data-act="cite" data-id="${esc(source.document_id)}" data-name="${esc(source.file_name)}">Open original document</button>` : ''}
    </footer>`);
}

function drawChat(p) {
  const m = $('#msgs');
  if (!m) return;

  if (!p.chat.length) {
    m.innerHTML = `<div class="hero">
      <h2>Ask about ${esc(p.name.split(' ')[0])}’s health</h2>
      <p>Answers are generated using this patient's indexed records, uploaded documents and available clinical notes, with source references you can check.</p>
      <div class="chips">
        ${CHIPS.map(c => `<button class="chip" data-act="chip" data-q="${esc(c)}">${esc(c)}</button>`).join('')}
      </div>
    </div>`;
    return;
  }

  m.innerHTML = p.chat.map(message => {
    if (message.typing) return '<div class="bub a dots"><span></span><span></span><span></span></div>';

    if (message.r === 'u') {
      return `<div class="bub u">${esc(message.t)}</div>`;
    }

    return `<div class="bub a">
      ${renderChatAnswer(message.t, message.sources)}
      ${renderChatSources(message.sources)}
    </div>`;
  }).join('');

  // Render LaTeX and medical formulas after inserting the answer.
  if (window.MathJax && window.MathJax.typesetPromise) {
    window.MathJax.typesetPromise([m]).catch(error => {
      console.warn("MathJax rendering issue:", error);
    });
  }

  m.scrollTop = m.scrollHeight;
}

/* Restore a previously saved conversation when reopening a patient. */

async function restoreChatHistory(p) {
  if (!p.conversationId || p.chatHistoryLoaded || p.chatHistoryLoading) return;

  p.chatHistoryLoading = true;

  try {
    const result = await apiRequest(
      `/api/patients/${encodeURIComponent(p.id)}/chat-history?conversation_id=${encodeURIComponent(p.conversationId)}`
    );

    const messages = result.messages || [];

    p.chat = messages
      .filter(message => message.role === 'user' || message.role === 'assistant')
      .map(message => ({
        r: message.role === 'user' ? 'u' : 'a',
        t: message.content || '',
        sources: normalizeChatSources(message.sources)
      }));

    p.chatHistoryLoaded = true;

    if (curr() === p && p.tab === 'ask') drawChat(p);

    console.log('Chat history restored:', messages.length);

  } catch (error) {
    console.error('Chat history restoration failed:', error);
    toast('Unable to restore previous chat history');
  } finally {
    p.chatHistoryLoading = false;
  }
}

/* Send a question to the real backend RAG chatbot. */

async function ask(p, question) {
  const q = question.trim();
  if (!q) return;

  if (q.length < 3) {
    toast('Please enter at least 3 characters');
    return;
  }

  if (q.length > 1000) {
    toast('Please keep your question under 1000 characters');
    return;
  }

  const pendingMessage = { typing: 1 };
  p.chat.push({ r: 'u', t: q }, pendingMessage);
  drawChat(p);

  try {
    const requestBody = { question: q, match_count: 5 };
    if (p.conversationId) requestBody.conversation_id = p.conversationId;

    const result = await apiRequest(
      `/api/patients/${encodeURIComponent(p.id)}/chat`,
      { method: 'POST', body: JSON.stringify(requestBody) }
    );

    console.log('RAG chatbot response:', result);

    if (result.conversation_id) {
      p.conversationId = result.conversation_id;
      sessionStorage.setItem(chatStorageKey(p.id), p.conversationId);
    }

    const assistantMessage = {
      r: 'a',
      t: result.answer || 'The assistant did not return an answer.',
      sources: normalizeChatSources(result.sources)
    };

    const pendingIndex = p.chat.indexOf(pendingMessage);
    if (pendingIndex !== -1) p.chat.splice(pendingIndex, 1, assistantMessage);
    else p.chat.push(assistantMessage);

    if (curr() === p && p.tab === 'ask') drawChat(p);

    if (result.saved === false) {
      toast('Answer received, but chat saving was not confirmed');
    }

  } catch (error) {
    console.error('RAG chatbot request failed:', error);
    const pendingIndex = p.chat.indexOf(pendingMessage);

    if (pendingIndex !== -1) {
      p.chat.splice(pendingIndex, 1, {
        r: 'a',
        t: `I couldn't process your question. ${error.message}`,
        sources: []
      });
    }

    if (curr() === p && p.tab === 'ask') drawChat(p);
    toast('Unable to get an answer from the assistant');
  }
}

/* ---------- Overlays ---------- */

const layer = () => $('#layer');

function open(html, cls = '') {
  layer().innerHTML = `<div class="ov ${cls}" data-act="bg"><div class="md" role="dialog" aria-modal="true">${html}</div></div>`;
  document.body.style.overflow = 'hidden';
  $('.md input,.md textarea,.md button', layer())?.focus();
}

function close() {
  layer().innerHTML = '';
  document.body.style.overflow = '';
}

function toast(t) {
  const e = $('#toast');
  if (!e) return;
  e.textContent = t;
  e.classList.add('on');
  clearTimeout(toast.t);
  toast.t = setTimeout(() => e.classList.remove('on'), 2600);
}

const fld = (id, l, ph = '', t = 'text') =>
  `<label>${l}<input id="${id}" type="${t}" placeholder="${ph}"></label>`;

const foot = ok => `<footer>
  <button class="btn" data-act="close">Cancel</button>
  <button class="btn pri" data-act="${ok[0]}">${ok[1]}</button>
</footer>`;

function newPatient() {
  open(`<header><h2>New patient</h2>
    <p class="mut">Basic information starts the record. Everything here is searchable by the assistant.</p></header>
    <div class="body">
      <div class="gh">Identity</div>
      <div class="f"><label>Full name *<input id="nm" placeholder="e.g. Anita Sharma" required><span class="err" id="nme"></span></label></div>
      <div class="f c3">
        ${fld('dob', 'Date of birth', '', 'date')}
        <label>Sex<select id="sx"><option value="">Select</option><option>Female</option><option>Male</option><option>Other</option></select></label>
        <label>Blood group<select id="bg"><option>Unknown</option>${['A+', 'A−', 'B+', 'B−', 'AB+', 'AB−', 'O+', 'O−'].map(b => `<option>${b}</option>`).join('')}</select></label>
      </div>
      <div class="gh">Contact</div>
      <div class="f c2">${fld('ph', 'Phone', '+91', 'tel')}${fld('em', 'Email', '', 'email')}</div>
      <div class="f">${fld('ad', 'Address')}</div>
      <div class="f c2">${fld('en', 'Emergency contact name', 'Name (relation)')}${fld('ep', 'Emergency contact phone', '', 'tel')}</div>
      <div class="gh">Medical baseline</div>
      <div class="f c2">${fld('al', 'Allergies', 'Comma separated, or “None known”')}${fld('co', 'Chronic conditions', 'Comma separated')}</div>
      <div class="f"><label>Current medications<textarea id="me" rows="3" placeholder="One per line — name, dose, frequency"></textarea></label></div>
      <div class="f c2">${fld('dc', 'Primary physician')}<label>Initial documents (optional)<input id="fl" type="file" multiple></label></div>
      <p class="note">Only upload documents you have consent to store.</p>
    </div>${foot(['create', 'Create patient'])}`);
}


function editPatient(p) {
  open(`<header><h2>Edit patient</h2>
    <p class="mut">Update this patient's personal and medical information.</p></header>
    <div class="body">
      <div class="gh">Identity</div>
      <div class="f"><label>Full name *<input id="pnm" required><span class="err" id="pnme"></span></label></div>
      <div class="f c3">
        ${fld('pdob', 'Date of birth', '', 'date')}
        <label>Sex<select id="psx"><option value="">Select</option><option>Female</option><option>Male</option><option>Other</option></select></label>
        <label>Blood group<select id="pbg"><option value="Unknown">Unknown</option>${['A+', 'A\u2212', 'B+', 'B\u2212', 'AB+', 'AB\u2212', 'O+', 'O\u2212'].map(b => `<option>${b}</option>`).join('')}</select></label>
      </div>
      <div class="gh">Contact</div>
      <div class="f c2">${fld('pph', 'Phone', '+91', 'tel')}${fld('pem', 'Email', '', 'email')}</div>
      <div class="f">${fld('pad', 'Address')}</div>
      <div class="f c2">${fld('pen', 'Emergency contact name', 'Name (relation)')}${fld('pep', 'Emergency contact phone', '', 'tel')}</div>
      <div class="gh">Medical baseline</div>
      <div class="f c2">${fld('pal', 'Allergies', 'Comma separated')}${fld('pco', 'Chronic conditions', 'Comma separated')}</div>
      <div class="f"><label>Current medications<textarea id="pme" rows="3" placeholder="One medication per line"></textarea></label></div>
      <div class="f">${fld('pdc', 'Primary physician')}</div>
    </div>${foot(['updatepatient', 'Save changes'])}`);

  const values = {
    pnm: p.name,
    pdob: p.dob,
    psx: p.sex === 'Not specified' ? '' : p.sex,
    pbg: p.bg === 'Not specified' ? 'Unknown' : p.bg,
    pph: p.phone,
    pem: p.email,
    pad: p.address,
    pen: p.emerg === 'Not provided' ? '' : p.emerg,
    pep: p.ephone,
    pal: p.allergies.join(', '),
    pco: p.cond.join(', '),
    pme: p.meds.join('\n'),
    pdc: p.doc === 'Not specified' ? '' : p.doc
  };

  Object.entries(values).forEach(([id, value]) => {
    const field = $('#' + id);
    if (field) field.value = value || '';
  });
}

function addNote(p) {
  open(`<header><h2>Add visit note</h2></header>
    <div class="body">
      <div class="f c2">${fld('nd', 'Date', '', 'date')}${fld('nt', 'Title', 'e.g. Follow-up')}</div>
      <div class="f">${fld('ndr', 'Doctor', p.doc)}<label>Notes<textarea id="nb" rows="5"></textarea></label></div>
    </div>${foot(['savenote', 'Save note'])}`);
  $('#nd').value = '2026-11-23';
}

function editNote(p, noteId) {
  const note = p.notes.find(n => String(n.id) === String(noteId));
  if (!note) {
    toast('Visit note not found');
    return;
  }

  editingNoteId = note.id;
  open(`<header><h2>Edit visit note</h2></header>
    <div class="body">
      <div class="f c2">${fld('nd', 'Date', '', 'date')}${fld('nt', 'Title', 'Visit title')}</div>
      <div class="f">${fld('ndr', 'Doctor', '')}<label>Notes<textarea id="nb" rows="5"></textarea></label></div>
    </div>${foot(['updatenote', 'Update note'])}`);

  $('#nd').value = note.date || '';
  $('#nt').value = note.title || '';
  $('#ndr').value = note.doctor === 'Not specified' ? '' : (note.doctor || '');
  $('#nb').value = note.body || '';
}

function upload() {
  open(`<header><h2>Upload files</h2></header>
    <div class="body"><div class="f">
      <label>Document type<select id="ut"><option>Lab report</option><option>Prescription</option><option>Imaging</option><option>Other</option></select></label>
      <label>Files<input id="uf" type="file" multiple></label>
    </div><p class="note">Only upload documents you have consent to store.</p></div>
    ${foot(['savefiles', 'Upload'])}`);
}

/* ---------- Secure document preview ---------- */

async function preview(p, id, k) {
  const s = src(p).find(x => String(x.id) === String(id));
  if (!s) {
    toast('Document not found');
    return;
  }

  open(`<header><h2 style="font-size:22px;overflow-wrap:anywhere">${esc(s.name)}</h2>
    <p class="mut">${esc(s.sub || s.type || 'Document')} · ${fd(s.date)}</p></header>
    <div class="body" id="previewContent"><p class="mut">Generating secure preview link...</p></div>
    ${foot(['close', 'Close'])}`, 'dr');

  try {
    const result = await apiRequest(
      `/api/patients/${encodeURIComponent(p.id)}/documents/${encodeURIComponent(id)}/download`
    );
    if (!result.download_url) throw new Error('Secure download URL was not returned.');

    const previewContent = $('#previewContent');
    if (!previewContent) return;

    const mimeType = s.mime_type || '';
    const extension = (s.ext || '').toLowerCase();
    const safeUrl = esc(result.download_url);

    if (mimeType.startsWith('image/') || ['png', 'jpg', 'jpeg', 'webp'].includes(extension)) {
      previewContent.innerHTML = `<div style="text-align:center">
        <img src="${safeUrl}" alt="${esc(s.name)}" style="display:block;max-width:100%;max-height:65vh;object-fit:contain;margin:auto;border-radius:10px">
      </div>`;
    } else if (mimeType === 'application/pdf' || extension === 'pdf') {
      previewContent.innerHTML = `<iframe src="${safeUrl}" title="${esc(s.name)}" style="width:100%;height:65vh;border:0;border-radius:10px"></iframe>`;
    } else {
      previewContent.innerHTML = `<p>Preview is not supported for this file type.</p><a href="${safeUrl}" target="_blank" rel="noopener noreferrer">Open document</a>`;
    }
  } catch (error) {
    console.error('Document preview failed:', error);
    const previewContent = $('#previewContent');
    if (previewContent) {
      previewContent.innerHTML = `<p class="mut">Unable to load this document preview.</p><p class="err">${esc(error.message)}</p>`;
    }
    toast('Unable to preview document');
  }
}

/* ---------- AI document analysis ---------- */

function analysisModalHeader(fileName, subtitle = '') {
  return `<header><h2 style="font-size:22px;overflow-wrap:anywhere">AI document analysis</h2>
    <p class="mut">${esc(fileName)}${subtitle ? ' · ' + esc(subtitle) : ''}</p></header>`;
}

function renderAnalysisResult(result, fileName) {
  const summary = result.document_summary || result.analysis_text || result.summary || 'The analysis endpoint did not return a summary.';
  const model = result.ai_model || result.model_name || 'Not provided';
  const disclaimer = result.disclaimer || 'This AI-generated summary is for informational support only. It is not a medical diagnosis or a substitute for professional medical advice.';

  return `${analysisModalHeader(fileName, 'Analysis result')}
    <div class="body" id="analysisContent">
      <div class="box" style="margin:0 0 16px"><h3 class="lbl">Document summary</h3>
        <div style="white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.65">${esc(summary)}</div></div>
      <div class="box" style="margin:0 0 16px"><h3 class="lbl">AI model</h3><p>${esc(model)}</p></div>
      <div class="box" style="margin:0"><h3 class="lbl">Important disclaimer</h3>
        <p style="white-space:pre-wrap;line-height:1.6">${esc(disclaimer)}</p></div>
      ${result.analysis_id ? `<p class="note" style="margin-top:12px">Saved analysis ID: ${esc(result.analysis_id)}</p>` : ''}
    </div>${foot(['close', 'Close'])}`;
}

async function analyzeDocument(p, documentId) {
  const file = p.files.find(f => String(f.id) === String(documentId));
  if (!file) {
    toast('Document not found');
    return;
  }

  open(`${analysisModalHeader(file.name, 'Please wait')}
    <div class="body" id="analysisContent"><p class="mut">Gemini is analyzing this document. Please wait...</p>
    <p class="note">Do not close this window while the request is running.</p></div>${foot(['close', 'Close'])}`);

  try {
    const result = await apiRequest(
      `/api/patients/${encodeURIComponent(p.id)}/documents/${encodeURIComponent(documentId)}/analyze`,
      { method: 'POST' }
    );
    console.log('AI document analysis completed:', result);
    if (!$('#analysisContent')) return;
    layer().innerHTML = `<div class="ov" data-act="bg"><div class="md" role="dialog" aria-modal="true">${renderAnalysisResult(result, file.name)}</div></div>`;
    toast('Document analysis completed and saved');
  } catch (error) {
    console.error('AI document analysis failed:', error);
    const content = $('#analysisContent');
    if (content) {
      content.innerHTML = `<p class="err">Unable to analyze this document.</p><p class="mut">${esc(error.message)}</p><p class="note">You can close this window and try again.</p>`;
    }
    toast('AI document analysis failed');
  }
}

/* ---------- Saved AI analysis history ---------- */

function formatAnalysisDate(value) {
  if (!value) return 'Date not available';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Date not available';
  return date.toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
  });
}

async function loadDocumentAnalysisHistory(p, documentId) {
  const file = p.files.find(f => String(f.id) === String(documentId));
  if (!file) {
    toast('Document not found');
    return;
  }

  open(`${analysisModalHeader(file.name, 'Saved analysis history')}
    <div class="body" id="analysisHistoryContent"><p class="mut">Loading saved analyses...</p></div>
    ${foot(['close', 'Close'])}`);

  try {
    const result = await apiRequest(
      `/api/patients/${encodeURIComponent(p.id)}/documents/${encodeURIComponent(documentId)}/analyses`
    );
    const content = $('#analysisHistoryContent');
    if (!content) return;
    const analyses = result.analyses || [];

    if (!analyses.length) {
      content.innerHTML = `<p class="mut">No saved analyses found for this document yet.</p><p class="note">Select Analyze to generate and save the first AI analysis.</p>`;
      return;
    }

    content.innerHTML = `<p class="mut" style="margin-bottom:16px">${analyses.length} saved analysis${analyses.length === 1 ? '' : 'es'} · Newest first</p>
      ${analyses.map((item, index) => `<div class="box" style="margin:0 0 14px">
        <h3 class="lbl">Analysis ${analyses.length - index}</h3>
        <p class="meta" style="margin-bottom:12px">${esc(formatAnalysisDate(item.created_at))}</p>
        <div style="white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.65">${esc(item.analysis_text || 'No analysis text was saved.')}</div>
        <div class="sec">AI model</div><p>${esc(item.model_name || 'Not provided')}</p>
      </div>`).join('')}
      <p class="note">These are previously saved results. Opening this history does not run Gemini again.</p>`;
  } catch (error) {
    console.error('Unable to load analysis history:', error);
    const content = $('#analysisHistoryContent');
    if (content) content.innerHTML = `<p class="err">Unable to load saved analyses.</p><p class="mut">${esc(error.message)}</p>`;
    toast('Unable to load analysis history');
  }
}

/* ---------- Backend API & Authentication ---------- */

const API_BASE = (window.HEALTHSPHERE_CONFIG?.API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');
let authToken = sessionStorage.getItem('hs_access_token') || '';
let authUser = null;

async function apiRequest(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;
  if (options.body && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.detail || result.message || 'Something went wrong');
  return result;
}

function showAuth(mode = 'login') {
  const signup = mode === 'signup';
  $('#app').innerHTML = '';

  open(`<header><h2>${signup ? 'Create your account' : 'Welcome to Patient Workspace'}</h2>
    <p class="mut">${signup ? 'Create an account to access your private patient workspace.' : 'Sign in to access your patient records.'}</p></header>
    <form id="authForm"><div class="body">
      <div class="f"><label>Email address<input id="authEmail" type="email" placeholder="you@example.com" required></label></div>
      <div class="f"><label>Password<input id="authPassword" type="password" placeholder="Enter your password" minlength="8" required></label></div>
      <p class="err" id="authError"></p><p class="note">Demo project — use fictional patient data only.</p>
    </div>
    <footer><button class="btn" type="button" id="authToggle">${signup ? 'Back to login' : 'Create account'}</button>
    <button class="btn pri" type="submit" id="authSubmit">${signup ? 'Sign up' : 'Login'}</button></footer></form>`);

  $('#authToggle').addEventListener('click', () => showAuth(signup ? 'login' : 'signup'));

  $('#authForm').addEventListener('submit', async event => {
    event.preventDefault();
    const email = $('#authEmail').value.trim();
    const password = $('#authPassword').value;
    const submitButton = $('#authSubmit');
    const errorElement = $('#authError');
    submitButton.disabled = true;
    submitButton.textContent = 'Please wait...';
    errorElement.textContent = '';

    try {
      if (signup) {
        const result = await apiRequest('/api/auth/signup', {
          method: 'POST', body: JSON.stringify({ email, password })
        });
        showAuth('login');
        toast(result.message || 'Signup submitted successfully');
        return;
      }

      const result = await apiRequest('/api/auth/login', {
        method: 'POST', body: JSON.stringify({ email, password })
      });
      authToken = result.access_token;
      authUser = result.user;
      sessionStorage.setItem('hs_access_token', authToken);
      close();

      try {
        authUser = await apiRequest('/api/auth/me');
        P.splice(0, P.length);
        await loadPatients();
        toast('Login successful');
        route();
      } catch (error) {
        console.error('Login initialization failed:', error);
        authToken = '';
        authUser = null;
        sessionStorage.removeItem('hs_access_token');
        toast('Unable to load your records');
        showAuth('login');
      }
    } catch (error) {
      errorElement.textContent = error.message;
    } finally {
      if ($('#authSubmit')) {
        $('#authSubmit').disabled = false;
        $('#authSubmit').textContent = signup ? 'Sign up' : 'Login';
      }
    }
  });
}

async function initializeApp() {
  console.log('HealthSphere initialization started');
  if (!authToken) {
    route();
    return;
  }

  try {
    authUser = await apiRequest('/api/auth/me');
    console.log('Authentication verified:', authUser.email);
    P.splice(0, P.length);
    await loadPatients();
  } catch (error) {
    console.error('Initialization failed:', error);
    if (error.message.toLowerCase().includes('authentication') || error.message.toLowerCase().includes('token')) {
      authToken = '';
      authUser = null;
      sessionStorage.removeItem('hs_access_token');
      toast('Your session has expired. Please login again.');
    } else {
      toast('Unable to load patient records.');
    }
  }
  route();
}

function logout() {
  authToken = '';
  authUser = null;
  sessionStorage.removeItem('hs_access_token');
  location.hash = '#/';
  route();
}

/* ---------- State & Routing ---------- */

const curr = () => {
  const match = location.hash.match(/^#\/patient\/([^/]+)/);
  if (!match) return null;
  const patientId = decodeURIComponent(match[1]);
  return P.find(p => p.id === patientId) || null;
};

let routeRequestId = 0;

async function route() {
  close();
  const currentRequest = ++routeRequestId;

  if (!authToken) {
    showAuth('login');
    return;
  }

  const match = location.hash.match(/^#\/patient\/([^/]+)/);
  if (!match) {
    home();
    scrollTo(0, 0);
    return;
  }

  const patientId = decodeURIComponent(match[1]);
  $('#app').innerHTML = `<section class="wrap"><a class="back" href="#/">${ic.back} All patients</a>
    <div class="box" style="margin-top:24px;text-align:center;padding:40px"><p class="mut">Loading patient record...</p></div></section>`;

  try {
    const patient = await loadPatientDetails(patientId);
    if (currentRequest !== routeRequestId) return;
    if (!location.hash.includes(encodeURIComponent(patientId))) return;
    detail(patient);
    scrollTo(0, 0);
  } catch (error) {
    console.error('Unable to load patient details:', error);
    if (currentRequest !== routeRequestId) return;
    $('#app').innerHTML = `<section class="wrap"><a class="back" href="#/">${ic.back} All patients</a>
      <div class="box" style="margin-top:24px"><h2>Unable to load patient</h2>
      <p class="mut">${esc(error.message)}</p><button class="btn pri" onclick="location.hash='#/'">Return to patients</button></div></section>`;
    toast('Unable to load patient record');
  }
}

addEventListener('hashchange', route);
const list = v => v.split(',').map(x => x.trim()).filter(Boolean);

/* ---------- Click events ---------- */

document.addEventListener('click', e => {
  const b = e.target.closest('[data-act]');
  if (!b) return;
  const a = b.dataset.act;
  const p = curr();

  if (a === 'bg') {
    if (e.target === b) close();
    return;
  }

  ({
    close,
    logout,
    new: newPatient,
    addnote: () => addNote(p),
    upload,
    deletepatient: () => showDeletePatientConfirmation(b.dataset.id),
    confirmdeletepatient: () => deletePatient(b.dataset.id, b),
    editpatient: () => { if (p) editPatient(p); },

    tab: () => {
      if (!p) return;
      p.tab = b.dataset.v;
      detail(p);
      $('.tab[aria-selected=true]')?.focus();
    },

    chip: () => { if (p) ask(p, b.dataset.q); },

    send: () => {
      if (!p) return;
      const t = $('#ta');
      if (!t) return;
      const question = t.value;
      t.value = '';
      t.style.height = '';
      ask(p, question);
    },

    src: () => { if (p) preview(p, b.dataset.id, b.dataset.k); },

    analyze: () => { if (p) analyzeDocument(p, b.dataset.id); },

    history: () => { if (p) loadDocumentAnalysisHistory(p, b.dataset.id); },

    cite: () => {
      if (!p) return;
      const documentId = b.dataset.id;
      if (!documentId) {
        toast('Source document ID is unavailable');
        return;
      }
      const file = p.files.find(f => String(f.id) === String(documentId));
      if (!file) {
        toast('The cited document is not available in this patient workspace');
        return;
      }
      preview(p, file.id, file.ext);
    },

    chunkcite: () => {
      if (!p) return;
      const sourceIndex = Number(b.dataset.source);
      const chunkIndex = Number(b.dataset.chunk);

      const message = p.chat.find(item =>
        item.r === 'a' &&
        findCitationSource(item.sources, sourceIndex, chunkIndex)
      );

      if (!message) {
        toast('Citation details are unavailable in this conversation');
        return;
      }

      showChunkCitation(p, message.sources, sourceIndex, chunkIndex);
    },

    create: async () => {
      const n = $('#nm').value.trim();
      if (!n) {
        $('#nme').textContent = 'Enter the patient’s full name.';
        $('#nm').focus();
        return;
      }

      const createButton = b;
      createButton.disabled = true;
      createButton.textContent = 'Saving...';

      try {
        const patientData = {
          full_name: n,
          date_of_birth: $('#dob').value || null,
          gender: $('#sx').value || null,
          blood_group: $('#bg').value === 'Unknown' ? null : $('#bg').value,
          phone: $('#ph').value.trim() || null,
          email: $('#em').value.trim() || null,
          address: $('#ad').value.trim() || null,
          emergency_contact_name: $('#en').value.trim() || null,
          emergency_contact_phone: $('#ep').value.trim() || null,
          primary_physician: $('#dc').value.trim() || null,
          allergies: list($('#al').value),
          medical_conditions: list($('#co').value),
          medications: $('#me').value.split(/\r?\n/).map(x => x.trim()).filter(Boolean),
          notes: null
        };

        const result = await apiRequest('/api/patients/', {
          method: 'POST', body: JSON.stringify(patientData)
        });

        console.log('Patient created in backend:', result);
        await loadPatients();
        const newPatientRecord = P.find(patient => patient.id === String(result.patient.id));
        close();
        location.hash = newPatientRecord ? '#/patient/' + newPatientRecord.id : '#/';
        toast('Patient created successfully');
      } catch (error) {
        console.error('Patient creation failed:', error);
        $('#nme').textContent = error.message;
        toast('Unable to create patient');
        createButton.disabled = false;
        createButton.textContent = 'Create patient';
      }
    },

    updatepatient: async () => {
      const name = $('#pnm').value.trim();

      if (name.length < 2) {
        $('#pnme').textContent = 'Enter a valid full name (at least 2 characters).';
        $('#pnm').focus();
        return;
      }

      const saveButton = b;
      saveButton.disabled = true;
      saveButton.textContent = 'Saving...';

      try {
        const patientData = {
          full_name: name,
          date_of_birth: $('#pdob').value || null,
          gender: $('#psx').value || null,
          blood_group: $('#pbg').value === 'Unknown' ? null : $('#pbg').value,
          phone: $('#pph').value.trim() || null,
          email: $('#pem').value.trim() || null,
          address: $('#pad').value.trim() || null,
          emergency_contact_name: $('#pen').value.trim() || null,
          emergency_contact_phone: $('#pep').value.trim() || null,
          primary_physician: $('#pdc').value.trim() || null,
          allergies: list($('#pal').value),
          medical_conditions: list($('#pco').value),
          medications: $('#pme').value.split(/\r?\n/).map(x => x.trim()).filter(Boolean)
        };

        await apiRequest(`/api/patients/${encodeURIComponent(p.id)}`, {
          method: 'PATCH',
          body: JSON.stringify(patientData)
        });

        const updatedPatient = await loadPatientDetails(p.id);
        updatedPatient.tab = 'profile';

        close();
        detail(updatedPatient);
        toast('Patient details updated successfully');
      } catch (error) {
        console.error('Patient update failed:', error);
        const errorElement = $('#pnme');
        if (errorElement) errorElement.textContent = error.message;
        toast('Unable to update patient details');
        saveButton.disabled = false;
        saveButton.textContent = 'Save changes';
      }
    },

    savenote: async () => {
      if (!p) return;
      const t = $('#nt').value.trim();
      if (!t) {
        $('#nt').focus();
        toast('Please enter a note title');
        return;
      }

      const visitDate = $('#nd').value;
      const doctor = $('#ndr').value.trim();
      const body = $('#nb').value.trim();

      if (!visitDate) {
        $('#nd').focus();
        toast('Please select a visit date');
        return;
      }

      try {
        await apiRequest(`/api/patients/${encodeURIComponent(p.id)}/notes/`, {
          method: 'POST',
          body: JSON.stringify({
            title: t, visit_date: visitDate, doctor: doctor || null,
            body: body || 'No details entered.'
          })
        });
        const updatedPatient = await loadPatientDetails(p.id);
        close();
        detail(updatedPatient);
        toast('Visit note saved successfully');
        console.log('Visit note saved to database');
      } catch (error) {
        console.error('Visit note save failed:', error);
        toast(error.message || 'Failed to save visit note');
      }
    },

    editnote: () => { if (p) editNote(p, b.dataset.id); },

    updatenote: async () => {
      if (!p) return;
      const title = $('#nt').value.trim();
      const visitDate = $('#nd').value;
      const doctor = $('#ndr').value.trim();
      const body = $('#nb').value.trim();

      if (!title) {
        $('#nt').focus();
        toast('Please enter a note title');
        return;
      }
      if (!visitDate) {
        $('#nd').focus();
        toast('Please select a visit date');
        return;
      }
      if (!editingNoteId) {
        toast('No visit note selected');
        return;
      }

      try {
        await apiRequest(`/api/patients/${encodeURIComponent(p.id)}/notes/${encodeURIComponent(editingNoteId)}`, {
          method: 'PATCH',
          body: JSON.stringify({
            title, visit_date: visitDate, doctor: doctor || null,
            body: body || 'No details entered.'
          })
        });
        const updatedPatient = await loadPatientDetails(p.id);
        editingNoteId = null;
        close();
        detail(updatedPatient);
        toast('Visit note updated successfully');
        console.log('Visit note updated in database');
      } catch (error) {
        console.error('Visit note update failed:', error);
        toast(error.message || 'Failed to update visit note');
      }
    },

    deletenote: async () => {
      if (!p) return;
      const noteId = b.dataset.id;
      if (!confirm('Are you sure you want to delete this visit note?')) return;

      try {
        await apiRequest(`/api/patients/${encodeURIComponent(p.id)}/notes/${encodeURIComponent(noteId)}`, { method: 'DELETE' });
        const updatedPatient = await loadPatientDetails(p.id);
        editingNoteId = null;
        detail(updatedPatient);
        toast('Visit note deleted successfully');
        console.log('Visit note deleted from database');
      } catch (error) {
        console.error('Visit note deletion failed:', error);
        toast(error.message || 'Failed to delete visit note');
      }
    },

    savefiles: async () => {
      if (!p) return;
      const fs = [...$('#uf').files];
      if (!fs.length) {
        $('#uf').focus();
        toast('Please select at least one file');
        return;
      }

      const patientId = p.id;
      if (!patientId) {
        toast('Patient ID not found');
        return;
      }

      const uploadedFiles = [];
      const failedFiles = [];
      const documentType = $('#ut').value;

      for (const f of fs) {
        try {
          const formData = new FormData();
          formData.append('file', f);
          const result = await apiRequest(`/api/patients/${encodeURIComponent(patientId)}/documents`, {
            method: 'POST', body: formData
          });
          const doc = result.document;

          uploadedFiles.push({
            id: String(doc.id), name: doc.file_name, type: documentType,
            ext: (f.name.split('.').pop() || 'FILE').toUpperCase().slice(0, 4),
            date: new Date().toISOString().slice(0, 10),
            size: f.size >= 1048576 ? (f.size / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(f.size / 1024)) + ' KB',
            mime_type: doc.mime_type || f.type, file_size: f.size
          });
        } catch (error) {
          console.error(`Upload failed: ${f.name}`, error);
          failedFiles.push(f.name);
        }
      }

      p.files = p.files || [];
      p.files.push(...uploadedFiles);
      if (uploadedFiles.length) p.upd = 'just now';
      close();
      detail(p);

      if (failedFiles.length === 0) {
        toast(uploadedFiles.length + ' file(s) uploaded successfully');
      } else {
        toast(uploadedFiles.length + ' uploaded, ' + failedFiles.length + ' failed. Check Console.');
      }
    }
  }[a] || (() => {}))();
});

/* ---------- Input and keyboard events ---------- */

document.addEventListener('input', e => {
  if (e.target.id === 'q') drawList();
  if (e.target.id === 'ta') {
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px';
  }
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') close();

  if (e.target.id === 'ta' && e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    $('[data-act=send]')?.click();
  }

  const t = e.target.closest?.('.tab');
  if (t && (e.key === 'ArrowRight' || e.key === 'ArrowLeft')) {
    const all = [...document.querySelectorAll('.tab')];
    const i = all.indexOf(t) + (e.key === 'ArrowRight' ? 1 : -1);
    all[(i + all.length) % all.length].click();
  }
});

/* ---------- Start application ---------- */

initializeApp();
