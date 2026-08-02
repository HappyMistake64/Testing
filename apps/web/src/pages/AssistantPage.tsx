import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { assistantApi } from "@/api/client";
import type { AssistantTurn } from "@/api/types";

const ACTIVE_STATES = new Set(["queued", "running"]);

declare global {
  interface Window {
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
    SpeechRecognition?: new () => SpeechRecognitionLike;
  }
}

interface SpeechRecognitionLike {
  lang: string;
  interimResults: boolean;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

export function AssistantPage() {
  const queryClient = useQueryClient();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [command, setCommand] = useState("");
  const [mode, setMode] = useState("execute");
  const [speakReplies, setSpeakReplies] = useState(false);
  const [listening, setListening] = useState(false);
  const [memoryDraft, setMemoryDraft] = useState("");
  const [automationDraft, setAutomationDraft] = useState({
    name: "",
    command: "",
    schedule_kind: "once",
    interval_seconds: 3600,
    delay_seconds: 60,
  });
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const spokenTurns = useRef(new Set<string>());
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  const status = useQuery({
    queryKey: ["assistant", "status"],
    queryFn: assistantApi.status,
    refetchInterval: 10_000,
  });

  const sessions = useQuery({
    queryKey: ["assistant", "sessions"],
    queryFn: assistantApi.sessions.list,
  });

  useEffect(() => {
    if (!sessionId && sessions.data && sessions.data.length > 0) {
      setSessionId(sessions.data[0].id);
    }
  }, [sessions.data, sessionId]);

  const turns = useQuery({
    queryKey: ["assistant", "turns", sessionId],
    queryFn: () => assistantApi.turns.list(sessionId!),
    enabled: Boolean(sessionId),
    refetchInterval: (query) => {
      const data = query.state.data as AssistantTurn[] | undefined;
      return data?.some((t) => ACTIVE_STATES.has(t.state)) ? 1500 : 5000;
    },
  });

  const approvals = useQuery({
    queryKey: ["assistant", "approvals"],
    queryFn: assistantApi.approvals.list,
    refetchInterval: 4000,
  });

  const memory = useQuery({
    queryKey: ["assistant", "memory"],
    queryFn: () => assistantApi.memory.list(),
  });

  const automations = useQuery({
    queryKey: ["assistant", "automations"],
    queryFn: assistantApi.automations.list,
    refetchInterval: 10_000,
  });

  const invalidate = (key: string) =>
    queryClient.invalidateQueries({ queryKey: ["assistant", key] });

  const createSession = useMutation({
    mutationFn: () => assistantApi.sessions.create(),
    onSuccess: (session) => {
      setSessionId(session.id);
      void invalidate("sessions");
    },
  });

  const sendCommand = useMutation({
    mutationFn: async () => {
      let sid = sessionId;
      if (!sid) {
        const session = await assistantApi.sessions.create();
        sid = session.id;
        setSessionId(sid);
      }
      const turn = await assistantApi.turns.create(sid, command, mode);
      // Run inline so the assistant works even without a separate worker.
      return assistantApi.turns.execute(turn.id).catch(() => turn);
    },
    onSuccess: () => {
      setCommand("");
      void invalidate("turns");
      void invalidate("approvals");
      void invalidate("memory");
      void invalidate("sessions");
    },
  });

  const decideApproval = useMutation({
    mutationFn: async ({ id, approve }: { id: string; approve: boolean }) => {
      const decision = approve
        ? await assistantApi.approvals.approve(id)
        : await assistantApi.approvals.deny(id);
      if (approve && decision.turn_requeued) {
        await assistantApi.turns.execute(decision.turn_id).catch(() => undefined);
      }
      return decision;
    },
    onSuccess: () => {
      void invalidate("approvals");
      void invalidate("turns");
    },
  });

  const emergencyStop = useMutation({
    mutationFn: (paused: boolean) =>
      assistantApi.emergencyStop(paused, paused ? "Emergency stop from UI" : ""),
    onSuccess: () => {
      void invalidate("status");
      void invalidate("approvals");
    },
  });

  const storeMemory = useMutation({
    mutationFn: () => assistantApi.memory.store(memoryDraft),
    onSuccess: () => {
      setMemoryDraft("");
      void invalidate("memory");
    },
  });

  const deleteMemory = useMutation({
    mutationFn: (id: string) => assistantApi.memory.remove(id),
    onSuccess: () => void invalidate("memory"),
  });

  const createAutomation = useMutation({
    mutationFn: () =>
      assistantApi.automations.create({
        name: automationDraft.name,
        command: automationDraft.command,
        schedule_kind: automationDraft.schedule_kind,
        interval_seconds:
          automationDraft.schedule_kind === "interval"
            ? automationDraft.interval_seconds
            : null,
        delay_seconds:
          automationDraft.schedule_kind === "once" ? automationDraft.delay_seconds : null,
      }),
    onSuccess: () => {
      setAutomationDraft({ ...automationDraft, name: "", command: "" });
      void invalidate("automations");
    },
  });

  const toggleAutomation = useMutation({
    mutationFn: (id: string) => assistantApi.automations.toggle(id),
    onSuccess: () => void invalidate("automations"),
  });

  const deleteAutomation = useMutation({
    mutationFn: (id: string) => assistantApi.automations.remove(id),
    onSuccess: () => void invalidate("automations"),
  });

  // Speak new completed replies when voice output is enabled.
  useEffect(() => {
    if (!speakReplies || !turns.data) return;
    for (const turn of turns.data) {
      if (
        turn.state === "completed" &&
        turn.response &&
        !spokenTurns.current.has(turn.id)
      ) {
        spokenTurns.current.add(turn.id);
        const utterance = new SpeechSynthesisUtterance(turn.response);
        window.speechSynthesis?.speak(utterance);
      }
    }
  }, [turns.data, speakReplies]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [turns.data]);

  const speechSupported = useMemo(
    () =>
      typeof window !== "undefined" &&
      Boolean(window.SpeechRecognition ?? window.webkitSpeechRecognition),
    [],
  );

  const toggleListening = () => {
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }
    const Ctor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!Ctor) return;
    const recognition = new Ctor();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript ?? "";
      setCommand((prev) => (prev ? `${prev} ${transcript}` : transcript));
    };
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  };

  const paused = status.data?.paused ?? false;

  return (
    <div className="assistant-page">
      <header className="page-header">
        <div>
          <h1>Assistant</h1>
          <p className="page-subtitle">
            Command-driven personal agent. Local-first, every side effect audited.
          </p>
        </div>
        <button
          type="button"
          className={paused ? "btn-primary" : "btn-danger"}
          onClick={() => emergencyStop.mutate(!paused)}
        >
          {paused ? "Resume assistant" : "Emergency stop"}
        </button>
      </header>

      {paused ? (
        <div className="banner banner--danger" role="alert">
          Assistant is paused. All tool execution is blocked and pending approvals were
          revoked.
        </div>
      ) : null}

      <div className="assistant-grid">
        <section className="card assistant-chat">
          <div className="assistant-chat__header">
            <h2>Chat</h2>
            <div className="assistant-chat__controls">
              <select
                aria-label="Session"
                value={sessionId ?? ""}
                onChange={(event) => setSessionId(event.target.value || null)}
              >
                {(sessions.data ?? []).map((session) => (
                  <option key={session.id} value={session.id}>
                    {session.title}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => createSession.mutate()}
              >
                New session
              </button>
            </div>
          </div>

          <div className="assistant-chat__messages">
            {(turns.data ?? []).map((turn) => (
              <div key={turn.id} className="assistant-turn">
                <div className="assistant-turn__command">
                  <span className="assistant-turn__role">You</span>
                  {turn.command}
                </div>
                <div
                  className={`assistant-turn__response assistant-turn__response--${turn.state}`}
                >
                  <span className="assistant-turn__role">FADE</span>
                  {turn.response ??
                    (ACTIVE_STATES.has(turn.state) ? "Working…" : `(${turn.state})`)}
                  <span className={`status-badge status-badge--${turn.state}`}>
                    {turn.state}
                  </span>
                </div>
              </div>
            ))}
            {(turns.data ?? []).length === 0 ? (
              <p className="empty-state">
                Try: “remember I prefer tea”, “what do you know about tea”, “turn on
                light.office”, “lights”, “notify me: build finished”, or ask anything.
              </p>
            ) : null}
            <div ref={chatEndRef} />
          </div>

          <form
            className="assistant-chat__composer"
            onSubmit={(event) => {
              event.preventDefault();
              if (command.trim()) sendCommand.mutate();
            }}
          >
            <select
              aria-label="Mode"
              value={mode}
              onChange={(event) => setMode(event.target.value)}
            >
              <option value="execute">Execute</option>
              <option value="draft">Draft</option>
              <option value="answer">Answer</option>
            </select>
            <input
              aria-label="Command"
              value={command}
              placeholder="Tell FADE what to do…"
              onChange={(event) => setCommand(event.target.value)}
            />
            {speechSupported ? (
              <button
                type="button"
                className={listening ? "btn-danger" : "btn-secondary"}
                onClick={toggleListening}
                aria-label="Voice input"
              >
                {listening ? "Stop" : "Mic"}
              </button>
            ) : null}
            <button
              type="submit"
              className="btn-primary"
              disabled={sendCommand.isPending || !command.trim()}
            >
              Send
            </button>
          </form>
          <label className="assistant-voice-toggle">
            <input
              type="checkbox"
              checked={speakReplies}
              onChange={(event) => setSpeakReplies(event.target.checked)}
            />
            Speak replies aloud
          </label>
        </section>

        <div className="assistant-side">
          <section className="card">
            <h2>Approvals</h2>
            {(approvals.data ?? []).length === 0 ? (
              <p className="empty-state">No pending approvals.</p>
            ) : (
              (approvals.data ?? []).map((approval) => (
                <div key={approval.id} className="approval-item">
                  <div>
                    <strong>{approval.tool_name}</strong>
                    <span className="status-badge">{approval.capability}</span>
                  </div>
                  <code className="approval-item__args">{approval.args_preview}</code>
                  <div className="approval-item__actions">
                    <button
                      type="button"
                      className="btn-primary"
                      onClick={() =>
                        decideApproval.mutate({ id: approval.id, approve: true })
                      }
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="btn-danger"
                      onClick={() =>
                        decideApproval.mutate({ id: approval.id, approve: false })
                      }
                    >
                      Deny
                    </button>
                  </div>
                </div>
              ))
            )}
          </section>

          <section className="card">
            <h2>Memory</h2>
            <form
              className="inline-form"
              onSubmit={(event) => {
                event.preventDefault();
                if (memoryDraft.trim()) storeMemory.mutate();
              }}
            >
              <input
                aria-label="New memory"
                value={memoryDraft}
                placeholder="Store a fact…"
                onChange={(event) => setMemoryDraft(event.target.value)}
              />
              <button type="submit" className="btn-secondary" disabled={!memoryDraft.trim()}>
                Store
              </button>
            </form>
            <ul className="memory-list">
              {(memory.data ?? []).map((item) => (
                <li key={item.id}>
                  <span>{item.content}</span>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => deleteMemory.mutate(item.id)}
                  >
                    Forget
                  </button>
                </li>
              ))}
            </ul>
          </section>

          <section className="card">
            <h2>Automations</h2>
            <form
              className="automation-form"
              onSubmit={(event) => {
                event.preventDefault();
                if (automationDraft.name.trim() && automationDraft.command.trim()) {
                  createAutomation.mutate();
                }
              }}
            >
              <input
                aria-label="Automation name"
                value={automationDraft.name}
                placeholder="Name"
                onChange={(event) =>
                  setAutomationDraft({ ...automationDraft, name: event.target.value })
                }
              />
              <input
                aria-label="Automation command"
                value={automationDraft.command}
                placeholder="Command to run"
                onChange={(event) =>
                  setAutomationDraft({ ...automationDraft, command: event.target.value })
                }
              />
              <div className="automation-form__row">
                <select
                  aria-label="Schedule"
                  value={automationDraft.schedule_kind}
                  onChange={(event) =>
                    setAutomationDraft({
                      ...automationDraft,
                      schedule_kind: event.target.value,
                    })
                  }
                >
                  <option value="once">Once (delay)</option>
                  <option value="interval">Interval</option>
                </select>
                <input
                  aria-label="Seconds"
                  type="number"
                  min={30}
                  value={
                    automationDraft.schedule_kind === "interval"
                      ? automationDraft.interval_seconds
                      : automationDraft.delay_seconds
                  }
                  onChange={(event) => {
                    const value = Number(event.target.value);
                    setAutomationDraft(
                      automationDraft.schedule_kind === "interval"
                        ? { ...automationDraft, interval_seconds: value }
                        : { ...automationDraft, delay_seconds: value },
                    );
                  }}
                />
                <button type="submit" className="btn-secondary">
                  Add
                </button>
              </div>
            </form>
            <ul className="automation-list">
              {(automations.data ?? []).map((automation) => (
                <li key={automation.id}>
                  <div>
                    <strong>{automation.name}</strong>
                    <span className="status-badge">
                      {automation.enabled ? "enabled" : "disabled"}
                    </span>
                  </div>
                  <code>{automation.command}</code>
                  <div className="approval-item__actions">
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => toggleAutomation.mutate(automation.id)}
                    >
                      {automation.enabled ? "Disable" : "Enable"}
                    </button>
                    <button
                      type="button"
                      className="btn-danger"
                      onClick={() => deleteAutomation.mutate(automation.id)}
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="card">
            <h2>Capabilities</h2>
            <ul className="tool-list">
              {(status.data?.tools ?? []).map((tool) => (
                <li key={tool.name}>
                  <strong>{tool.name}</strong>
                  <span className="status-badge">{tool.capability}</span>
                  {tool.requires_approval ? (
                    <span className="status-badge status-badge--blocked">approval</span>
                  ) : null}
                </li>
              ))}
            </ul>
            <h3>Connectors</h3>
            <ul className="tool-list">
              {Object.entries(status.data?.connectors ?? {}).map(([name, info]) => (
                <li key={name}>
                  <strong>{name}</strong> {info.provider}
                  <span className="status-badge">{info.local ? "local" : "remote"}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </div>
  );
}
