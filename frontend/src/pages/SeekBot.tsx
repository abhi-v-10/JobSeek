import React, { useState, useCallback } from "react";
import { AlertCircle, X, Menu } from "lucide-react";
import ProtectedRoute from "../components/auth/ProtectedRoute";
import Sidebar from "../components/seekbot/Sidebar";
import ChatWindow from "../components/seekbot/ChatWindow";
import type { Message } from "../components/seekbot/ChatWindow";
import ChatInput from "../components/seekbot/ChatInput";
import { chatService } from "../services/chatService";

const SeekBot: React.FC = () => {
  // ── Core chat state ────────────────────────────────────────────────────────
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // ── UI state ───────────────────────────────────────────────────────────────
  const [error, setError] = useState<string | null>(null);
  const [sidebarRefresh, setSidebarRefresh] = useState(0);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // ── Load an existing session from Django ───────────────────────────────────
  const loadSession = useCallback(async (id: string) => {
    setError(null);
    setSessionId(id);
    setMessages([]);
    setIsLoading(true);

    try {
      const data = await chatService.getMessages(id);
      const mapped: Message[] = data
        .filter((m) => m.role === "user" || m.role === "assistant")
        .map((m) => {
          // Restore structured job cards from Django metadata when loading history
          const metaJobs =
            m.message_type === "jobs" &&
            m.metadata &&
            Array.isArray((m.metadata as Record<string, unknown>).jobs)
              ? ((m.metadata as Record<string, unknown>)
                  .jobs as import("../services/chatService").JobSearchResult[])
              : undefined;
          return {
            role: m.role as "user" | "assistant",
            content: m.content,
            messageType: m.message_type,
            jobs: metaJobs,
            skipAnimation: true,
          };
        });
      setMessages(mapped);
    } catch {
      setError("Failed to load chat history. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ── Start a fresh conversation ─────────────────────────────────────────────
  const handleNewChat = useCallback(() => {
    setSessionId(null);
    setMessages([]);
    setInputValue("");
    setError(null);
  }, []);

  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [isStopping, setIsStopping] = useState(false);

  // ── Stop the ongoing AI request ─────────────────────────────────────────────
  const handleStop = useCallback(() => {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
      setIsStopping(true);
      setIsLoading(false);
      // Give it a moment to reset
      setTimeout(() => setIsStopping(false), 500);
    }
  }, [abortController]);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // ── Send a message ─────────────────────────────────────────────────────────
  const handleSend = useCallback(async () => {
    const text = inputValue.trim();
    if ((!text && !selectedFile) || isLoading || isStopping) return;

    setError(null);
    setInputValue("");
    setIsLoading(true);

    const controller = new AbortController();
    setAbortController(controller);

    // Optimistic: show user message immediately
    setMessages((prev) => [...prev, { role: "user", content: text || "Sent a file" }]);

    try {
      let currentSessionId = sessionId;

      // First message → create a new Django session
      if (!currentSessionId) {
        // Generate AI title from first message
        const title = await chatService.generateTitle(text || "New File Analysis");
        const session = await chatService.createSession(title);
        currentSessionId = session.id;
        setSessionId(currentSessionId);
        setSidebarRefresh((n) => n + 1);
      }

      // Forward message and file to the FastAPI AI engine
      const response = await chatService.sendMessage(currentSessionId, text, controller.signal, selectedFile);

      const assistantMsg: Message = {
        role: "assistant",
        content: response.message.content,
        messageType: response.message.type,
        jobs:
          response.message.type === "jobs" && Array.isArray(response.message.data)
            ? response.message.data
            : undefined,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setSidebarRefresh((n) => n + 1);
      setSelectedFile(null); // Clear file after send
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        console.log("Request aborted by user");
        return;
      }
      const msg = err instanceof Error && err.message ? err.message : "Something went wrong. Please try again.";
      setError(msg);
    } finally {
      setIsLoading(false);
      setAbortController(null);
    }
  }, [inputValue, isLoading, isStopping, sessionId, selectedFile]);

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <ProtectedRoute>
      {/*
        This div must fill the entire height of <main> (which is flex-1 flex-col inside Layout).
        Using flex-1 here makes it take all remaining space below the sticky Navbar.
        overflow-hidden ensures the internal panels scroll, not the page itself.
      */}
      <div
        className="flex overflow-hidden bg-zinc-950"
        style={{ height: "calc(100vh - 4rem)" }}
      >
        {/* ── Left Sidebar ── */}
        <Sidebar
          activeSessionId={sessionId}
          onSelectSession={loadSession}
          onNewChat={handleNewChat}
          refreshTrigger={sidebarRefresh}
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
        />

        {/* ── Right: Chat area ── */}
        <div className="flex flex-col flex-1 overflow-hidden min-w-0">
          {/* Mobile top bar (only visible on small screens) */}
          <div className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-zinc-800 bg-zinc-950 shrink-0">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="p-2 rounded-xl text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
              aria-label="Open chat history"
            >
              <Menu size={20} />
            </button>
            <span className="text-sm font-medium text-zinc-300">SeekBot</span>
          </div>

          {/* Error banner */}
          {error && (
            <div className="flex items-center gap-3 px-4 py-3 bg-red-950/60 border-b border-red-900/50 text-red-300 text-sm shrink-0">
              <AlertCircle size={16} className="shrink-0" />
              <span className="flex-1">{error}</span>
              <button
                onClick={() => setError(null)}
                className="shrink-0 p-0.5 rounded hover:text-red-100 transition-colors"
                aria-label="Dismiss error"
              >
                <X size={16} />
              </button>
            </div>
          )}

          {/* Scrollable message list — fills all remaining height */}
          <ChatWindow messages={messages} isLoading={isLoading} />

          {/* Fixed input bar at bottom */}
          <ChatInput
            value={inputValue}
            onChange={setInputValue}
            onSend={handleSend}
            onStop={handleStop}
            onFileSelect={setSelectedFile}
            selectedFile={selectedFile}
            isLoading={isLoading}
          />
        </div>
      </div>
    </ProtectedRoute>
  );
};

export default SeekBot;
