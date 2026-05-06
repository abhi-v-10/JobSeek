import React, { useState, useEffect, useMemo } from "react";
import { Bot } from "lucide-react";
import ThinkingIndicator from "./ThinkingIndicator";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  isLoading?: boolean;
  messageType?: string;
  isLast?: boolean;
  skipAnimation?: boolean;
}

// ── Typewriter Hook ────────────────────────────────────────────────────────
// Simulates streaming by revealing text character by character
function useTypewriter(text: string, enabled: boolean, speed: number = 5) {
  const [displayedText, setDisplayedText] = useState(enabled ? "" : text);

  useEffect(() => {
    if (!enabled) {
      setDisplayedText(text);
      return;
    }

    setDisplayedText("");
    let i = 0;
    const interval = setInterval(() => {
      setDisplayedText((prev) => text.slice(0, i));
      i++;
      if (i > text.length) {
        clearInterval(interval);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, enabled, speed]);

  return displayedText;
}

// ── Markdown-lite renderer ──────────────────────────────────────────────────
function renderFormattedContent(content: string) {
  if (!content) return null;

  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let key = 0;

  for (const line of lines) {
    // Force remove hashtags as requested
    const trimmed = line.trim().replace(/^#+\s*/, "");
    if (!trimmed && line.trim() === "") {
      elements.push(<div key={key++} className="h-3" />);
      continue;
    }

    // Bullet items: "- item" or "* item"
    const bulletMatch = trimmed.match(/^[-*•]\s+(.+)$/);
    if (bulletMatch) {
      elements.push(
        <div key={key++} className="flex items-start gap-2 mb-2 last:mb-0 ml-1">
          <span className="mt-2 w-1 h-1 rounded-full bg-indigo-500 shrink-0" />
          <p className="text-[14px] text-zinc-300 leading-relaxed">
            {renderInlineFormatting(bulletMatch[1])}
          </p>
        </div>
      );
      continue;
    }

    // Bold section headers
    const sectionMatch = trimmed.match(/^\d+\.\s+\*\*([^*]+)\*\*:?\s*(.*)$/) || trimmed.match(/^\*\*([^*]+)\*\*:?\s*(.*)$/);
    
    if (sectionMatch) {
      const title = sectionMatch[1].trim();
      const rest = sectionMatch[2]?.trim();
      
      elements.push(
        <div key={key++} className="mt-6 mb-3 first:mt-0 last:mb-0">
          <h4 className="text-[13px] font-black text-indigo-400 mb-1.5 uppercase tracking-tighter">
            {title}
          </h4>
          {rest && (
            <p className="text-[14px] text-zinc-300 leading-relaxed">
              {renderInlineFormatting(rest)}
            </p>
          )}
        </div>
      );
      continue;
    }

    // Plain text line
    elements.push(
      <p
        key={key++}
        className="text-[15px] text-zinc-300 leading-relaxed mb-4 last:mb-0"
      >
        {renderInlineFormatting(trimmed)}
      </p>
    );
  }

  return <>{elements}</>;
}

function renderInlineFormatting(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <span key={i} className="font-bold text-zinc-100">
          {part.slice(2, -2)}
        </span>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={i}
          className="px-1.5 py-0.5 bg-indigo-500/10 text-indigo-300 rounded border border-indigo-500/20 text-xs font-mono"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

const MessageBubble: React.FC<MessageBubbleProps> = ({
  role,
  content,
  isLoading = false,
  messageType,
  isLast = false,
  skipAnimation = false,
}) => {
  const isUser = role === "user";
  
  // We only want to animate typing for the very last assistant message if it's currently "active" and not historical
  const shouldAnimate = !isUser && isLast && !skipAnimation && content.length > 0;
  const typedContent = useTypewriter(content, shouldAnimate);

  // ── User message — bubble only ───────────────────────────────────────────
  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[80%] px-5 py-3 text-[15px] leading-relaxed bg-zinc-800 text-zinc-100 rounded-2xl rounded-tr-sm border border-zinc-700/30 shadow-sm">
          <p className="whitespace-pre-wrap break-words">{content}</p>
        </div>
      </div>
    );
  }

  // ── Assistant: Loading state ───────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-start gap-4 mb-6">
        <div className="shrink-0 w-8 h-8 rounded-xl bg-indigo-600/10 border border-indigo-500/20 text-indigo-500 flex items-center justify-center shadow-sm">
          <Bot size={18} />
        </div>
        <ThinkingIndicator />
      </div>
    );
  }

  // ── Assistant: ChatGPT styled (No bubble, rich text) ──────────────────────
  return (
    <div className="flex items-start gap-4 mb-8 group">
      <div className="shrink-0 w-8 h-8 rounded-xl bg-zinc-900 border border-zinc-800 text-zinc-400 flex items-center justify-center group-hover:border-zinc-700 transition-colors shadow-sm mt-1">
        <Bot size={18} />
      </div>
      
      <div className="flex-1 min-w-0 max-w-[85%]">
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
          {renderFormattedContent(typedContent)}
          
          {/* Typing cursor if animating */}
          {shouldAnimate && typedContent.length < content.length && (
            <span className="inline-block w-2 h-4 bg-indigo-500 ml-1 animate-pulse align-middle" />
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
