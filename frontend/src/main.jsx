import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BarChart3,
  CheckCircle2,
  Clock3,
  Download,
  ExternalLink,
  FileSearch,
  FileUp,
  History,
  KeyRound,
  LayoutDashboard,
  MessageSquare,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Signal,
  Trash2,
  TriangleAlert,
  UploadCloud,
  X,
} from "lucide-react";
import "./styles.css";

const LOCAL_HOSTS = ["localhost", "127.0.0.1", ""];
const API = import.meta.env.VITE_API_URL || (LOCAL_HOSTS.includes(window.location.hostname) ? "http://localhost:8000" : "");
const HISTORY_KEY = "evidence-alpha-chat-history";
const MODEL_KEY = "evidence-alpha-selected-model";
const IS_LOCAL_APP = LOCAL_HOSTS.includes(window.location.hostname);
const MODEL_OPTIONS = [
  { id: "openai-gpt-4.1-mini", label: "OpenAI ChatGPT 4.1-mini", provider: "OpenAI", model: "gpt-4.1-mini" },
  { id: "local-qwen3-14b", label: "qwen3:14b local", provider: "Local Ollama", model: "qwen3:14b" },
  { id: "local-llama3.1", label: "llama3.1 local", provider: "Local Ollama", model: "llama3.1" },
];
const LOCAL_MODEL_OPTIONS = [
  { id: "local-qwen3-14b", label: "qwen3:14b local", model: "qwen3:14b" },
  { id: "local-llama3.1", label: "llama3.1 local", model: "llama3.1" },
];

