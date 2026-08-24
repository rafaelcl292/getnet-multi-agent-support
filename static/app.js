const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const state = { busy: false };

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) throw new Error((await response.json()).detail || `HTTP ${response.status}`);
  return response.json();
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

function addMessage(role, text, citations = []) {
  const node = document.createElement("div");
  node.className = `message ${role}`;
  const label = role === "user" ? "YOU" : "AGENT RESPONSE";
  const avatar = role === "user" ? "MC" : "AI";
  node.innerHTML = `<div class="avatar">${avatar}</div><div class="bubble"><span class="agent-label">${label}</span><p>${escapeHtml(text)}</p>${citations.length ? `<div class="citations">${citations.map((c, i) => `<a href="${c.url}" target="_blank" rel="noreferrer">SOURCE ${i + 1} ↗</a>`).join("")}</div>` : ""}</div>`;
  $("#messages").append(node);
  $("#messages").scrollTop = $("#messages").scrollHeight;
  return node;
}

function addLoader() {
  const node = document.createElement("div");
  node.className = "message assistant loading";
  node.innerHTML = '<div class="avatar">AI</div><div class="bubble"><span class="agent-label">ORCHESTRATING</span><p><b></b><b></b><b></b></p></div>';
  $("#messages").append(node);
  $("#messages").scrollTop = $("#messages").scrollHeight;
  return node;
}

function renderTrace(data) {
  $("#traceEmpty").style.display = "none";
  $("#traceId").textContent = `TRACE ${data.trace_id}`;
  $$(".node").forEach(n => n.classList.remove("active"));
  $(".node.router").classList.add("active");
  const routeNode = $(`.node.${data.route}`);
  if (routeNode) routeNode.classList.add("active");
  $("#traceList").innerHTML = data.trace.map((step, index) => `<li class="${step.status}" style="animation-delay:${index * 80}ms"><strong>${escapeHtml(step.agent)}</strong><span>${step.duration_ms}ms</span><p>${escapeHtml(step.action)}</p><code>${escapeHtml(JSON.stringify(step.details))}</code></li>`).join("");
}

async function refreshMetrics() {
  try {
    const data = await api("/api/metrics");
    $("#metricRequests").textContent = data.requests;
    $("#metricLatency").textContent = data.avg_latency_ms ? `${data.avg_latency_ms}ms` : "—";
    $("#metricHandoff").textContent = `${Math.round(data.handoff_rate * 100)}%`;
  } catch (_) {}
}

async function sendMessage(message) {
  if (state.busy || !message.trim()) return;
  state.busy = true;
  addMessage("user", message.trim());
  $("#messageInput").value = "";
  const loader = addLoader();
  try {
    const data = await api("/api/chat", { method: "POST", body: JSON.stringify({ message: message.trim(), user_id: $("#userId").value.trim() || "cliente1988" }) });
    loader.remove();
    addMessage("assistant", data.answer, data.citations);
    renderTrace(data);
    refreshMetrics();
  } catch (error) {
    loader.remove();
    addMessage("assistant", `Não foi possível concluir: ${error.message}`);
  } finally { state.busy = false; }
}

function renderEvaluation(data) {
  const pct = Math.round(data.score * 100);
  $("#scoreValue").textContent = `${pct}`;
  $("#scoreRing").style.strokeDashoffset = 327 - (327 * data.score);
  $("#verdict").textContent = data.passed ? "PASS" : "FAIL";
  $("#verdict").className = `verdict ${data.passed ? "pass" : "fail"}`;
  $("#judgeReason").textContent = data.reason;
  Object.entries(data.criteria).forEach(([key, score]) => {
    const row = $(`#criteria [data-key="${key}"]`);
    if (row) { row.style.setProperty("--score", `${score * 100}%`); row.querySelector("b").textContent = score.toFixed(2); }
  });
  $("#actualOutput p").textContent = data.actual_answer;
}

$("#chatForm").addEventListener("submit", e => { e.preventDefault(); sendMessage($("#messageInput").value); });
$("#messageInput").addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#chatForm").requestSubmit(); } });
$("#evalForm").addEventListener("submit", async e => {
  e.preventDefault();
  const button = e.currentTarget.querySelector("button");
  button.disabled = true; button.querySelector("span").textContent = "JUDGE ANALISANDO…";
  try {
    const body = { question: $("#evalQuestion").value, expected_answer: $("#expectedAnswer").value, user_id: $("#userId").value || "cliente1988" };
    if ($("#actualAnswer").value.trim()) body.actual_answer = $("#actualAnswer").value.trim();
    renderEvaluation(await api("/api/evaluations", { method: "POST", body: JSON.stringify(body) }));
    refreshMetrics();
  } catch (error) { $("#judgeReason").textContent = error.message; }
  finally { button.disabled = false; button.querySelector("span").textContent = "EXECUTAR AVALIAÇÃO"; }
});

$$('[data-view]').forEach(tab => tab.addEventListener("click", () => {
  $$('[data-view]').forEach(t => t.classList.remove("active")); tab.classList.add("active");
  $$(".view").forEach(v => v.classList.remove("active")); $(`#${tab.dataset.view}View`).classList.add("active");
}));

async function boot() {
  try {
    const [health, cases] = await Promise.all([api("/health"), api("/api/demo-cases")]);
    $("#systemStatus").textContent = `${health.llm} · ${health.agents} agents`;
    $("#suggestions").innerHTML = cases.map(c => `<button data-message="${escapeHtml(c.message)}" data-user="${c.user_id}">${escapeHtml(c.label)}</button>`).join("");
    $$("#suggestions button").forEach(button => button.addEventListener("click", () => { $("#userId").value = button.dataset.user; sendMessage(button.dataset.message); }));
    refreshMetrics();
  } catch (_) { $(".system-state").classList.add("error"); $("#systemStatus").textContent = "api offline"; }
}
boot();

