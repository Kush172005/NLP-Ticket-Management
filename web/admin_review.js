"use strict";

const $ = (selector, root = document) => root.querySelector(selector);
const state = { queue: [], tickets: [], labels: [], model: null, active: null, departments: [], agents: {}, summary: {} };
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;", "'":"&#39;"}[c]));
const human = value => String(value || "").replace(/_/g, " ").replace(/\s+/g, " ").trim().replace(/\b\w/g, c => c.toUpperCase());
const date = value => { const d = new Date(value); return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString([], {month:"short", day:"numeric", hour:"2-digit", minute:"2-digit"}); };
const api = async (url, options = {}) => {
  const response = await fetch(url, { ...options, headers: { "Content-Type":"application/json", ...(options.headers || {}) } });
  let body = {};
  try { body = await response.json(); } catch (_) {}
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`);
  return body;
};

async function loadData() {
  setError("");
  $("#queueState").hidden = false;
  $("#queueState").textContent = "Loading review queue…";
  $("#queueTableWrap").hidden = true;
  try {
    const [queue, summary, feedback, labels, model, tickets, operations, agents] = await Promise.all([
      api("/tickets/review-queue"), api("/tickets/summary"), api("/tickets/feedback"),
      api("/tickets/labels"), api("/model-info"), api("/tickets"), api("/tickets/operations"), api("/agents")
    ]);
    state.queue = queue.tickets || [];
    state.tickets = tickets.tickets || [];
    state.labels = labels.labels || [];
    state.model = model;
    state.summary = operations.summary || summary;
    state.departments = operations.departments || [];
    state.agents = agents.agents_by_department || {};
    $("#awaitingCount").textContent = summary.awaiting_review ?? "--";
    $("#approvedCount").textContent = summary.approved_today ?? "--";
    $("#correctedCount").textContent = summary.corrected_today ?? "--";
    $("#reviewTime").textContent = summary.average_review_seconds == null ? "--" : formatDuration(summary.average_review_seconds);
    $("#totalTickets").textContent = summary.total_tickets ?? "0";
    $("#humanVerified").textContent = summary.human_verified ?? "0";
    $("#humanCorrected").textContent = summary.human_corrected ?? "0";
    $("#routedCount").textContent = summary.routed ?? "0";
    $("#inProgressCount").textContent = summary.in_progress ?? "0";
    $("#resolvedCount").textContent = summary.resolved ?? "0";
    $("#feedbackTotal").textContent = feedback.reviewed_total ?? "0";
    $("#correctedTotal").textContent = feedback.corrected_total ?? "0";
    $("#agreementRate").textContent = feedback.agreement_rate == null ? "--" : `${(feedback.agreement_rate * 100).toFixed(1)}%`;
    $("#correctionRate").textContent = feedback.correction_rate == null ? "--" : `${(feedback.correction_rate * 100).toFixed(1)}%`;
    const badge = $("#queueBadge");
    badge.textContent = state.queue.length;
    badge.style.display = state.queue.length ? "inline-block" : "none";
    $("#departmentFilter").innerHTML = `<option value="">All departments</option>${state.departments.map(item => `<option value="${esc(item.department)}">${esc(item.department)}</option>`).join("")}`;
    $("#departmentTiles").innerHTML = state.departments.map(item => `<button class="dept-tile" data-department="${esc(item.department)}"><b>${item.count}</b><span>${esc(item.department)}</span></button>`).join("");
    document.querySelectorAll("[data-department]").forEach(button => button.addEventListener("click", () => { $("#statusFilter").value = "all"; $("#departmentFilter").value = button.dataset.department; renderRows(); document.querySelector(".filters").scrollIntoView({behavior:"smooth", block:"center"}); }));
    renderRows();
  } catch (error) {
    $("#queueState").innerHTML = `<div><strong>Unable to load review queue.</strong><br>${esc(error.message === "Failed to fetch" ? "The local API is unavailable. Start the backend and retry." : error.message)}<br><button class="btn" id="retryLoad">Retry</button></div>`;
    $("#retryLoad").addEventListener("click", loadData);
    setError("The queue and summary are loaded from the local ticket database. If the API is offline, start the backend and retry.");
  }
}

function formatDuration(seconds) {
  if (seconds < 60) return `${Math.round(seconds)} sec`;
  const minutes = Math.floor(seconds / 60), remainder = Math.round(seconds % 60);
  return remainder ? `${minutes}m ${remainder}s` : `${minutes} min`;
}
function setError(message) { const node = $("#pageError"); node.textContent = message; node.style.display = message ? "block" : "none"; }
function renderRows() {
  const all = $("#statusFilter").value === "all";
  const items = all ? state.tickets : state.queue;
  const query = $("#queueSearch").value.trim().toLowerCase();
  const department = $("#departmentFilter").value;
  const filtered = items.filter(item => (!query || [item.ticket_id, item.message, item.ai_intent, item.final_intent, item.assigned_department].join(" ").toLowerCase().includes(query)) && (!department || item.assigned_department === department));
  $("#queueMeta").textContent = `${filtered.length} ${all ? "tickets" : "awaiting"}`;
  if (!filtered.length) {
    $("#queueTableWrap").hidden = true;
    $("#queueState").hidden = false;
    $("#queueState").innerHTML = query ? `<div><strong>No matching tickets.</strong><br>Try a different search.</div>` : all ? `<div><strong>No tickets yet.</strong><br>New predictions will appear here after the model classifies a ticket.</div>` : `<div><strong>All caught up.</strong><br>There are no tickets waiting for review.</div>`;
    return;
  }
  $("#queueState").hidden = true;
  $("#queueTableWrap").hidden = false;
  $("#queueRows").innerHTML = filtered.map(item => {
    const pending = item.status === "AWAITING_REVIEW";
    const status = pending ? '<span class="status pending">Awaiting Review</span>' : `<span class="status ${item.status === "RESOLVED" ? "verified" : item.status === "IN_PROGRESS" ? "corrected" : "verified"}">${esc(human(item.status))}</span>`;
    return `<tr><td><span class="ticket-id">${esc(item.ticket_id)}</span></td><td><div class="message" title="${esc(item.message)}">${esc(item.message)}</div></td><td><span class="intent" title="${esc(item.ai_intent)}">${esc(human(item.ai_intent))}</span></td><td>${esc(human(item.final_intent || "—"))}</td><td>${esc(item.assigned_department || "—")}</td><td>${esc(item.assigned_agent || "—")}</td><td><span class="priority">${esc(item.priority || "Not provided")}</span></td><td>${status}</td><td>${esc(date(item.created_at))}</td><td><button class="btn ${pending ? "primary" : ""}" data-open="${esc(item.ticket_id)}">${pending ? "Review" : "View"}</button></td></tr>`;
  }).join("");
  document.querySelectorAll("[data-open]").forEach(button => button.addEventListener("click", () => openTicket(button.dataset.open)));
}

async function openTicket(ticketId) {
  try {
    let ticket = await api(`/tickets/${encodeURIComponent(ticketId)}/start-review`, { method:"POST", body:"{}" });
    state.active = ticket;
    showDrawer();
  } catch (error) { setError(error.message || "Unable to open this ticket."); }
}
function showDrawer() {
  const t = state.active;
  if (!t) return;
  const pending = t.status === "AWAITING_REVIEW";
  const alreadyDecided = !pending;
  const events = (t.audit || []).map(event => auditLine(event)).join("") || '<div class="muted">No audit events recorded.</div>';
  const alternatives = (t.alternatives || []).map(intent => `<span class="chip" title="${esc(intent)}">${esc(human(intent))}</span>`).join("") || '<span class="muted">No alternatives returned.</span>';
  const currentOutcome = t.review_outcome || "AWAITING_REVIEW";
  const isCorrection = currentOutcome === "HUMAN_CORRECTED";
  const lifecycle = ["NEW", "AI_ANALYZED", "AWAITING_REVIEW", currentOutcome, "ROUTED", "IN_PROGRESS", "RESOLVED"];
  const currentStage = t.status === "AWAITING_REVIEW" ? 2 : t.status === "ROUTED" ? 4 : t.status === "IN_PROGRESS" ? 5 : 6;
  const lifecycleHtml = lifecycle.map((stage, index) => `${index ? '<span class="life-arrow">→</span>' : ""}<span class="life-step ${index < currentStage ? "done" : index === currentStage ? "current" : ""}">${esc(stage)}</span>`).join("");
  const finalPanel = alreadyDecided ? `<div class="section"><h3>Final Intent &amp; Department Routing</h3><div class="final-box ${isCorrection ? "corrected" : ""}"><h3>✓ Classification ${isCorrection ? "Corrected" : "Approved"}</h3><div class="detail-grid"><div class="detail-tile"><span>AI Prediction (audit record)</span><b>${esc(human(t.ai_intent))}</b></div><div class="detail-tile"><span>Final Intent</span><b class="final-intent">${esc(human(t.final_intent))}</b></div><div class="detail-tile"><span>Review Decision</span><b>${isCorrection ? "Human Corrected" : "Human Verified"}</b></div><div class="detail-tile"><span>Verified By</span><b>${esc(t.reviewed_by || "Admin (local prototype)")}</b></div><div class="detail-tile"><span>Reviewed At</span><b>${esc(date(t.reviewed_at))}</b></div></div></div><div class="route-box"><span class="muted">✓ Routed to department</span><b>${esc(t.assigned_department || t.assigned_queue)}</b><div class="subnote">Final intent: ${esc(t.final_intent)} · Status: ${esc(t.status)}</div></div></div>` : "";
  const decisionPanel = pending ? `<div class="section"><div class="decision-box"><h3>Admin Decision</h3><p>Does the AI classification correctly represent this ticket?</p><div class="decision-actions"><button class="btn approve" id="approveButton">✓ Approve Classification</button><button class="btn correct" id="correctButton">✎ Correct Classification</button></div></div></div><div id="correctionPanel"></div>` : "";
  const workPanel = t.status === "ROUTED" ? `<div class="section"><h3>Agent Assignment</h3><div class="route-box"><span class="muted">Support Department</span><b>${esc(t.assigned_department || t.assigned_queue)}</b><div class="form-row"><label for="agentSelect">Assign demo support agent</label><select id="agentSelect"><option value="">Select an agent…</option>${(state.agents[t.assigned_department || t.assigned_queue] || []).map(agent => `<option value="${esc(agent)}" ${agent === t.assigned_agent ? "selected" : ""}>${esc(agent)}</option>`).join("")}</select><div class="subnote">Demo agent names only. This project has no employee directory.</div><div id="assignmentError" class="form-error"></div></div>${t.assigned_agent ? `<p>Assigned to <strong>${esc(t.assigned_agent)}</strong></p><button class="btn primary" id="startWorkButton">Start Work · IN_PROGRESS</button>` : `<button class="btn primary" id="assignAgentButton">Assign Agent</button>`}</div></div>` : "";
  const notesHtml = (t.agent_notes || []).map(note => `<div class="drawer-meta" style="margin-bottom:7px"><div style="grid-column:1/-1"><span>${esc(note.author)} · ${esc(date(note.created_at))}</span><b>${esc(note.body)}</b></div></div>`).join("");
  const workInProgress = t.status === "IN_PROGRESS" ? `<div class="section"><h3>Agent Work</h3><div class="detail-grid"><div class="detail-tile"><span>Department</span><b>${esc(t.assigned_department)}</b></div><div class="detail-tile"><span>Assigned Agent</span><b>${esc(t.assigned_agent)}</b></div><div class="detail-tile"><span>Status</span><b>IN_PROGRESS</b></div></div><div class="form-row"><label for="agentNote">Agent Notes · Internal</label><textarea id="agentNote" maxlength="4000" placeholder="Add internal investigation notes…"></textarea><div id="noteError" class="form-error"></div><button class="btn" id="addNoteButton">Add Note</button></div><div style="margin-top:13px">${notesHtml || '<div class="subnote">No agent notes have been entered.</div>'}</div><div class="route-box"><button class="btn approve" id="resolveButton">Resolve Ticket</button></div></div>` : "";
  const resolvedPanel = t.status === "RESOLVED" ? `<div class="section"><h3>Resolution</h3><div class="final-box"><h3>✓ Ticket Resolved</h3><div class="detail-grid"><div class="detail-tile"><span>Final Intent</span><b>${esc(t.final_intent)}</b></div><div class="detail-tile"><span>Department</span><b>${esc(t.assigned_department)}</b></div><div class="detail-tile"><span>Assigned Agent</span><b>${esc(t.assigned_agent)}</b></div><div class="detail-tile"><span>Resolved At</span><b>${esc(date(t.resolved_at))}</b></div></div><div class="route-box"><span class="muted">Resolution Summary</span><p>${esc(t.resolution_summary)}</p></div></div>${notesHtml ? `<h3 style="margin-top:14px">Agent Notes</h3>${notesHtml}` : ""}</div>` : "";
  $("#drawer").innerHTML = `<div class="drawer-head"><div><h2>Ticket ${esc(t.ticket_id)}</h2><span class="status ${pending ? "pending" : isCorrection ? "corrected" : "verified"}">${esc(human(t.status))}</span></div><button class="close" id="closeDrawer" aria-label="Close review panel">×</button></div>
    <div class="detail-grid"><div class="detail-tile"><span>Request ID</span><b>${esc(t.request_id)}</b></div><div class="detail-tile"><span>Created At</span><b>${esc(date(t.created_at))}</b></div><div class="detail-tile"><span>Priority</span><b>${esc(t.priority || "Not provided")}</b></div><div class="detail-tile"><span>Lifecycle Status</span><b>${esc(t.status)}</b></div><div class="detail-tile"><span>Review Decision</span><b>${esc(t.review_outcome ? human(t.review_outcome) : "Awaiting Review")}</b></div><div class="detail-tile"><span>Request Reference</span><b>${esc(t.ticket_id)}</b></div></div>
    <div class="section"><h3>Customer Ticket</h3><div class="message-full">${esc(t.message)}</div></div>
    <div class="section"><h3>AI Suggested Classification</h3><div class="suggestion"><span class="muted">Suggested Intent</span><div class="raw">${esc(human(t.ai_intent))}</div><small>Original model prediction is retained for auditability.</small></div><div style="margin-top:12px"><span class="muted" style="font-size:9px">Alternative Predictions</span><div class="chips">${alternatives}</div></div><div class="model-strip"><span>Classification Model · ${esc(state.model?.display_name || "TF-IDF + LinearSVC")}</span><span>Intent Categories · ${esc(state.model?.intent_categories ?? state.labels.length ?? "--")}</span><span>Confidence · Not provided</span></div></div>
    ${pending ? `<div class="section"><h3>Ticket Lifecycle</h3><div class="lifecycle">${lifecycleHtml}</div></div>` : ""}${decisionPanel}${finalPanel}${workPanel}${workInProgress}${resolvedPanel}${alreadyDecided ? `<div class="section"><h3>Ticket Lifecycle</h3><div class="lifecycle">${lifecycleHtml}</div></div>` : ""}
    <div class="section"><h3>Audit Trail</h3><div class="audit">${events}</div></div>
    <div class="subnote">Local prototype: there is no sign-in or role enforcement. Decisions are stored as “Admin (local prototype)”. Ticket text is retained in a local SQLite database for review.</div>`;
  $("#drawerScrim").classList.add("open"); $("#drawer").classList.add("open");
  $("#closeDrawer").addEventListener("click", closeDrawer);
  $("#approveButton")?.addEventListener("click", confirmApproval);
  $("#correctButton")?.addEventListener("click", showCorrection);
  $("#assignAgentButton")?.addEventListener("click", () => runAction("assign", {agent:$("#agentSelect").value}, "assignmentError", "Choose one of the demo agents for this department."));
  $("#startWorkButton")?.addEventListener("click", () => runAction("start", {}, "assignmentError", "Unable to start work on this ticket."));
  $("#addNoteButton")?.addEventListener("click", () => runAction("notes", {note:$("#agentNote").value}, "noteError", "Unable to save the internal note."));
  $("#resolveButton")?.addEventListener("click", showResolveModal);
}
function auditLine(event) {
  const names = {TICKET_CREATED:"Ticket Created", AI_CLASSIFIED:"AI Classification", ADMIN_REVIEW_STARTED:"Admin Review Started", CLASSIFICATION_APPROVED:"Classification Approved", CLASSIFICATION_CORRECTED:"Admin Correction", TICKET_ROUTED:"Ticket Routed", AGENT_ASSIGNED:"Agent Assigned", WORK_STARTED:"Work Started", AGENT_NOTE_ADDED:"Agent Note Added", TICKET_RESOLVED:"Ticket Resolved"};
  const d = event.details || {};
  const info = d.reason ? `Reason: ${d.reason}` : d.summary || d.note || d.agent || d.intent || d.final_intent || d.assigned_queue || "";
  return `<div class="audit-item"><i class="audit-dot"></i><div><b>${esc(names[event.event_type] || human(event.event_type))}</b><span>${esc(date(event.event_at))} · ${esc(event.actor)}${info ? ` · ${esc(info)}` : ""}</span></div></div>`;
}
function closeDrawer() { $("#drawer").classList.remove("open"); $("#drawerScrim").classList.remove("open"); }
function confirmApproval() {
  const t = state.active;
  $("#modalScrim").innerHTML = `<div class="modal" role="dialog" aria-modal="true" aria-labelledby="confirmTitle"><h2 id="confirmTitle">Approve Classification?</h2><p>AI suggested:</p><div class="intent-preview">${esc(human(t.ai_intent))}</div><p>This will mark the classification as verified and route the ticket to the configured support queue.</p><div id="modalError" class="form-error"></div><div class="modal-actions"><button class="btn" id="cancelApprove">Cancel</button><button class="btn approve" id="confirmApprove">Approve</button></div></div>`;
  $("#modalScrim").classList.add("open");
  $("#cancelApprove").addEventListener("click", closeModal);
  $("#confirmApprove").addEventListener("click", async () => {
    const button = $("#confirmApprove"); button.disabled = true; button.textContent = "Saving…";
    try { state.active = await api(`/tickets/${encodeURIComponent(t.ticket_id)}/approve`, {method:"POST", body:"{}"}); closeModal(); await loadData(); showDrawer(); }
    catch (error) { $("#modalError").textContent = "We couldn't approve this classification. Please try again."; button.disabled = false; button.textContent = "Approve"; }
  });
}
function closeModal() { $("#modalScrim").classList.remove("open"); $("#modalScrim").innerHTML = ""; }
async function runAction(action, body, errorTarget, fallback) {
  const error = $("#" + errorTarget);
  error.textContent = "";
  try {
    state.active = await api(`/tickets/${encodeURIComponent(state.active.ticket_id)}/${action}`, {method:"POST", body:JSON.stringify(body)});
    await loadData();
    showDrawer();
    showToast(action === "assign" ? "Demo agent assigned." : action === "start" ? "Ticket moved to IN_PROGRESS." : "Internal note saved.");
  } catch (_) {
    error.textContent = fallback;
  }
}
function showResolveModal() {
  $("#modalScrim").innerHTML = `<div class="modal" role="dialog" aria-modal="true" aria-labelledby="resolveTitle"><h2 id="resolveTitle">Resolve Ticket</h2><p>Enter a resolution summary. The ticket will not be marked resolved without this note.</p><textarea id="resolutionSummary" maxlength="4000" placeholder="Describe how the issue was resolved…" required></textarea><div id="resolveError" class="form-error"></div><div class="modal-actions"><button class="btn" id="cancelResolve">Cancel</button><button class="btn approve" id="confirmResolve">Mark as Resolved</button></div></div>`;
  $("#modalScrim").classList.add("open");
  $("#cancelResolve").addEventListener("click", closeModal);
  $("#confirmResolve").addEventListener("click", async () => {
    const summary = $("#resolutionSummary").value.trim();
    if (!summary) { $("#resolveError").textContent = "Resolution summary is required."; return; }
    const button = $("#confirmResolve"); button.disabled = true; button.textContent = "Saving…";
    try {
      state.active = await api(`/tickets/${encodeURIComponent(state.active.ticket_id)}/resolve`, {method:"POST", body:JSON.stringify({summary})});
      closeModal(); await loadData(); showDrawer(); showToast("Ticket marked RESOLVED.");
    } catch (_) { $("#resolveError").textContent = "Unable to resolve this ticket. Check its status and try again."; button.disabled = false; button.textContent = "Mark as Resolved"; }
  });
}
function showCorrection() {
  const target = $("#correctionPanel");
  target.innerHTML = `<div class="section"><h3>Correct Classification</h3><div class="form-row"><label for="intentSearch">Search intent labels (${state.labels.length} available)</label><input id="intentSearch" type="search" placeholder="Search intent…" autocomplete="off"><label for="intentSelect">Select correct intent</label><select id="intentSelect" size="7"><option value="" selected disabled>Choose one of the ${state.labels.length} labels…</option>${state.labels.map(label => `<option value="${esc(label)}">${esc(human(label))}</option>`).join("")}</select><label for="correctionReason">Reason for correction · Optional</label><textarea id="correctionReason" maxlength="1000" placeholder="Add a short note for the audit trail…"></textarea><div id="correctionError" class="form-error"></div><div class="decision-actions" style="margin-top:10px"><button id="saveCorrection" class="btn primary">Save Correction</button><button id="cancelCorrection" class="btn">Cancel</button></div></div></div>`;
  const search = $("#intentSearch"), select = $("#intentSelect");
  search.addEventListener("input", () => {
    const query = search.value.trim().toLowerCase();
    const matches = state.labels.filter(label => `${label} ${human(label)}`.toLowerCase().includes(query));
    select.innerHTML = `<option value="" selected disabled>${matches.length ? "Choose a matching intent…" : "No matching intent labels"}</option>${matches.map(label => `<option value="${esc(label)}">${esc(human(label))}</option>`).join("")}`;
  });
  $("#cancelCorrection").addEventListener("click", () => { target.innerHTML = ""; });
  $("#saveCorrection").addEventListener("click", async () => {
    if (!select.value) { $("#correctionError").textContent = "Select an intent from the project labels."; return; }
    if (select.value === state.active.ai_intent) { $("#correctionError").textContent = "This matches the AI suggestion. Use Approve Classification instead."; return; }
    const button = $("#saveCorrection"); button.disabled = true; button.textContent = "Saving…";
    try { state.active = await api(`/tickets/${encodeURIComponent(state.active.ticket_id)}/correct`, {method:"POST", body:JSON.stringify({intent:select.value, reason:$("#correctionReason").value})}); await loadData(); showDrawer(); }
    catch (error) { $("#correctionError").textContent = "Unable to save classification correction. Please try again."; button.disabled = false; button.textContent = "Save Correction"; }
  });
}
function showToast(message) { const node = $("#toast"); node.textContent = message; node.classList.add("show"); setTimeout(() => node.classList.remove("show"), 2600); }

$("#refreshButton").addEventListener("click", loadData);
$("#queueSearch").addEventListener("input", renderRows);
$("#statusFilter").addEventListener("change", renderRows);
$("#departmentFilter").addEventListener("change", renderRows);
$("#drawerScrim").addEventListener("click", closeDrawer);
$("#menuButton").addEventListener("click", () => $("#sidebar").classList.toggle("open"));
$("#modalScrim").addEventListener("click", event => { if (event.target.id === "modalScrim") closeModal(); });
document.addEventListener("keydown", event => { if (event.key === "Escape") { closeModal(); closeDrawer(); } });
loadData().then(() => {
  const ticketId = new URLSearchParams(location.search).get("ticket");
  if (ticketId) openTicket(ticketId);
});
