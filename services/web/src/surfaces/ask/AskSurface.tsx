import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send,
  Loader2,
  FileText,
  Clock,
  AlertTriangle,
  ArrowRight,
  Trash2,
  ImagePlus,
  X,
  Paperclip,
  Plus,
  MessageSquare,
  MoreHorizontal,
} from "lucide-react";
import { api, getUserId } from "../../api/client";
import { useNavigate } from "react-router-dom";

interface Citation {
  source: string;
  entity_name: string;
  entity_type: string;
  snippet: string;
}

interface AnswerEnvelope {
  answer: string;
  citations: Citation[];
  freshness: string;
  layer: string;
  conflicts: string[];
  latency_ms: number;
}

interface Attachment {
  id: string;
  file: File;
  preview: string;
  type: "image" | "file";
}

interface QAPair {
  question: string;
  answer: AnswerEnvelope;
  timestamp: number;
  attachments?: { name: string; preview?: string; type: string }[];
}

interface ChatSession {
  id: string;
  title: string;
  messages: QAPair[];
  createdAt: number;
  updatedAt: number;
}

const SESSIONS_KEY = "optimus_chat_sessions";
const ACTIVE_KEY = "optimus_active_chat";

const PROMPTS = [
  { text: "What data sources do I have connected?", sub: "Check integrations" },
  { text: "Who are my top contacts by email volume?", sub: "Analyze contacts" },
  { text: "Show me recent documents from Drive", sub: "Browse files" },
  { text: "What companies have I interacted with?", sub: "Entity analysis" },
];