function App() {
  const [page, setPage] = useState("dashboard");
  const [filings, setFilings] = useState([]);
  const [processorJobs, setProcessorJobs] = useState([]);
  const [health, setHealth] = useState(null);
  const [serviceHealth, setServiceHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [localModelStatus, setLocalModelStatus] = useState(null);
  const [localActionMessage, setLocalActionMessage] = useState("");
  const [selectedModel, setSelectedModel] = useState(loadModelChoice);
  const [appError, setAppError] = useState("");
  const [sessions, setSessions] = useState(loadSessions);
  const [activeSessionId, setActiveSessionId] = useState(() => sessions[0]?.id || createSessionId());
  const completedJobCount = useRef(0);

  useEffect(() => {
    fetchHealth();
    fetchServiceHealth(selectedModel);
    fetchLocalModelStatus();
    fetchFilings();
    fetchProcessor();
    const processorTimer = window.setInterval(fetchProcessor, 3000);
    const healthTimer = window.setInterval(() => fetchServiceHealth(selectedModel), 10000);
    const localModelTimer = window.setInterval(fetchLocalModelStatus, 5000);
    return () => {
      window.clearInterval(processorTimer);
      window.clearInterval(healthTimer);
      window.clearInterval(localModelTimer);
    };
  }, [selectedModel]);

  useEffect(() => {
    window.localStorage.setItem(HISTORY_KEY, JSON.stringify(sessions));
  }, [sessions]);

  useEffect(() => {
    window.localStorage.setItem(MODEL_KEY, selectedModel);
  }, [selectedModel]);

  async function fetchHealth() {
    try {
      setHealth(await apiJson("/health"));
      setAppError("");
    } catch (error) {
      setAppError(error.message);
    }
  }

  async function fetchServiceHealth(modelChoice = selectedModel) {
    setHealthLoading(true);
    try {
      setServiceHealth(await apiJson(`/health/services?model_choice=${encodeURIComponent(modelChoice)}`));
      setAppError("");
    } catch (error) {
      setServiceHealth({
        status: "error",
        services: [
          {
            name: "FastAPI backend",
            status: "error",
            message: error.message,
            detail: "Check that the backend is running on port 8000",
          },
        ],
      });
      setAppError(error.message);
    } finally {
      setHealthLoading(false);
    }
  }

  async function fetchLocalModelStatus() {
    try {
      setLocalModelStatus(await apiJson("/local-models/status"));
    } catch {
      setLocalModelStatus(null);
    }
  }

  async function startLocalModels() {
    try {
      const data = await apiJson("/local-models/start", { method: "POST" });
      setLocalActionMessage(data.message);
      window.setTimeout(() => {
        fetchServiceHealth(selectedModel);
        fetchLocalModelStatus();
      }, 1200);
    } catch (error) {
      setLocalActionMessage(error.message);
    }
  }

  async function downloadLocalModel(modelChoice) {
    try {
      const data = await apiJson("/local-models/pull", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_choice: modelChoice }),
      });
      setLocalActionMessage(data.message);
      await fetchLocalModelStatus();
      window.setTimeout(() => {
        fetchServiceHealth(selectedModel);
        fetchLocalModelStatus();
      }, 1500);
    } catch (error) {
      setLocalActionMessage(error.message);
    }
  }

  async function fetchFilings() {
    try {
      setFilings(await apiJson("/filings"));
      setAppError("");
    } catch (error) {
      setAppError(error.message);
    }
  }

  async function fetchProcessor() {
    let jobs = [];
    try {
      jobs = await apiJson("/processor");
    } catch {
      return;
    }
    const completeCount = jobs.filter((job) => job.status === "complete").length;
    if (completeCount > completedJobCount.current) {
      completedJobCount.current = completeCount;
      fetchFilings();
    }
    setProcessorJobs(jobs);
  }

  async function deleteAllDocuments(confirmation) {
    const data = await apiJson("/documents/delete-all", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmation }),
    });
    setFilings([]);
    setProcessorJobs([]);
    setSessions([]);
    window.localStorage.removeItem(HISTORY_KEY);
    await fetchServiceHealth(selectedModel);
    await fetchHealth();
    return data;
  }

  function upsertActiveSession(updater) {
    setSessions((items) => {
      const existing = items.find((session) => session.id === activeSessionId);
      if (!existing) {
        const updated = updater(newSession(activeSessionId));
        return [updated, ...items];
      }
      return items.map((session) => (session.id === activeSessionId ? updater(session) : session));
    });
  }

  function startNewChat() {
    const session = newSession();
    setSessions((items) => [session, ...items]);
    setActiveSessionId(session.id);
    setPage("chat");
  }

  function openSession(sessionId) {
    setActiveSessionId(sessionId);
    setPage("chat");
  }

  async function askQuestion(question) {
    const clean = question.trim();
    if (!clean) return;
    const currentSession = sessions.find((session) => session.id === activeSessionId) || newSession(activeSessionId);
    const chatContext = buildChatContext(currentSession);

    upsertActiveSession((session) => ({
      ...session,
      title: session.title === "New chat" ? clean.slice(0, 70) : session.title,
      docName: "All uploaded filings",
      updatedAt: new Date().toISOString(),
      messages: [...session.messages, { role: "user", text: clean }],
    }));

    let data;
    try {
      data = await apiJson("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: clean,
          doc_name: null,
          model_choice: selectedModel,
          chat_context: chatContext,
        }),
      });
    } catch (error) {
      data = {
        status: "not_found",
        answer: error.message,
        confidence: 0,
        evidence: [],
      };
    }

    upsertActiveSession((session) => ({
      ...session,
      updatedAt: new Date().toISOString(),
      messages: [...session.messages, { role: "assistant", data }],
    }));
  }

  const activeSession = sessions.find((session) => session.id === activeSessionId) || newSession(activeSessionId);
  const activeJobs = processorJobs.filter((job) => job.status === "queued" || job.status === "processing");
  const completedJobs = processorJobs.filter((job) => job.status === "complete");
  const failedJobs = processorJobs.filter((job) => job.status === "failed");

  return (
    <main className="appShell">
      <TopNav page={page} setPage={setPage} startNewChat={startNewChat} />
      {appError && <div className="appError">{appError}</div>}
      <GlobalProcessor jobs={processorJobs} activeJobs={activeJobs} />

      {page === "dashboard" && (
        <Dashboard
          filings={filings}
          serviceHealth={serviceHealth}
          fetchServiceHealth={fetchServiceHealth}
          healthLoading={healthLoading}
          localModelStatus={localModelStatus}
          fetchLocalModelStatus={fetchLocalModelStatus}
          startLocalModels={startLocalModels}
          downloadLocalModel={downloadLocalModel}
          localActionMessage={localActionMessage}
          selectedModel={selectedModel}
          sessions={sessions}
          activeJobs={activeJobs}
          completedJobs={completedJobs}
          failedJobs={failedJobs}
          setPage={setPage}
        />
      )}

      {page === "upload" && (
        <UploadPage
          fetchFilings={fetchFilings}
          fetchProcessor={fetchProcessor}
          processorJobs={processorJobs}
          setProcessorJobs={setProcessorJobs}
          setPage={setPage}
        />
      )}

      {page === "chat" && (
        <ChatPage
          filings={filings}
          selectedModel={selectedModel}
          session={activeSession}
          askQuestion={askQuestion}
          startNewChat={startNewChat}
        />
      )}

      {page === "history" && <HistoryPage sessions={sessions} openSession={openSession} startNewChat={startNewChat} />}
      {page === "health" && (
        <HealthPage
          serviceHealth={serviceHealth}
          fetchServiceHealth={fetchServiceHealth}
          healthLoading={healthLoading}
          localModelStatus={localModelStatus}
          fetchLocalModelStatus={fetchLocalModelStatus}
          startLocalModels={startLocalModels}
          downloadLocalModel={downloadLocalModel}
          localActionMessage={localActionMessage}
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
          deleteAllDocuments={deleteAllDocuments}
        />
      )}
      <HealthBar serviceHealth={serviceHealth} healthLoading={healthLoading} setPage={setPage} />
    </main>
  );
}

