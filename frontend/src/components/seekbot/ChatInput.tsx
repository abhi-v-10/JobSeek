import React, { useRef, useEffect } from "react";
import { Send, Square, Paperclip } from "lucide-react";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onStop?: () => void;
  onFileSelect?: (file: File | null) => void;
  selectedFile?: File | null;
  isLoading: boolean;
  disabled?: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({
  value,
  onChange,
  onSend,
  onStop,
  onFileSelect,
  selectedFile,
  isLoading,
  disabled = false,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  }, [value]);

  const canSend = !isLoading && !disabled && value.trim().length > 0;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (canSend) {
        onSend();
      }
    }
  };

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onFileSelect?.(files[0]);
    }
  };

  const removeFile = () => {
    onFileSelect?.(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div className="border-t border-zinc-800 bg-zinc-950 px-4 pt-4 pb-3">
      {/* File preview */}
      {selectedFile && (
        <div className="flex items-center gap-2 mb-2 px-3 py-1.5 bg-zinc-900 border border-zinc-800 rounded-lg w-fit animate-in fade-in slide-in-from-bottom-1">
          <Paperclip size={14} className="text-indigo-400" />
          <span className="text-xs text-zinc-300 truncate max-w-[200px]">{selectedFile.name}</span>
          <button 
            onClick={removeFile}
            className="p-1 hover:bg-zinc-800 rounded text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            <Square size={10} fill="currentColor" />
          </button>
        </div>
      )}

      <div className="flex items-end gap-3 bg-zinc-900 border border-zinc-700/60 rounded-2xl px-4 py-3 focus-within:border-zinc-500/80 transition-colors">
        {/* Attachment button */}
        <button
          type="button"
          onClick={handleFileClick}
          disabled={isLoading || disabled}
          className="shrink-0 p-2 text-zinc-500 hover:text-zinc-300 disabled:opacity-30 transition-colors"
          title="Attach image or document"
        >
          <Paperclip size={20} />
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept="image/*,.pdf,.txt,.doc,.docx"
            onChange={handleFileChange}
          />
        </button>

        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isLoading ? "AI is thinking..." : "Ask me anything…"}
          rows={1}
          disabled={disabled || isLoading}
          style={{ minHeight: "24px", maxHeight: "160px" }}
          className="flex-1 bg-transparent text-zinc-100 placeholder-zinc-500 text-sm resize-none outline-none leading-relaxed disabled:opacity-50"
        />

        {/* Send / Stop button */}
        {isLoading ? (
          <button
            type="button"
            onClick={onStop}
            className="shrink-0 p-2 rounded-xl bg-red-600/20 hover:bg-red-600/40 text-red-400 transition-all border border-red-500/30"
            title="Stop generating"
          >
            <Square size={16} fill="currentColor" />
          </button>
        ) : (
          <button
            type="button"
            onClick={canSend ? onSend : undefined}
            disabled={!canSend}
            className={`shrink-0 p-2 rounded-xl transition-all ${
              canSend
                ? "bg-indigo-600 hover:bg-indigo-500 text-white"
                : "bg-zinc-800 text-zinc-600 cursor-not-allowed"
            }`}
          >
            <Send size={16} />
          </button>
        )}
      </div>

      <p className="text-zinc-600 text-xs text-center mt-2">
        {isLoading ? "Wait for the AI to finish or press stop" : "Press Enter to send · Shift+Enter for new line"}
      </p>
    </div>
  );
};

export default ChatInput;
