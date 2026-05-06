import React, { useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble";
import JobResultsMessage from "./JobResultsMessage";
import { Bot, ChevronDown } from "lucide-react";
import type { JobSearchResult } from "../../services/chatService";

// ── Message shape shared across SeekBot ───────────────────────────────────────
export interface Message {
  role: "user" | "assistant";
  content: string;
  /** 'text' | 'jobs' | other AI message types */
  messageType?: string;
  /** Structured job list — populated when messageType === 'jobs' */
  jobs?: JobSearchResult[];
  /** If true, the message will skip any entrance animations (like typewriter) */
  skipAnimation?: boolean;
}

interface ChatWindowProps {
  messages: Message[];
  isLoading: boolean;
}

const SUGGESTIONS = [
  "🔍 Find React developer jobs near me",
  "📄 Review my resume for a backend role",
  "🗺️ Skills needed for data science?",
  "💬 How to ace a behavioral interview?",
];

const ChatWindow: React.FC<ChatWindowProps> = ({ messages, isLoading }) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showScrollArrow, setShowScrollArrow] = useState(false);

  // Auto-scroll to latest message if already at bottom
  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;

    const isAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 100;
    
    if (isAtBottom || isLoading) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading]);

  const handleScroll = () => {
    const container = scrollRef.current;
    if (!container) return;

    const isNearBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 150;
    setShowScrollArrow(!isNearBottom);
  };

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const isEmpty = messages.length === 0 && !isLoading;

  return (
    <div className="relative flex-1 min-h-0 flex flex-col">
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className={`flex-1 min-h-0 overflow-y-auto${isEmpty ? " flex flex-col items-center justify-center" : ""}`}
      >
        {/* ── Empty state ───────────────────────────────────────────────────────── */}
        {isEmpty ? (
          <div className="flex flex-col items-center text-center px-4">
            <div className="w-16 h-16 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center mb-4">
              <Bot size={28} className="text-indigo-400" />
            </div>
            <h2 className="text-xl font-semibold text-zinc-200 mb-2">
              How can I help you today?
            </h2>
            <p className="text-zinc-500 text-sm max-w-xs mb-6">
              Ask me about job searching, resume feedback, career roadmaps, or
              interview prep.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-md">
              {SUGGESTIONS.map((chip) => (
                <div
                  key={chip}
                  className="bg-zinc-900 border border-zinc-800 hover:border-zinc-700 hover:text-zinc-300 rounded-xl px-4 py-3 text-sm text-zinc-500 text-left transition-colors cursor-default select-none"
                >
                  {chip}
                </div>
              ))}
            </div>
          </div>
        ) : (
          /* ── Message list ─────────────────────────────────────────────────────── */
          <div className="px-4 py-6 space-y-2">
            {messages.map((msg, i) => {
              const isLast = i === messages.length - 1 && !isLoading;
              if (msg.role === "assistant" && msg.messageType === "jobs") {
                return (
                  <JobResultsMessage
                    key={i}
                    content={msg.content}
                    jobs={msg.jobs}
                  />
                );
              }
              return (
                <MessageBubble 
                  key={i} 
                  role={msg.role} 
                  content={msg.content} 
                  messageType={msg.messageType}
                  isLast={isLast}
                  skipAnimation={msg.skipAnimation}
                />
              );
            })}

            {isLoading && (
              <MessageBubble role="assistant" content="" isLoading={true} />
            )}

            <div ref={bottomRef} className="h-4" />
          </div>
        )}
      </div>

      {/* Scroll to bottom arrow */}
      {showScrollArrow && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-6 right-8 p-2.5 rounded-full bg-indigo-600 text-white shadow-lg hover:bg-indigo-500 transition-all animate-in fade-in zoom-in duration-200 border border-indigo-400/30"
          aria-label="Scroll to bottom"
        >
          <ChevronDown size={20} />
        </button>
      )}
    </div>
  );
};

export default ChatWindow;