function TopNav({ page, setPage, startNewChat }) {
  const items = [
    ["dashboard", LayoutDashboard, "Dashboard"],
    ["upload", UploadCloud, "Upload"],
    ["chat", MessageSquare, "Ask"],
    ["history", History, "History"],
  ];

  return (
    <header className="topNav">
      <div className="brandMark">
        <ShieldCheck size={28} />
        <div>
          <h1>Evidence Alpha</h1>
          <p>SEC filing copilot</p>
        </div>
      </div>
      <nav>
        {items.map(([key, Icon, label]) => (
          <button className={page === key ? "active" : ""} key={key} onClick={() => setPage(key)}>
            <Icon size={18} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      <button className="primaryNav" onClick={startNewChat}>
        <Plus size={18} />
        <span>New Chat</span>
      </button>
    </header>
  );
}

function GlobalProcessor({ jobs, activeJobs }) {
  if (!jobs.length) return null;
  const latest = jobs[0];
  return (
    <section className={`processor ${activeJobs.length ? "busy" : "ready"}`}>
      <div>
        {activeJobs.length ? <Clock3 size={20} /> : <CheckCircle2 size={20} />}
        <strong>{activeJobs.length ? `${activeJobs.length} file(s) processing` : "Processor idle"}</strong>
        <span>{latest.file_name}: {latest.message}</span>
      </div>
      <div className="processorJobs">
        {jobs.slice(0, 4).map((job) => (
          <span key={job.job_id} className={job.status}>{job.doc_name}</span>
        ))}
      </div>
    </section>
  );
}

function Dashboard({
  filings,
  serviceHealth,
  fetchServiceHealth,
  healthLoading,
  selectedModel,
  sessions,
  activeJobs,
  completedJobs,
  failedJobs,
  setPage,
}) {
  const totalChunks = filings.reduce((sum, filing) => sum + filing.chunk_count, 0);
  const selected = MODEL_OPTIONS.find((item) => item.id === selectedModel) || MODEL_OPTIONS[0];
  return (
    <section className="page dashboard">
      <div className="pageIntro">
        <p className="eyebrow">Dashboard</p>
        <h2>Analyst filing workspace</h2>
        <p>Monitor indexed filings, processing status, model configuration, and recent chat activity.</p>
      </div>

      <div className="metricGrid">
        <Metric icon={FileSearch} label="Indexed filings" value={filings.length} />
        <Metric icon={BarChart3} label="Evidence chunks" value={totalChunks.toLocaleString()} />
        <Metric icon={Clock3} label="Processing now" value={activeJobs.length} />
        <Metric icon={MessageSquare} label="Chat sessions" value={sessions.length} />
      </div>

      <div className="dashboardGrid">
        <HealthSummary serviceHealth={serviceHealth} fetchServiceHealth={fetchServiceHealth} healthLoading={healthLoading} setPage={setPage} />
        <section className="workspacePanel">
          <h3>Model Status</h3>
          <dl className="detailList">
            <div><dt>Provider</dt><dd>{selected.provider}</dd></div>
            <div><dt>Model</dt><dd>{selected.model}</dd></div>
            <div><dt>Selected</dt><dd>{selected.label}</dd></div>
            <div><dt>Configured in</dt><dd>Service Health</dd></div>
          </dl>
        </section>
        <section className="workspacePanel">
          <h3>Processor</h3>
          <dl className="detailList">
            <div><dt>Completed</dt><dd>{completedJobs.length}</dd></div>
            <div><dt>Failed</dt><dd>{failedJobs.length}</dd></div>
            <div><dt>Status</dt><dd>{activeJobs.length ? "Working" : "Ready"}</dd></div>
          </dl>
        </section>
        <section className="workspacePanel wide">
          <h3>Quick Actions</h3>
          <div className="quickActions">
            <button onClick={() => setPage("upload")}><FileUp size={18} /> Upload filings</button>
            <button onClick={() => setPage("chat")}><Search size={18} /> Ask a question</button>
            <button onClick={() => setPage("history")}><History size={18} /> View chat history</button>
          </div>
        </section>
      </div>
    </section>
  );
}

function HealthPage({
  serviceHealth,
  fetchServiceHealth,
  healthLoading,
  localModelStatus,
  fetchLocalModelStatus,
  startLocalModels,
  downloadLocalModel,
  localActionMessage,
  selectedModel,
  setSelectedModel,
  deleteAllDocuments,
}) {
  return (
    <section className="page">
      <div className="pageIntro splitIntro">
        <div>
          <p className="eyebrow">Health</p>
          <h2>Service health check</h2>
          <p>Check backend, index, upload processor, OpenAI configuration, and local Ollama availability.</p>
        </div>
        <button className="primaryAction" onClick={fetchServiceHealth} disabled={healthLoading}>
          <RefreshCw size={18} />
          {healthLoading ? "Checking..." : "Refresh"}
        </button>
      </div>
      <HealthSummary
        serviceHealth={serviceHealth}
        fetchServiceHealth={fetchServiceHealth}
        healthLoading={healthLoading}
        localModelStatus={localModelStatus}
        fetchLocalModelStatus={fetchLocalModelStatus}
        startLocalModels={startLocalModels}
        downloadLocalModel={downloadLocalModel}
        localActionMessage={localActionMessage}
        selectedModel={selectedModel}
        setSelectedModel={setSelectedModel}
        deleteAllDocuments={deleteAllDocuments}
        expanded
      />
    </section>
  );
}

function HealthSummary({
  serviceHealth,
  fetchServiceHealth,
  healthLoading,
  setPage,
  localModelStatus,
  fetchLocalModelStatus,
  startLocalModels,
  downloadLocalModel,
  localActionMessage,
  selectedModel,
  setSelectedModel,
  deleteAllDocuments,
  expanded = false,
}) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmation, setConfirmation] = useState("");
  const [deleteMessage, setDeleteMessage] = useState("");
  const [deleting, setDeleting] = useState(false);
  const services = serviceHealth?.services || [];
  const overall = serviceHealth?.status || "checking";
  const selectedModelHealth = services.find((service) => service.name === modelLabel(selectedModel));

  async function submitDelete() {
    setDeleting(true);
    setDeleteMessage("");
    try {
      const data = await deleteAllDocuments(confirmation);
      setDeleteMessage(`${data.deleted_documents} document(s) and ${data.deleted_chunks} evidence chunk(s) deleted.`);
      setConfirmOpen(false);
      setConfirmation("");
    } catch (error) {
      setDeleteMessage(error.message);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <section className={`workspacePanel healthPanel ${expanded ? "wide" : ""}`}>
      <div className="panelTitle">
        <h3>Service Health</h3>
        <span className={`healthPill ${overall}`}>{healthLabel(overall)}</span>
      </div>
      {expanded && setSelectedModel && (
        <ModelSelector selectedModel={selectedModel} setSelectedModel={setSelectedModel} />
      )}
      <div className="serviceList">
        {services.length === 0 && <p className="muted">Checking services...</p>}
        {services.map((service) => (
          <article className="serviceItem" key={service.name}>
            <span className={`serviceDot ${service.status}`} />
            <div>
              <strong>{service.name}</strong>
              <p>{service.message}</p>
              {expanded && service.detail && <small>{service.detail}</small>}
            </div>
          </article>
        ))}
      </div>
      <div className="healthActions">
        <button className="secondaryAction" onClick={fetchServiceHealth} disabled={healthLoading}>
          <RefreshCw size={18} />
          {healthLoading ? "Checking..." : "Refresh"}
        </button>
        {setPage && (
          <button className="secondaryAction" onClick={() => setPage("health")}>
            <Signal size={18} />
            Details
          </button>
        )}
      </div>
      {expanded && selectedModel?.startsWith("local-") && (
        <LocalModelControls
          status={localModelStatus}
          refreshStatus={fetchLocalModelStatus}
          startLocalModels={startLocalModels}
          downloadLocalModel={downloadLocalModel}
          actionMessage={localActionMessage}
          selectedModel={selectedModel}
        />
      )}
      {expanded && selectedModel === "openai-gpt-4.1-mini" && (
        <OpenAISetupControls selectedModelHealth={selectedModelHealth} />
      )}
      {expanded && deleteAllDocuments && (
        <section className="dangerZone">
          <div>
            <h3>Document Reset</h3>
            <p>Delete all indexed documents, uploaded files, processor jobs, and local chat history for this browser.</p>
          </div>
          <button className="dangerAction" onClick={() => setConfirmOpen(true)}>
            <Trash2 size={18} />
            Delete all documents
          </button>
          {deleteMessage && <div className="uploadMessage dangerMessage">{deleteMessage}</div>}
        </section>
      )}
      {confirmOpen && (
        <div className="modalBackdrop" role="presentation">
          <section className="confirmDialog" role="dialog" aria-modal="true" aria-labelledby="delete-documents-title">
            <button className="iconButton closeButton" onClick={() => setConfirmOpen(false)} aria-label="Close dialog">
              <X size={18} />
            </button>
            <TriangleAlert size={34} />
            <h3 id="delete-documents-title">Delete all documents?</h3>
            <p>
              This clears the active app index and uploaded files. Type <strong>DELETE</strong> to confirm.
            </p>
            <input
              autoFocus
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
              placeholder="Type DELETE"
            />
            <div className="dialogActions">
              <button className="secondaryAction" onClick={() => setConfirmOpen(false)} disabled={deleting}>
                Cancel
              </button>
              <button className="dangerAction" onClick={submitDelete} disabled={confirmation !== "DELETE" || deleting}>
                <Trash2 size={18} />
                {deleting ? "Deleting..." : "Delete documents"}
              </button>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}

function OpenAISetupControls({ selectedModelHealth }) {
  const [copied, setCopied] = useState("");
  const ready = selectedModelHealth?.status === "ok";
  const envText = [
    "LLM_PROVIDER=openai",
    "OPENAI_API_KEY=your_openai_api_key_here",
    "OLLAMA_BASE_URL=http://localhost:11434/v1",
    "LLM_MODEL=gpt-4.1-mini",
    "USE_LLM=true",
    "USE_PRACTICE_ANSWER_KEY=false",
  ].join("\n");

  async function copyText(text, label) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(label);
      window.setTimeout(() => setCopied(""), 1600);
    } catch {
      setCopied("");
    }
  }

  return (
    <section className="openAISetupControls">
      <div className="panelTitle">
        <h3>OpenAI Setup</h3>
        <span className={`healthPill ${ready ? "ok" : "warning"}`}>{ready ? "Ready" : "Key needed"}</span>
      </div>
      <p>
        Use this setup when ChatGPT 4.1-mini is selected. The API key must be configured on the backend, then the backend must restart.
      </p>
      <div className="localSetupSteps">
        <article className="setupStep warning">
          <span>{ready ? <CheckCircle2 size={18} /> : "1"}</span>
          <div>
            <strong>Create or use an OpenAI API key</strong>
            <small>Open the API keys page, create a project key, and keep it private.</small>
          </div>
          <a className="secondaryLink" href="https://platform.openai.com/api-keys" target="_blank" rel="noreferrer">
            <KeyRound size={18} />
            API keys
            <ExternalLink size={15} />
          </a>
        </article>

        <article className={`setupStep ${ready ? "complete" : "warning"}`}>
          <span>{ready ? <CheckCircle2 size={18} /> : "2"}</span>
          <div>
            <strong>Set backend/.env locally</strong>
            <small>Paste the key into backend/.env on the machine running FastAPI.</small>
            <pre className="envBlock">{envText}</pre>
          </div>
          <button className="secondaryAction compactAction" onClick={() => copyText(envText, "env")}>
            <KeyRound size={18} />
            {copied === "env" ? "Copied" : "Copy env"}
          </button>
        </article>

        <article className={`setupStep ${ready ? "complete" : "warning"}`}>
          <span>{ready ? <CheckCircle2 size={18} /> : "3"}</span>
          <div>
            <strong>Set Render secret for hosted demo</strong>
            <small>In Render, add OPENAI_API_KEY under Environment for the evidence-alpha service, then redeploy or restart.</small>
          </div>
          <a className="secondaryLink" href="https://dashboard.render.com/web/srv-daam2buk1f9s73as2h5g/env" target="_blank" rel="noreferrer">
            <KeyRound size={18} />
            Render env
            <ExternalLink size={15} />
          </a>
        </article>

        <article className={`setupStep ${ready ? "complete" : "warning"}`}>
          <span>{ready ? <CheckCircle2 size={18} /> : "4"}</span>
          <div>
            <strong>Restart and refresh health</strong>
            <small>After changing the key, restart the backend or Render service, then click Refresh on this page.</small>
          </div>
        </article>
      </div>
      {!ready && (
        <div className="modelNotice warningNotice">
          {selectedModelHealth?.message || "OPENAI_API_KEY is not configured yet."}
        </div>
      )}
    </section>
  );
}

function ModelSelector({ selectedModel, setSelectedModel }) {
  const selected = MODEL_OPTIONS.find((item) => item.id === selectedModel) || MODEL_OPTIONS[0];
  const localSelected = selectedModel.startsWith("local-");

  return (
    <section className="modelSelectorPanel">
      <div>
        <h3>Answer Model</h3>
        <p>Chat will use this selected model for every filing question.</p>
      </div>
      <label>
        <span>Selected service</span>
        <select value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)}>
          {MODEL_OPTIONS.map((option) => (
            <option value={option.id} key={option.id}>{option.label}</option>
          ))}
        </select>
      </label>
      <dl className="modelMeta">
        <div><dt>Provider</dt><dd>{selected.provider}</dd></div>
        <div><dt>Model</dt><dd>{selected.model}</dd></div>
      </dl>
      {localSelected && (
        <div className="modelNotice">
          {IS_LOCAL_APP
            ? "Local Ollama selected. Use the setup controls below if the selected model is not ready."
            : "Local Ollama models work only in the local version. Use OpenAI ChatGPT 4.1-mini on Render."}
        </div>
      )}
    </section>
  );
}

function LocalModelControls({ status, refreshStatus, startLocalModels, downloadLocalModel, actionMessage, selectedModel }) {
  const installedModels = status?.installed_models || [];
  const ollamaInstalled = Boolean(status?.ollama_installed);
  const ollamaRunning = Boolean(status?.ollama_running);
  const selectedLocalModel = LOCAL_MODEL_OPTIONS.find((item) => item.id === selectedModel);
  const selectedJob = status?.jobs?.find((item) => item.model_choice === selectedModel);
  const selectedReady = selectedLocalModel ? isLocalModelInstalled(installedModels, selectedLocalModel.model) : false;
  const selectedDownloading = selectedJob?.status === "working" || selectedJob?.status === "queued";
  const setupState = getLocalSetupState(ollamaInstalled, ollamaRunning, selectedReady, selectedDownloading);

  return (
    <section className="localModelControls">
      <div className="panelTitle">
        <h3>Local Model Setup</h3>
        <span className={`healthPill ${setupState.status}`}>{setupState.label}</span>
      </div>
      <p>
        Use these controls only on a local machine. This page can install Ollama, start the local service, and download the selected model.
      </p>

      {selectedLocalModel && (
        <div className="localSetupSteps">
          <article className={`setupStep ${ollamaInstalled ? "complete" : "warning"}`}>
            <span>{ollamaInstalled ? <CheckCircle2 size={18} /> : "1"}</span>
            <div>
              <strong>Install Ollama</strong>
              <small>{ollamaInstalled ? "Ollama command is available on this machine." : "Download and install Ollama before local models can run."}</small>
            </div>
            {!ollamaInstalled && (
              <a className="secondaryLink" href="https://ollama.com/download" target="_blank" rel="noreferrer">
                <Download size={18} />
                Download
                <ExternalLink size={15} />
              </a>
            )}
          </article>

          <article className={`setupStep ${ollamaRunning ? "complete" : "warning"}`}>
            <span>{ollamaRunning ? <CheckCircle2 size={18} /> : "2"}</span>
            <div>
              <strong>Start Ollama service</strong>
              <small>{ollamaRunning ? "Ollama is reachable at http://localhost:11434." : "Start the local Ollama service before downloading or using a model."}</small>
            </div>
            {ollamaInstalled && !ollamaRunning && (
              <button className="primaryAction compactAction" onClick={startLocalModels}>
                <Signal size={18} />
                Start
              </button>
            )}
          </article>

          <article className={`setupStep ${selectedReady ? "complete" : selectedDownloading ? "working" : "warning"}`}>
            <span>{selectedReady ? <CheckCircle2 size={18} /> : "3"}</span>
            <div>
              <strong>Download {selectedLocalModel.label}</strong>
              <small>{selectedJob?.message || (selectedReady ? "Selected model is downloaded and ready for chat." : `${selectedLocalModel.model} is not downloaded yet.`)}</small>
            </div>
            <button
              className={selectedReady ? "secondaryAction" : "primaryAction compactAction"}
              disabled={!ollamaRunning || selectedReady || selectedDownloading}
              onClick={() => downloadLocalModel(selectedLocalModel.id)}
            >
              <Download size={18} />
              {selectedReady ? "Ready" : selectedDownloading ? "Downloading" : `Download ${selectedLocalModel.model}`}
            </button>
          </article>
        </div>
      )}

      {selectedLocalModel && !selectedReady && ollamaRunning && !selectedDownloading && (
        <div className="modelNotice warningNotice">
          Ollama is running, but {selectedLocalModel.model} is not downloaded. Click Download to set up this selected model.
        </div>
      )}
      {selectedLocalModel && (
        <p className="healthHint">Selected local model: {selectedLocalModel.label}</p>
      )}
      {actionMessage && <div className="uploadMessage">{actionMessage}</div>}
      <button className="secondaryAction compactAction" onClick={refreshStatus}>
        <RefreshCw size={18} />
        Refresh local status
      </button>
    </section>
  );
}

function getLocalSetupState(ollamaInstalled, ollamaRunning, selectedReady, selectedDownloading) {
  if (selectedReady) return { status: "ok", label: "Ready" };
  if (selectedDownloading) return { status: "working", label: "Downloading" };
  if (ollamaRunning) return { status: "warning", label: "Model missing" };
  if (ollamaInstalled) return { status: "warning", label: "Start needed" };
  return { status: "warning", label: "Install needed" };
}

function HealthBar({ serviceHealth, healthLoading, setPage }) {
  const services = serviceHealth?.services || [];
  const overall = serviceHealth?.status || "checking";
  const label = healthLoading ? "Checking services..." : `${healthLabel(overall)} · ${services.length || 0} checks`;
  return (
    <footer className={`healthBar ${overall}`}>
      <button onClick={() => setPage("health")}>
        <Signal size={17} />
        <span>{label}</span>
      </button>
    </footer>
  );
}

function healthLabel(status) {
  if (status === "ok") return "Healthy";
  if (status === "working") return "Working";
  if (status === "warning") return "Needs attention";
  if (status === "error") return "Service issue";
  return "Checking";
}

function Metric({ icon: Icon, label, value }) {
  return (
    <article className="metric">
      <Icon size={22} />
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function UploadPage({ fetchFilings, fetchProcessor, processorJobs, setProcessorJobs, setPage }) {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploadedJobIds, setUploadedJobIds] = useState([]);

  async function submitUpload(event) {
    event.preventDefault();
    if (!files.length) return;
    setUploading(true);
    setUploadMessage(`Uploading ${files.length} file(s) to the processor...`);
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    try {
      const data = await apiJson("/filings/upload-multiple", { method: "POST", body: formData });
      setUploadedJobIds(data.jobs.map((job) => job.job_id));
      setProcessorJobs((jobs) => mergeJobs(data.jobs, jobs));
      setUploadMessage(`${data.jobs.length} file(s) uploaded and queued for processing.`);
      await fetchProcessor();
      await fetchFilings();
      setFiles([]);
    } catch (error) {
      setUploadMessage(error.message || "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  }

  const visibleJobs = processorJobs.filter((job) => uploadedJobIds.includes(job.job_id));

  return (
    <section className="page">
      <div className="pageIntro">
        <p className="eyebrow">Upload</p>
        <h2>Add one or many SEC filings</h2>
        <p>Upload `.htm` or `.html` filings. The global processor will index them and make them available for chat.</p>
      </div>
      <form className="uploadSurface" onSubmit={submitUpload}>
        <label className="dropZone">
          <FileUp size={34} />
          <strong>{files.length ? `${files.length} file(s) selected` : "Choose SEC filing files"}</strong>
          <span>Single or multiple `.htm` / `.html` files are supported.</span>
          <input multiple type="file" accept=".htm,.html" onChange={(event) => setFiles(Array.from(event.target.files || []))} />
        </label>
        {files.length > 0 && (
          <div className="selectedFiles">
            {files.map((file) => <span key={`${file.name}-${file.size}`}>{file.name}</span>)}
          </div>
        )}
        <button className="primaryAction" disabled={!files.length || uploading}>
          <UploadCloud size={18} />
          {uploading ? "Sending to processor..." : "Upload and process"}
        </button>
        {uploadMessage && <div className="uploadMessage">{uploadMessage}</div>}
        {visibleJobs.length > 0 && (
          <div className="uploadJobs">
            {visibleJobs.map((job) => (
              <div className="uploadJob" key={job.job_id}>
                <span className={job.status}>{job.status}</span>
                <strong>{job.file_name}</strong>
                <small>{job.message}{job.chunk_count ? ` · ${job.chunk_count} chunks` : ""}</small>
              </div>
            ))}
          </div>
        )}
        {visibleJobs.some((job) => job.status === "complete") && (
          <button type="button" className="secondaryAction" onClick={() => setPage("chat")}>
            <MessageSquare size={18} />
            Ask questions
          </button>
        )}
      </form>
    </section>
  );
}

function ChatPage({ filings, selectedModel, session, askQuestion, startNewChat }) {
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);

  const samples = [
    {
      question:
        "What is the FY2018 capital expenditure amount (in USD millions) for 3M? Give a response to the question by relying on the details shown in the cash flow statement.",
    },
    {
      question: "Is 3M a capital-intensive business based on FY2022 data?",
    },
    {
      question:
        "What drove operating margin change as of FY2022 for 3M? If operating margin is not a useful metric for a company like this, then please state that and explain why.",
    },
  ];

  async function submit(event) {
    event.preventDefault();
    const clean = question.trim();
    if (!clean) return;
    setQuestion("");
    setAsking(true);
    try {
      await askQuestion(clean);
    } finally {
      setAsking(false);
    }
  }

  return (
    <section className="page chatPage">
      <div className="chatLayout">
        <aside className="chatTools">
          <button className="secondaryAction" onClick={startNewChat}><Plus size={18} /> New chat</button>
          <div className="scopeBox">
            <span>Scope</span>
            <strong>All uploaded filings</strong>
            <small>{filings.length} indexed filing(s) will be searched for every question.</small>
          </div>
          <div className="scopeBox">
            <span>Model</span>
            <strong>{modelLabel(selectedModel)}</strong>
            <small>Change model and setup status from Service Health.</small>
          </div>
          <div className="scopeBox">
            <span>Memory</span>
            <strong>This chat only</strong>
            <small>Follow-up questions can use this chat history. Other chats stay separate.</small>
          </div>
          <div className="sampleList">
            <strong>Sample questions</strong>
            {samples.map((sample) => (
              <button
                key={sample.question}
                onClick={() => {
                  setQuestion(sample.question);
                }}
              >
                {sample.question}
              </button>
            ))}
          </div>
        </aside>

        <div className="chatPanel">
          <header className="chatHeader">
            <div>
              <p className="eyebrow">Ask</p>
              <h2>{session.title}</h2>
            </div>
            <span className="status">Evidence required</span>
          </header>
          <div className="messages">
            {session.messages.length === 0 && (
              <div className="empty">
                <MessageSquare size={38} />
                <h3>Ask a filing question</h3>
                <p>Answers cite document evidence and can use this chat's prior turns for follow-ups.</p>
              </div>
            )}
            {session.messages.map((message, index) =>
              message.role === "user" ? (
                <div className="bubble user" key={index}>{message.text}</div>
              ) : (
                <AnswerCard key={index} data={message.data} />
              )
            )}
            {asking && <div className="bubble assistant">Retrieving evidence and asking the LLM...</div>}
          </div>
          <form className="ask" onSubmit={submit}>
            <Search size={19} />
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about revenue, capex, operating margin, balance sheet items..."
            />
            <button disabled={asking || !filings.length}>Ask</button>
          </form>
        </div>
      </div>
    </section>
  );
}

function HistoryPage({ sessions, openSession, startNewChat }) {
  return (
    <section className="page">
      <div className="pageIntro splitIntro">
        <div>
          <p className="eyebrow">History</p>
          <h2>Previous chats</h2>
          <p>Open earlier analyst conversations and continue asking questions.</p>
        </div>
        <button className="primaryAction" onClick={startNewChat}><Plus size={18} /> New chat</button>
      </div>
      <div className="historyList">
        {sessions.length === 0 && <p className="muted">No chat history yet.</p>}
        {sessions.map((session) => (
          <button className="historyItem" key={session.id} onClick={() => openSession(session.id)}>
            <MessageSquare size={20} />
            <span>
              <strong>{session.title}</strong>
              <small>{session.docName || "All uploaded filings"} · {session.messages.length} message(s)</small>
            </span>
            <time>{new Date(session.updatedAt).toLocaleString()}</time>
          </button>
        ))}
      </div>
    </section>
  );
}

function AnswerCard({ data }) {
  return (
    <article className={`answer ${data.status}`}>
      <div className="answerTop">
        <span>{data.status === "answered" ? "Answered" : "Not found"}</span>
        <strong>{Math.round((data.confidence || 0) * 100)}% confidence</strong>
      </div>
      {data.model_used && <p className="model">Model: {data.model_used}</p>}
      <p className="answerText">{data.answer}</p>
      {data.calculation && <p className="calc">{data.calculation}</p>}
      {data.document && (
        <p className="cite">
          Source: {data.document}{data.page ? `, page ${data.page}` : ""}
        </p>
      )}
      <details>
        <summary>Evidence</summary>
        {(data.evidence || []).map((item, index) => (
          <div className="evidence" key={`${item.doc_name}-${index}`}>
            <div>
              <strong>{item.doc_name}</strong>
              <span>{item.page_num ? `Page ${item.page_num}` : "Page not detected"}</span>
            </div>
            <p>{item.text}</p>
          </div>
        ))}
      </details>
    </article>
  );
}

function createSessionId() {
  return `chat-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function newSession(id = createSessionId()) {
  return {
    id,
    title: "New chat",
    docName: "",
    messages: [],
    updatedAt: new Date().toISOString(),
  };
}

function loadSessions() {
  try {
    const stored = JSON.parse(window.localStorage.getItem(HISTORY_KEY) || "[]");
    return Array.isArray(stored) ? stored : [];
  } catch {
    return [];
  }
}

function loadModelChoice() {
  const stored = window.localStorage.getItem(MODEL_KEY);
  return MODEL_OPTIONS.some((item) => item.id === stored) ? stored : "openai-gpt-4.1-mini";
}

function buildChatContext(session) {
  return session.messages.slice(-8).map((message) => {
    if (message.role === "assistant") {
      return {
        role: "assistant",
        text: [
          message.data?.answer,
          message.data?.document ? `Source: ${message.data.document}${message.data.page ? `, page ${message.data.page}` : ""}` : "",
        ].filter(Boolean).join("\n"),
      };
    }
    return { role: "user", text: message.text || "" };
  }).filter((message) => message.text.trim());
}

function modelLabel(modelId) {
  return MODEL_OPTIONS.find((item) => item.id === modelId)?.label || "OpenAI ChatGPT 4.1-mini";
}

function isLocalModelInstalled(installedModels, model) {
  return installedModels.some((item) => item === model || item.startsWith(`${model}:`));
}

function mergeJobs(incoming, existing) {
  const byId = new Map(existing.map((job) => [job.job_id, job]));
  incoming.forEach((job) => byId.set(job.job_id, job));
  return Array.from(byId.values());
}

async function apiJson(path, options) {
  const response = await fetch(`${API}${path}`, options);
  const text = await response.text();
  let data = null;

  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error(`${path} returned a non-JSON response. Check that the backend is running on port 8000.`);
    }
  }

  if (!response.ok) {
    const detail = data?.detail || data?.message || text || response.statusText;
    throw new Error(`${path} failed: ${detail}`);
  }

  return data;
}

createRoot(document.getElementById("root")).render(<App />);
