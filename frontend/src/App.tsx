import { FormEvent, ReactNode, useEffect, useRef, useState } from "react";
import { ChatPanel, ChatMessage } from "./components/ChatPanel";
import { ModelViewer } from "./components/ModelViewer";
import { createEventSource, createJob, getFileUrl, getJob, JobEvent } from "./api";

type MessageTone = "default" | "success" | "error";

function createMessage(
  role: ChatMessage["role"],
  content: string,
  options: { meta?: string; tone?: MessageTone } = {}
): ChatMessage {
  return {
    id: typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
    role,
    content,
    meta: options.meta,
    tone: options.tone
  };
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function cleanText(value: string): string {
  return value.replace(/\r/g, "").replace(/\n{3,}/g, "\n\n").trim();
}

function summarizeToolResult(result: unknown): string {
  const record = asRecord(result);
  if (!record) {
    return typeof result === "string" ? cleanText(result) : "The local tool finished.";
  }

  if (typeof record.model_path === "string") {
    return "Generated a local GLB and prepared it inside Blender.";
  }

  if (Array.isArray(record.operations)) {
    const lines = record.operations
      .map((operation) => {
        const operationRecord = asRecord(operation);
        if (!operationRecord) {
          return "";
        }
        if (typeof operationRecord.result === "string") {
          return cleanText(operationRecord.result);
        }
        const nestedResult = asRecord(operationRecord.result);
        if (nestedResult && typeof nestedResult.result === "string") {
          return cleanText(nestedResult.result);
        }
        return "";
      })
      .filter(Boolean);
    return lines.length > 0 ? lines.join("\n") : "Applied the requested Blender updates.";
  }

  if (typeof record.result === "string") {
    return cleanText(record.result);
  }

  return "The local tool finished.";
}

function summarizeEvent(event: JobEvent): { content: string; meta: string; tone?: MessageTone } | null {
  const payload = asRecord(event.payload) ?? {};
  const tool = typeof payload.tool === "string" ? payload.tool : null;
  const error = typeof payload.error === "string" ? payload.error : null;

  switch (event.type) {
    case "job_started":
      return { content: "Starting the local agent loop.", meta: "Agent" };
    case "agent_thinking":
      return { content: "Reviewing the request and selecting the next local action.", meta: "Thinking" };
    case "tool_selected":
      if (tool === "generate_mesh") {
        return { content: "Using InstantMesh to generate a model from the uploaded image.", meta: "Tool" };
      }
      if (tool === "blender_modify") {
        return { content: "Applying the requested changes in Blender.", meta: "Tool" };
      }
      if (tool === "finish") {
        return { content: "Wrapping up the current job.", meta: "Tool" };
      }
      return { content: "Running a local tool.", meta: "Tool" };
    case "tool_completed":
      return { content: summarizeToolResult(payload.result), meta: "Completed", tone: "success" };
    case "job_completed":
      return { content: "The job completed successfully.", meta: "Ready", tone: "success" };
    case "job_failed":
      return { content: error ? `The job failed: ${error}` : "The job failed.", meta: "Error", tone: "error" };
    default:
      return null;
  }
}

function HeaderIcon({ children }: { children: ReactNode }) {
  return <span className="icon-art">{children}</span>;
}

function PlusIcon() {
  return (
    <HeaderIcon>
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <path d="M8 2.5v11M2.5 8h11" />
      </svg>
    </HeaderIcon>
  );
}

function ChevronDownIcon() {
  return (
    <HeaderIcon>
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <path d="m4.5 6.5 3.5 3.5 3.5-3.5" />
      </svg>
    </HeaderIcon>
  );
}

function GearIcon() {
  return (
    <HeaderIcon>
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <path d="M8 1.75v1.5M8 12.75v1.5M3.25 8H1.75M14.25 8h-1.5M12.62 3.38l-1.06 1.06M4.44 11.56l-1.06 1.06M12.62 12.62l-1.06-1.06M4.44 4.44 3.38 3.38M10.2 8A2.2 2.2 0 1 1 5.8 8a2.2 2.2 0 0 1 4.4 0Z" />
      </svg>
    </HeaderIcon>
  );
}

function MoreIcon() {
  return (
    <HeaderIcon>
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <path d="M3.5 8h0M8 8h0M12.5 8h0" />
      </svg>
    </HeaderIcon>
  );
}

function PanelIcon() {
  return (
    <HeaderIcon>
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <path d="M2.5 3.25h11v9.5h-11zM10 3.25v9.5" />
      </svg>
    </HeaderIcon>
  );
}

function CloseIcon() {
  return (
    <HeaderIcon>
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <path d="m4 4 8 8M12 4 4 12" />
      </svg>
    </HeaderIcon>
  );
}

function AttachIcon() {
  return (
    <span className="inline-icon" aria-hidden="true">
      <svg viewBox="0 0 16 16">
        <path d="M10.75 5.25 6.12 9.88a2.12 2.12 0 1 0 3 3l4.12-4.13a3.63 3.63 0 1 0-5.13-5.13L3.62 8.12" />
      </svg>
    </span>
  );
}

function SendIcon() {
  return (
    <span className="inline-icon" aria-hidden="true">
      <svg viewBox="0 0 16 16">
        <path d="M2 13.25 14 8 2 2.75l1.92 4.18L10 8l-6.08 1.07Z" />
      </svg>
    </span>
  );
}

function AgentGlyph() {
  return (
    <div className="empty-state-icon" aria-hidden="true">
      <span className="bubble-mark" />
      <span className="spark spark-a" />
      <span className="spark spark-b" />
    </div>
  );
}

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState("idle");
  const [backendState, setBackendState] = useState<"checking" | "online" | "offline">("checking");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [modelUrl, setModelUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const conversationEndRef = useRef<HTMLDivElement | null>(null);

  const suggestedActions = ["Build Workspace", "Show Config"];

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  useEffect(() => {
    let active = true;

    async function checkHealth() {
      try {
        const response = await fetch("http://127.0.0.1:8000/health", { cache: "no-store" });
        if (!active) {
          return;
        }
        setBackendState(response.ok ? "online" : "offline");
      } catch {
        if (active) {
          setBackendState("offline");
        }
      }
    }

    checkHealth();
    const interval = window.setInterval(checkHealth, 5000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  useEffect(() => {
    if (modelUrl) {
      setIsPreviewOpen(true);
    }
  }, [modelUrl]);

  function appendMessage(message: ChatMessage) {
    setMessages((current) => [...current, message]);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }
    const submittedPrompt = prompt.trim();
    if (!submittedPrompt) {
      setError("Enter an instruction before sending.");
      return;
    }
    if (backendState === "offline") {
      setError("Backend is offline. Restart the Blender agent launcher.");
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      setStatus("queued");
      setPrompt("");
      appendMessage(createMessage("user", submittedPrompt, { meta: file ? `Image attached: ${file.name}` : "You" }));
      appendMessage(
        createMessage("agent", file ? "Queued the request with your reference image." : "Queued the request for local execution.", {
          meta: "Queued"
        })
      );

      const job = await createJob(submittedPrompt, file);
      setJobId(job.job_id);
      eventSourceRef.current?.close();
      const source = createEventSource(job.job_id);
      eventSourceRef.current = source;

      source.onmessage = async (message) => {
        const parsed = JSON.parse(message.data) as JobEvent;
        const summary = summarizeEvent(parsed);
        if (summary) {
          appendMessage(createMessage("agent", summary.content, { meta: summary.meta, tone: summary.tone }));
        }

        if (parsed.payload.status && typeof parsed.payload.status === "string") {
          setStatus(parsed.payload.status);
        }

        if (parsed.type === "job_completed" || parsed.type === "job_failed") {
          const latest = await getJob(job.job_id);
          setStatus(latest.status);
          setModelUrl(getFileUrl(latest.result_path));
          setError(latest.error ?? null);
          setIsSubmitting(false);
          if (latest.error) {
            appendMessage(createMessage("agent", latest.error, { meta: "Error", tone: "error" }));
          }
          source.close();
        }
      };

      source.onerror = async () => {
        try {
          const latest = await getJob(job.job_id);
          setStatus(latest.status);
          setModelUrl(getFileUrl(latest.result_path));
          setError(latest.error ?? null);
          if (latest.error) {
            appendMessage(createMessage("agent", latest.error, { meta: "Connection", tone: "error" }));
          }
        } catch {
          setStatus("failed");
          setError("Lost connection to the backend.");
          appendMessage(createMessage("agent", "Lost connection to the backend.", { meta: "Connection", tone: "error" }));
        } finally {
          setIsSubmitting(false);
        }
        source.close();
      };

      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : "Failed to submit job";
      setStatus("failed");
      setError(message);
      setIsSubmitting(false);
      appendMessage(createMessage("agent", message, { meta: "Error", tone: "error" }));
    }
  }

  return (
    <main className={`agent-shell ${isPreviewOpen ? "preview-open" : ""}`}>
      <section className="agent-panel">
        <header className="agent-header">
          <div className="agent-header-title">
            <span className="agent-tab">Chat</span>
          </div>
          <div className="agent-toolbar" aria-label="Agent controls">
            <button type="button" className="icon-button" aria-label="New prompt" onClick={() => setPrompt("")}>
              <PlusIcon />
            </button>
            <button type="button" className="icon-button" aria-label="Prompt presets">
              <ChevronDownIcon />
            </button>
            <button type="button" className="icon-button" aria-label="Show config" onClick={() => setPrompt("Show config")}>
              <GearIcon />
            </button>
            <button type="button" className="icon-button" aria-label="More actions">
              <MoreIcon />
            </button>
            <span className="toolbar-divider" />
            <button
              type="button"
              className="icon-button"
              aria-label="Toggle preview drawer"
              onClick={() => setIsPreviewOpen((current) => !current)}
            >
              <PanelIcon />
            </button>
            <button
              type="button"
              className="icon-button"
              aria-label="Clear conversation"
              onClick={() => {
                setMessages([]);
                setError(null);
              }}
            >
              <CloseIcon />
            </button>
          </div>
        </header>

        <section className="agent-scroll">
          <section className="conversation-region">
            {messages.length === 0 ? (
              <section className="empty-state">
                <AgentGlyph />
                <h1>Build with Agent</h1>
                <p className="empty-copy">AI responses may be inaccurate.</p>
                <p className="empty-link">Generate Agent Instructions to onboard AI onto your codebase.</p>
              </section>
            ) : (
              <section className="conversation">
                {jobId ? <p className="meta-line">Job ID {jobId}</p> : null}
                {error ? <p className="error-text">{error}</p> : null}
                <ChatPanel messages={messages} />
                <div ref={conversationEndRef} />
              </section>
            )}
          </section>

          <section className="suggestions">
            <p className="section-label">Suggested Actions</p>
            <div className="suggestion-row">
              {suggestedActions.map((action) => (
                <button key={action} type="button" className="suggestion-chip" disabled={isSubmitting} onClick={() => setPrompt(action)}>
                  {action}
                </button>
              ))}
            </div>
          </section>
        </section>

        <form className="composer" onSubmit={handleSubmit}>
          <input
            ref={fileInputRef}
            className="sr-only"
            type="file"
            accept="image/*"
            disabled={isSubmitting}
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
          <div className="composer-topline">
            <button type="button" className="context-button" disabled={isSubmitting} onClick={() => fileInputRef.current?.click()}>
              <AttachIcon />
              <span>Add Context...</span>
            </button>
            {file ? <span className="file-pill">{file.name}</span> : null}
          </div>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={3}
            disabled={isSubmitting}
            placeholder="Describe what to build next"
          />
          <div className="composer-footer">
            <div className="composer-meta">
              <span>local</span>
              <span>ollama</span>
              <span>auto</span>
              <span className={`backend-pill backend-${backendState}`}>{backendState}</span>
              <span className={`status-chip status-${status}`}>{status}</span>
            </div>
            <button type="submit" className="send-button" aria-label="Send prompt" disabled={isSubmitting || backendState !== "online"}>
              <SendIcon />
            </button>
          </div>
        </form>
      </section>

      <aside className={`preview-drawer ${isPreviewOpen ? "open" : ""}`} aria-label="Preview drawer">
        <div className="preview-drawer-header">
          <div>
            <p className="drawer-kicker">Preview</p>
            <h2>Model Drawer</h2>
          </div>
          <button type="button" className="icon-button drawer-close" aria-label="Close preview" onClick={() => setIsPreviewOpen(false)}>
            <CloseIcon />
          </button>
        </div>
        <div className="preview-drawer-body">
          <ModelViewer modelUrl={modelUrl} />
        </div>
      </aside>
    </main>
  );
}