function generateId(): string {
  return `chat_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function loadSessions(): ChatSession[] {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY);
    if (raw) {
      const sessions = JSON.parse(raw) as ChatSession[];
      return sessions.sort((a, b) => b.updatedAt - a.updatedAt);
    }
  } catch { /* ignore */ }
  return [];
}

async function loadSessionsFromServer(): Promise<ChatSession[]> {
  try {
    const userId = localStorage.getItem("user_id") || "default";
    const resp = await api.get<ChatSession[]>("/api/v1/chats", { params: { user_id: userId } });
    if (resp.data && resp.data.length > 0) {
      return resp.data;
    }
  } catch { /* ignore */ }
  return [];
}

function saveSessions(sessions: ChatSession[]) {
  try {
    const trimmed = sessions.slice(0, 50);
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(trimmed));
    const userId = localStorage.getItem("user_id") || "default";
    api.post("/api/v1/chats", { user_id: userId, sessions: trimmed }).catch(() => {});
  } catch { /* full */ }
}

function generateTitle(question: string): string {
  // Simple title from first question — truncate and clean
  const clean = question
    .replace(/[?!.]+$/, "")
    .replace(/\s+/g, " ")
    .trim();
  return clean.length > 50 ? clean.slice(0, 50) + "..." : clean;
}

export function AskSurface() {
  const [sessions, setSessions] = useState<ChatSession[]>(loadSessions);
  const [activeId, setActiveId] = useState<string | null>(() => {
    const stored = localStorage.getItem(ACTIVE_KEY);
    return stored || null;
  });
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const activeSession = activeId
    ? sessions.find((s) => s.id === activeId) || null
    : null;
  const history = activeSession?.messages || [];

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [history.length, loading]);

  useEffect(() => {
    // On mount, merge server-side chat history with local
    loadSessionsFromServer().then((serverSessions) => {
      if (serverSessions.length > 0) {
        setSessions((local) => {
          const localIds = new Set(local.map((s) => s.id));
          const merged = [...local];
          for (const ss of serverSessions) {
            if (!localIds.has(ss.id)) merged.push(ss);
          }
          return merged.sort((a, b) => b.updatedAt - a.updatedAt);
        });
      }
    });
  }, []);

  useEffect(() => {
    saveSessions(sessions);
  }, [sessions]);

  useEffect(() => {
    if (activeId) {
      localStorage.setItem(ACTIVE_KEY, activeId);
    } else {
      localStorage.removeItem(ACTIVE_KEY);
    }
  }, [activeId]);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height =
        Math.min(inputRef.current.scrollHeight, 150) + "px";
    }
  }, [question]);

  const startNewChat = () => {
    setActiveId(null);
    setQuestion("");
    setAttachments([]);
    setShowHistory(false);
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  const openSession = (id: string) => {
    setActiveId(id);
    setShowHistory(false);
  };

  const deleteSession = (id: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (activeId === id) setActiveId(null);
    setMenuOpenId(null);
  };

  const addFiles = (files: FileList | File[]) => {
    const newAttachments: Attachment[] = [];
    for (const file of Array.from(files)) {
      const isImage = file.type.startsWith("image/");
      const preview = isImage ? URL.createObjectURL(file) : "";
      newAttachments.push({
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        file,
        preview,
        type: isImage ? "image" : "file",
      });
    }
    setAttachments((prev) => [...prev, ...newAttachments]);
  };

  const removeAttachment = (id: string) => {
    setAttachments((prev) => {
      const item = prev.find((a) => a.id === id);
      if (item?.preview) URL.revokeObjectURL(item.preview);
      return prev.filter((a) => a.id !== id);
    });
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files?.length) {
      addFiles(e.dataTransfer.files);
    }
  }, []);

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      const files: File[] = [];
      for (const item of Array.from(items)) {
        if (item.kind === "file") {
          const file = item.getAsFile();
          if (file) files.push(file);
        }
      }
      if (files.length) addFiles(files);
    },
    []
  );

  const handleAsk = useCallback(
    async (q?: string) => {
      const text = q || question;
      if (!text.trim() || loading) return;

      const currentAttachments = attachments.map((a) => ({
        name: a.file.name,
        preview: a.type === "image" ? a.preview : undefined,
        type: a.type,
      }));
      const currentFiles = attachments.map((a) => a.file);

      setLoading(true);
      setQuestion("");
      setAttachments([]);

      // If no active session, create one
      let sessionId = activeId;
      if (!sessionId) {
        sessionId = generateId();
        const newSession: ChatSession = {
          id: sessionId,
          title: generateTitle(text),
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        setSessions((prev) => [newSession, ...prev]);
        setActiveId(sessionId);
      }

      // Build conversation history from current session
      const currentSession = sessions.find((s) => s.id === sessionId);
      const chatHistory = (currentSession?.messages || []).flatMap((qa) => [
        { role: "user", content: qa.question },
        { role: "assistant", content: qa.answer.answer },
      ]);

      // Immediately show the user's message with a loading placeholder
      const placeholderPair: QAPair = {
        question: text,
        answer: {
          answer: "",
          citations: [],
          freshness: "",
          layer: "",
          conflicts: [],
          latency_ms: 0,
        },
        timestamp: Date.now(),
        attachments:
          currentAttachments.length > 0 ? currentAttachments : undefined,
      };

      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? { ...s, messages: [...s.messages, placeholderPair], updatedAt: Date.now() }
            : s
        )
      );

      try {
        let resp;

        if (currentFiles.length > 0) {
          const formData = new FormData();
          formData.append("question", text);
          formData.append("viewer_id", getUserId());
          formData.append("history", JSON.stringify(chatHistory));
          for (const file of currentFiles) {
            formData.append("files", file);
          }
          resp = await api.post<AnswerEnvelope>("/api/v1/ask/upload", formData);
        } else {
          resp = await api.post<AnswerEnvelope>("/api/v1/ask", {
            question: text,
            viewer_id: getUserId(),
            history: chatHistory,
          });
        }

        // Replace the placeholder with the real response
        setSessions((prev) =>
          prev.map((s) => {
            if (s.id !== sessionId) return s;
            const msgs = [...s.messages];
            const lastIdx = msgs.length - 1;
            if (lastIdx >= 0 && msgs[lastIdx].question === text && msgs[lastIdx].answer.answer === "") {
              msgs[lastIdx] = {
                ...msgs[lastIdx],
                answer: resp.data,
              };
            }
            return { ...s, messages: msgs, updatedAt: Date.now() };
          })
        );
      } catch (err: any) {
        const errorPair: QAPair = {
          question: text,
          answer: {
            answer: `Something went wrong: ${err?.message || "Unknown error"}. Please try again.`,
            citations: [],
            freshness: "",
            layer: "error",
            conflicts: [],
            latency_ms: 0,
          },
          timestamp: Date.now(),
          attachments:
            currentAttachments.length > 0 ? currentAttachments : undefined,
        };

        setSessions((prev) =>
          prev.map((s) => {
            if (s.id !== sessionId) return s;
            const msgs = [...s.messages];
            const lastIdx = msgs.length - 1;
            if (lastIdx >= 0 && msgs[lastIdx].question === text && msgs[lastIdx].answer.answer === "") {
              msgs[lastIdx] = { ...msgs[lastIdx], answer: errorPair.answer };
              return { ...s, messages: msgs, updatedAt: Date.now() };
            }
            return { ...s, messages: [...s.messages, errorPair], updatedAt: Date.now() };
          })
        );
      } finally {
        setLoading(false);
        inputRef.current?.focus();
      }
    },
    [question, loading, sessions, activeId, attachments]
  );

  const renderMarkdown = (text: string) => {
    return text
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(
        /`(.*?)`/g,
        '<code class="px-1.5 py-0.5 rounded bg-white/5 text-[#a5b4fc] text-xs font-mono">$1</code>'
      )
      .replace(/^#{4,}\s+(.*$)/gm, '<div class="text-sm font-semibold mt-3 mb-1">$1</div>')
      .replace(/^###\s+(.*$)/gm, '<div class="text-sm font-semibold mt-3 mb-1">$1</div>')
      .replace(/^##\s+(.*$)/gm, '<div class="text-base font-bold mt-4 mb-1.5">$1</div>')
      .replace(/^#\s+(.*$)/gm, '<div class="text-lg font-bold mt-4 mb-2">$1</div>')
      .replace(
        /^[-] (.*)/gm,
        '<div class="flex gap-2 items-start my-0.5"><span class="w-1 h-1 rounded-full bg-current mt-2 shrink-0 opacity-40"></span><span>$1</span></div>'
      )
      .replace(
        /^\d+\.\s+(.*)/gm,
        '<div class="flex gap-2 items-start my-0.5"><span class="opacity-40 font-medium">&#8250;</span><span>$1</span></div>'
      )
      .replace(/\n\n/g, '<div class="h-3"></div>')
      .replace(/\n/g, "<br/>");
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const formatDate = (ts: number) => {
    const d = new Date(ts);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 60000) return "Just now";
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    if (diff < 604800000) return d.toLocaleDateString([], { weekday: "short" });
    return d.toLocaleDateString([], { month: "short", day: "numeric" });
  };

  return (
    <div
      className="flex h-full relative"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Chat history sidebar */}
      <div
        className={`${
          showHistory ? "w-64" : "w-0"
        } shrink-0 border-r border-border bg-card overflow-hidden transition-all duration-200`}
      >
        <div className="w-64 h-full flex flex-col">
          <div className="p-3 border-b border-border flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Chat History
            </span>
            <button
              onClick={startNewChat}
              className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-all"
              title="New chat"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 overflow-auto py-1">
            {sessions.length === 0 ? (
              <div className="p-4 text-center text-xs text-muted-foreground/40">
                No conversations yet
              </div>
            ) : (
              sessions.map((s) => (
                <div key={s.id} className="relative group">
                  <button
                    onClick={() => openSession(s.id)}
                    className={`w-full text-left px-3 py-2.5 text-xs transition-all ${
                      activeId === s.id
                        ? "bg-primary/10 text-primary"
                        : "text-muted-foreground hover:bg-accent hover:text-foreground"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <MessageSquare className="h-3 w-3 shrink-0 opacity-40" />
                      <span className="truncate flex-1 font-medium">
                        {s.title}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5 pl-5">
                      <span className="text-[10px] opacity-40">
                        {s.messages.length} msg{s.messages.length !== 1 ? "s" : ""}
                      </span>
                      <span className="text-[10px] opacity-30">
                        {formatDate(s.updatedAt)}
                      </span>
                    </div>
                  </button>
                  <div className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpenId(menuOpenId === s.id ? null : s.id);
                      }}
                      className="p-1 rounded hover:bg-accent"
                    >
                      <MoreHorizontal className="h-3 w-3" />
                    </button>
                    {menuOpenId === s.id && (
                      <div className="absolute right-0 top-6 z-50 bg-card border border-border rounded-lg shadow-xl py-1 w-28">
                        <button
                          onClick={() => deleteSession(s.id)}
                          className="w-full text-left px-3 py-1.5 text-xs text-destructive hover:bg-destructive/10 flex items-center gap-2"
                        >
                          <Trash2 className="h-3 w-3" />
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Drag overlay */}
        {isDragging && (
          <div className="absolute inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center border-2 border-dashed border-primary/50 rounded-xl m-2">
            <div className="text-center space-y-2">
              <ImagePlus className="h-10 w-10 text-primary mx-auto" />
              <p className="text-sm font-medium text-primary">Drop files here</p>
              <p className="text-xs text-muted-foreground">Images, documents, and more</p>
            </div>
          </div>
        )}

        {/* Top bar */}
        <div className="shrink-0 h-11 border-b border-border/50 flex items-center px-3 gap-2">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground transition-all"
            title={showHistory ? "Hide history" : "Show history"}
          >
            <MessageSquare className="h-4 w-4" />
          </button>
          <div className="h-4 w-px bg-border" />
          <button
            onClick={startNewChat}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg hover:bg-accent text-xs text-muted-foreground hover:text-foreground transition-all"
          >
            <Plus className="h-3.5 w-3.5" />
            New chat
          </button>
          {activeSession && (
            <span className="flex-1 text-xs text-muted-foreground/40 truncate text-right">
              {activeSession.title}
            </span>
          )}
        </div>

        {/* Chat messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          {history.length === 0 && !loading ? (
            <div className="flex flex-col items-center justify-center h-full space-y-8 animate-fade-in px-4">
              <div className="space-y-4 text-center">
                <img src="/logo.svg" alt="Optimus" className="w-14 h-14 mx-auto" />
                <div>
                  <h2 className="text-xl font-semibold tracking-tight">
                    Optimus TrustLayer
                  </h2>
                  <p className="text-sm text-muted-foreground mt-1.5 max-w-md leading-relaxed">
                    Ask questions about your connected data. Get cited, fresh
                    answers with conflict detection.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2.5 max-w-lg w-full">
                {PROMPTS.map((p) => (
                  <button
                    key={p.text}
                    onClick={() => handleAsk(p.text)}
                    className="group text-left p-4 rounded-xl border border-border/60 hover:border-primary/30 hover:bg-white/[0.02] transition-all"
                  >
                    <span className="text-[13px] text-foreground/80 group-hover:text-foreground leading-snug block">
                      {p.text}
                    </span>
                    <span className="text-[11px] text-muted-foreground/50 mt-1.5 flex items-center gap-1">
                      {p.sub}
                      <ArrowRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </span>
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-4">
                {sessions.length > 0 && (
                  <button
                    onClick={() => setShowHistory(true)}
                    className="text-xs text-muted-foreground/40 hover:text-primary flex items-center gap-1 transition-colors"
                  >
                    <Clock className="h-3 w-3" />
                    {sessions.length} previous conversation{sessions.length !== 1 ? "s" : ""}
                  </button>
                )}
                <button
                  onClick={() => navigate("/sources")}
                  className="text-xs text-muted-foreground/40 hover:text-primary flex items-center gap-1 transition-colors"
                >
                  Connect data sources <ArrowRight className="h-3 w-3" />
                </button>
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
              {history.map((qa, i) => (
                <div key={i} className="space-y-4 animate-fade-in">
                  {/* User message */}
                  <div className="flex justify-end">
                    <div className="max-w-[75%] space-y-2">
                      {qa.attachments && qa.attachments.length > 0 && (
                        <div className="flex flex-wrap gap-2 justify-end">
                          {qa.attachments.map((att, j) =>
                            att.type === "image" && att.preview ? (
                              <img
                                key={j}
                                src={att.preview}
                                alt={att.name}
                                className="max-h-48 rounded-xl border border-white/10 object-cover"
                              />
                            ) : (
                              <div
                                key={j}
                                className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-xs"
                              >
                                <Paperclip className="h-3 w-3 text-muted-foreground" />
                                {att.name}
                              </div>
                            )
                          )}
                        </div>
                      )}
                      <div className="px-4 py-3 rounded-2xl rounded-br-sm bg-primary text-primary-foreground text-[13px] leading-relaxed">
                        {qa.question}
                      </div>
                      <div className="text-[10px] text-muted-foreground/30 text-right pr-1">
                        {formatTime(qa.timestamp)}
                      </div>
                    </div>
                  </div>

                  {/* Assistant */}
                  <div className="flex gap-3">
                    <img src="/logo.svg" alt="" className="w-7 h-7 rounded-lg shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0 space-y-2.5">
                      {qa.answer.answer === "" ? (
                        <div className="flex items-center gap-2 py-2">
                          <div className="flex gap-1">
                            <span className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: "0ms" }} />
                            <span className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: "150ms" }} />
                            <span className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: "300ms" }} />
                          </div>
                        </div>
                      ) : (
                      <div
                        className="text-[13px] leading-relaxed text-foreground/90"
                        dangerouslySetInnerHTML={{
                          __html: renderMarkdown(qa.answer.answer),
                        }}
                      />
                      )}

                      {qa.answer.citations.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {qa.answer.citations.map((c, j) => (
                            <span
                              key={j}
                              className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-white/[0.03] border border-white/[0.06] text-[11px] text-muted-foreground"
                            >
                              <FileText className="h-2.5 w-2.5 shrink-0" />
                              <span className="truncate max-w-[120px]">{c.entity_name}</span>
                              <span className="opacity-40">{c.source}</span>
                            </span>
                          ))}
                        </div>
                      )}

                      {qa.answer.conflicts.length > 0 && (
                        <div className="flex items-start gap-2 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/15 text-xs text-amber-400">
                          <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                          <div>
                            <div className="font-medium mb-1">Conflicts detected</div>
                            {qa.answer.conflicts.map((c, j) => (
                              <div key={j}>{c}</div>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="flex items-center gap-3 text-[10px] text-muted-foreground/30">
                        {qa.answer.latency_ms > 0 && <span>{qa.answer.latency_ms}ms</span>}
                        {qa.answer.freshness && qa.answer.freshness !== "N/A" && (
                          <span className="flex items-center gap-0.5">
                            <Clock className="h-2.5 w-2.5" />
                            {qa.answer.freshness.slice(0, 10)}
                          </span>
                        )}
                        {qa.answer.layer && qa.answer.layer !== "error" && (
                          <span className="capitalize">{qa.answer.layer}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}

            </div>
          )}
        </div>

        {/* Input area */}
        <div className="shrink-0 border-t border-white/[0.06] bg-[#0a0f1a]">
          <div className="max-w-3xl mx-auto px-4 py-3">
            {attachments.length > 0 && (
              <div className="flex gap-2 mb-2 flex-wrap">
                {attachments.map((att) => (
                  <div key={att.id} className="relative group">
                    {att.type === "image" ? (
                      <img
                        src={att.preview}
                        alt={att.file.name}
                        className="h-16 w-16 rounded-lg object-cover border border-white/10"
                      />
                    ) : (
                      <div className="h-16 px-3 rounded-lg border border-white/10 bg-white/[0.03] flex items-center gap-2 text-xs text-muted-foreground">
                        <Paperclip className="h-3.5 w-3.5" />
                        <span className="max-w-[100px] truncate">{att.file.name}</span>
                      </div>
                    )}
                    <button
                      onClick={() => removeAttachment(att.id)}
                      className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-destructive text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleAsk();
              }}
              className="relative"
            >
              <textarea
                ref={inputRef}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onPaste={handlePaste}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleAsk();
                  }
                }}
                placeholder="Message Optimus..."
                rows={1}
                className="w-full px-4 py-3.5 pr-24 rounded-xl border border-white/[0.08] bg-white/[0.03] text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-primary/30 resize-none transition-all"
                disabled={loading}
                autoFocus
              />
              <div className="absolute right-2 bottom-2 flex items-center gap-1">
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept="image/*,.pdf,.csv,.xlsx,.doc,.docx,.txt"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files?.length) addFiles(e.target.files);
                    e.target.value = "";
                  }}
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-muted-foreground/40 hover:text-muted-foreground hover:bg-white/[0.05] transition-all"
                  title="Attach file"
                >
                  <Paperclip className="h-4 w-4" />
                </button>
                <button
                  type="submit"
                  disabled={loading || (!question.trim() && attachments.length === 0)}
                  className="w-8 h-8 rounded-lg bg-primary text-primary-foreground flex items-center justify-center disabled:opacity-20 hover:bg-primary/80 transition-all"
                >
                  {loading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Send className="h-3.5 w-3.5" />
                  )}
                </button>
              </div>
            </form>

            <p className="text-[10px] text-muted-foreground/20 text-center mt-2">
              Optimus uses your connected data to provide cited, fresh answers.
              Drag and drop or paste images.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
