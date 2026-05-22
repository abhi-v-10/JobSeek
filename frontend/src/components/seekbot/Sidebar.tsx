import React, { useEffect, useState } from "react";
import {
  Bot,
  Plus,
  MessageSquare,
  Trash2,
  Pencil,
  Check,
  X,
} from "lucide-react";
import { chatService } from "../../services/chatService";
import type { ChatSessionData } from "../../services/chatService";

interface SidebarProps {
  activeSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onNewChat: () => void;
  refreshTrigger: number;
  isOpen: boolean;
  onClose: () => void;
}

function formatDate(iso: string): string {
  const date = new Date(iso);
  const today = new Date();
  const isToday =
    date.getFullYear() === today.getFullYear() &&
    date.getMonth() === today.getMonth() &&
    date.getDate() === today.getDate();

  if (isToday) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

const Sidebar: React.FC<SidebarProps> = ({
  activeSessionId,
  onSelectSession,
  onNewChat,
  refreshTrigger,
  isOpen,
  onClose,
}) => {
  const [sessions, setSessions] = useState<ChatSessionData[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [localRefresh, setLocalRefresh] = useState(0);

  useEffect(() => {
    let isMounted = true;
    setIsLoadingSessions(true);

    chatService
      .getSessions()
      .then((data) => {
        if (isMounted) setSessions(data);
      })
      .catch((err) => {
        console.error(err);
      })
      .finally(() => {
        if (isMounted) setIsLoadingSessions(false);
      });

    return () => {
      isMounted = false;
    };
  }, [refreshTrigger, localRefresh]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm("Are you sure you want to delete this chat?")) {
      try {
        await chatService.deleteSession(id);
        setLocalRefresh((prev) => prev + 1);
        if (id === activeSessionId) onNewChat();
      } catch (err) {
        console.error("Failed to delete session", err);
      }
    }
  };

  const startEditing = (e: React.MouseEvent, session: ChatSessionData) => {
    e.stopPropagation();
    setEditingId(session.id);
    setEditTitle(session.title);
  };

  const handleRename = async (e: React.MouseEvent | React.FormEvent) => {
    e.stopPropagation();
    if (!editingId || !editTitle.trim()) return;
    try {
      await chatService.updateSession(editingId, editTitle);
      setEditingId(null);
      setLocalRefresh((prev) => prev + 1);
    } catch (err) {
      console.error("Failed to rename session", err);
    }
  };

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed md:relative inset-y-0 left-0 z-40 flex flex-col w-72 bg-white dark:bg-zinc-950 border-r border-zinc-200 dark:border-zinc-800 transition-transform duration-300 ease-in-out shrink-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        {/* Header */}
        <div className="px-4 pt-5 pb-4 shrink-0">
          {/* Logo row */}
          <div className="flex items-center gap-2.5 mb-4">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center shrink-0">
              <Bot size={16} className="text-white" />
            </div>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100 text-lg">
              SeekBot
            </span>
          </div>

          {/* New Chat button */}
          <button
            onClick={() => {
              onNewChat();
              onClose();
            }}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl transition-colors"
          >
            <Plus size={16} />
            New Chat
          </button>
        </div>

        {/* Divider */}
        <div className="h-px bg-zinc-200 dark:bg-zinc-800 mx-4" />

        {/* Section label */}
        <div className="px-4 pt-3 pb-1.5">
          <span className="text-xs font-medium text-zinc-400 dark:text-zinc-600 uppercase tracking-wider">
            Recent Chats
          </span>
        </div>

        {/* Session list */}
        <div className="flex-1 min-h-0 overflow-y-auto px-2 pb-3">
          {isLoadingSessions ? (
            <>
              {[0, 1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-14 bg-zinc-100 dark:bg-zinc-900 rounded-xl animate-pulse mb-1"
                />
              ))}
            </>
          ) : sessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-2">
              <MessageSquare
                size={20}
                className="text-zinc-300 dark:text-zinc-700"
              />
              <span className="text-zinc-400 dark:text-zinc-600 text-xs">
                No conversations yet
              </span>
            </div>
          ) : (
            <div className="flex flex-col gap-0.5">
              {sessions.map((session) => {
                const isActive = session.id === activeSessionId;
                const isEditing = editingId === session.id;

                return (
                  <div
                    key={session.id}
                    onClick={() => {
                      if (!isEditing) {
                        onSelectSession(session.id);
                        onClose();
                      }
                    }}
                    className={`group relative w-full text-left flex items-start gap-3 px-3 py-3 rounded-xl transition-all cursor-pointer ${
                      isActive
                        ? "bg-zinc-200/80 dark:bg-zinc-800/80 text-zinc-900 dark:text-zinc-100"
                        : "text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-900 hover:text-zinc-800 dark:hover:text-zinc-200"
                    }`}
                  >
                    <MessageSquare
                      size={15}
                      className={`mt-0.5 shrink-0 ${
                        isActive
                          ? "text-indigo-400"
                          : "text-zinc-400 dark:text-zinc-600 group-hover:text-zinc-600 dark:group-hover:text-zinc-400"
                      }`}
                    />
                    <div className="flex-1 min-w-0 pr-12">
                      {isEditing ? (
                        <input
                          autoFocus
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleRename(e);
                            if (e.key === "Escape") setEditingId(null);
                          }}
                          className="w-full bg-white dark:bg-zinc-950 border border-indigo-500 rounded px-1 text-sm outline-none"
                        />
                      ) : (
                        <>
                          <p className="text-sm font-medium truncate">
                            {session.title}
                          </p>
                          <p className="text-xs text-zinc-400 dark:text-zinc-600 mt-0.5">
                            {formatDate(session.updated_at)}
                          </p>
                        </>
                      )}
                    </div>

                    {/* Actions - visible on hover or if active */}
                    <div
                      className={`absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1 transition-opacity ${isEditing ? "opacity-100" : "opacity-0 group-hover:opacity-100"}`}
                    >
                      {isEditing ? (
                        <>
                          <button
                            onClick={handleRename}
                            className="p-1 hover:text-green-400 text-zinc-400 dark:text-zinc-500"
                          >
                            <Check size={14} />
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="p-1 hover:text-red-400 text-zinc-400 dark:text-zinc-500"
                          >
                            <X size={14} />
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={(e) => startEditing(e, session)}
                            className="p-1.5 hover:bg-zinc-200 dark:hover:bg-zinc-700/50 rounded-lg text-zinc-400 dark:text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors"
                          >
                            <Pencil size={12} />
                          </button>
                          <button
                            onClick={(e) => handleDelete(e, session.id)}
                            className="p-1.5 hover:bg-zinc-200 dark:hover:bg-zinc-700/50 rounded-lg text-zinc-400 dark:text-zinc-500 hover:text-red-400 transition-colors"
                          >
                            <Trash2 size={12} />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-zinc-200 dark:border-zinc-800 shrink-0">
          <p className="text-zinc-400 dark:text-zinc-600 text-xs text-center">
            Powered by SeekBot AI
          </p>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
