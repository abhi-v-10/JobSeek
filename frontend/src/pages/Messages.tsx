import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import ProtectedRoute from '../components/auth/ProtectedRoute';
import { messagesService } from '../services/messages';
import type { Conversation, Message } from '../services/messages';
import { Send, User, Briefcase, Search, MessageSquare, ArrowLeft } from 'lucide-react';
import api from '../lib/axios';

const Messages = () => {
  const [searchParams] = useSearchParams();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConv, setSelectedConv] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isLoadingConv, setIsLoadingConv] = useState(true);
  const [isLoadingMsgs, setIsLoadingMsgs] = useState(false);
  const [currentUserId, setCurrentUserId] = useState<number | null>(null);
  const [isOtherTyping, setIsOtherTyping] = useState(false);
  
  const socketRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [showMobileList, setShowMobileList] = useState(true);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isOtherTyping]);

  // Load current user profile
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await api.get('/users/profile/');
        setCurrentUserId(response.data.user);
      } catch (err) {
        console.error("Failed to load user profile", err);
      }
    };
    fetchUser();
  }, []);

  // Load conversations
  useEffect(() => {
    const fetchConvs = async () => {
      try {
        const data = await messagesService.getConversations();
        setConversations(data);
        
        const convIdStr = searchParams.get('conversation');
        if (convIdStr) {
          const convId = parseInt(convIdStr);
          const found = data.find(c => c.id === convId);
          if (found) {
            setSelectedConv(found);
            setShowMobileList(false);
          }
        }
      } catch (err) {
        console.error("Failed to load conversations", err);
      } finally {
        setIsLoadingConv(false);
      }
    };
    fetchConvs();
  }, [searchParams]);

  // WebSocket Connection Management
  useEffect(() => {
    if (!selectedConv || !currentUserId) return;

    // Load initial messages
    const fetchMsgs = async () => {
      setIsLoadingMsgs(true);
      try {
        const data = await messagesService.getMessages(selectedConv.id);
        setMessages(data);
        setConversations(prev => prev.map(c => c.id === selectedConv.id ? { ...c, unread_count: 0 } : c));
      } catch (err) {
        console.error("Failed to load messages", err);
      } finally {
        setIsLoadingMsgs(false);
      }
    };
    fetchMsgs();

    // Establish WebSocket connection with Token
    const token = localStorage.getItem('access_token');
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://127.0.0.1:8000/ws/chat/${selectedConv.id}/?token=${token}`;
    
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log("WebSocket Connected");
    };

    socket.onmessage = (event) => {
      const data = json_parse_safe(event.data);
      if (!data) return;

      if (data.type === 'chat_message') {
        const msg = data.message;
        setMessages(prev => {
          if (prev.some(m => m.id === msg.id)) return prev;
          return [...prev, msg];
        });
        setIsOtherTyping(false);
      } else if (data.type === 'typing') {
        // ONLY show typing if the sender is NOT the current user
        if (Number(data.sender_id) !== Number(currentUserId)) {
          setIsOtherTyping(data.is_typing);
        }
      }
    };

    socket.onclose = (e) => {
      console.log("WebSocket Closed", e);
    };

    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [selectedConv, currentUserId]);

  const json_parse_safe = (str: string) => {
    try {
      return JSON.parse(str);
    } catch (e) {
      return null;
    }
  };

  const handleTyping = () => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({
        type: 'typing',
        is_typing: true
      }));

      if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
      
      typingTimeoutRef.current = setTimeout(() => {
        if (socketRef.current?.readyState === WebSocket.OPEN) {
          socketRef.current.send(JSON.stringify({
            type: 'typing',
            is_typing: false
          }));
        }
      }, 3000);
    }
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedConv || !socketRef.current) return;

    if (socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({
        type: 'chat_message',
        message: newMessage.trim()
      }));
      setNewMessage('');
      
      if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
      socketRef.current.send(JSON.stringify({
        type: 'typing',
        is_typing: false
      }));
    }
  };

  const getOtherParticipant = (conv: Conversation) => {
    return conv.participant_1.id === currentUserId ? conv.participant_2 : conv.participant_1;
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    if (date.toDateString() === now.toDateString()) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  return (
    <ProtectedRoute>
      <div className="flex-1 flex overflow-hidden bg-zinc-50 dark:bg-zinc-950 p-4 lg:p-6 h-[calc(100vh-64px)]">
        <div className="max-w-7xl mx-auto w-full flex bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-xl overflow-hidden relative">
          
          {/* Sidebar */}
          <div className={`w-full lg:w-80 border-r border-zinc-200 dark:border-zinc-800 flex flex-col transition-all duration-300 ${!showMobileList ? 'hidden lg:flex' : 'flex'}`}>
            <div className="p-6 border-b border-zinc-200 dark:border-zinc-800">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">Messages</h2>
                <div className="w-8 h-8 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-[10px] font-bold text-zinc-500">
                  ID:{currentUserId}
                </div>
              </div>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" size={16} />
                <input 
                  type="text" 
                  placeholder="Search chats..." 
                  className="w-full bg-zinc-100 dark:bg-zinc-800 border-none rounded-xl py-2 pl-10 pr-4 text-sm focus:ring-2 focus:ring-zinc-900 dark:focus:ring-zinc-100 transition-all"
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto">
              {isLoadingConv ? (
                <div className="p-8 text-center text-zinc-400">Loading chats...</div>
              ) : conversations.length === 0 ? (
                <div className="p-8 text-center">
                  <div className="w-12 h-12 bg-zinc-100 dark:bg-zinc-800 rounded-full flex items-center justify-center mx-auto mb-4 text-zinc-400">
                    <MessageSquare size={20} />
                  </div>
                  <p className="text-zinc-500 text-sm">No conversations yet.</p>
                </div>
              ) : (
                conversations.map(conv => {
                  const other = getOtherParticipant(conv);
                  const isActive = selectedConv?.id === conv.id;
                  return (
                    <div 
                      key={conv.id}
                      onClick={() => { setSelectedConv(conv); setShowMobileList(false); }}
                      className={`p-4 border-b border-zinc-100 dark:border-zinc-800/50 cursor-pointer transition-all hover:bg-zinc-50 dark:hover:bg-zinc-800/50 ${isActive ? 'bg-zinc-100/80 dark:bg-zinc-800/80 border-l-4 border-l-zinc-900 dark:border-l-zinc-100' : ''}`}
                    >
                      <div className="flex gap-3">
                        <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-zinc-200 to-zinc-100 dark:from-zinc-800 dark:to-zinc-700 flex items-center justify-center shrink-0 border border-zinc-200 dark:border-zinc-700">
                          <User size={20} className="text-zinc-500 dark:text-zinc-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex justify-between items-start mb-0.5">
                            <h3 className="font-bold text-zinc-900 dark:text-zinc-50 truncate text-sm">{other.username}</h3>
                            <span className="text-[10px] text-zinc-400">{conv.last_message ? formatDate(conv.last_message.created_at) : ''}</span>
                          </div>
                          <p className="text-[11px] font-medium text-blue-600 dark:text-blue-400 flex items-center gap-1 mb-1 truncate">
                            <Briefcase size={10} /> {conv.job?.position || conv.job?.work}
                          </p>
                          <div className="flex justify-between items-center">
                             <p className="text-xs text-zinc-500 dark:text-zinc-400 truncate pr-2">
                               {conv.last_message ? conv.last_message.content : 'No messages yet'}
                             </p>
                             {conv.unread_count > 0 && (
                               <span className="w-5 h-5 bg-zinc-900 dark:bg-zinc-50 text-white dark:text-zinc-900 text-[10px] font-bold rounded-full flex items-center justify-center shrink-0">
                                 {conv.unread_count}
                               </span>
                             )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Main Chat Area */}
          <div className={`flex-1 flex flex-col bg-zinc-50/30 dark:bg-zinc-900/10 ${showMobileList ? 'hidden lg:flex' : 'flex'}`}>
            {selectedConv ? (
              <>
                {/* Chat Header */}
                <div className="p-4 lg:p-6 border-b border-zinc-200 dark:border-zinc-800 flex items-center gap-4 bg-white/50 dark:bg-zinc-900/50 backdrop-blur-sm sticky top-0 z-10">
                  <button 
                    onClick={() => setShowMobileList(true)}
                    className="lg:hidden p-2 rounded-full hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500 transition-colors"
                  >
                    <ArrowLeft size={20} />
                  </button>
                  <div className="w-10 h-10 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center border border-zinc-200 dark:border-zinc-700">
                    <User size={18} className="text-zinc-500 dark:text-zinc-400" />
                  </div>
                  <div>
                    <h3 className="font-bold text-zinc-900 dark:text-zinc-50">{getOtherParticipant(selectedConv).username}</h3>
                    <p className="text-xs text-zinc-500 flex items-center gap-1">
                      <Briefcase size={12} /> {selectedConv.job?.position || selectedConv.job?.work} @ {selectedConv.job?.company || 'Job Post'}
                    </p>
                  </div>
                </div>

                {/* Messages List */}
                <div className="flex-1 overflow-y-auto p-4 lg:p-8 space-y-4">
                  {isLoadingMsgs ? (
                    <div className="flex items-center justify-center h-full text-zinc-400 text-sm">Loading messages...</div>
                  ) : messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-zinc-400">
                      <p className="text-sm italic">Send a message to start the conversation</p>
                    </div>
                  ) : (
                    messages.map(msg => {
                      const isMe = msg.sender === currentUserId;
                      return (
                        <div key={msg.id} className={`flex ${isMe ? 'justify-end' : 'justify-start'}`}>
                          <div className={`max-w-[80%] lg:max-w-[70%] px-4 py-2.5 rounded-2xl text-sm shadow-sm transition-all ${
                            isMe 
                              ? 'bg-zinc-900 text-white dark:bg-zinc-50 dark:text-zinc-900 rounded-tr-none' 
                              : 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50 border border-zinc-100 dark:border-zinc-700 rounded-tl-none'
                          }`}>
                            <p className="leading-relaxed">{msg.content}</p>
                            <span className={`text-[9px] mt-1 block opacity-60 text-right`}>
                              {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                        </div>
                      );
                    })
                  )}
                  
                  {/* Typing Indicator - Show ONLY for other user */}
                  {isOtherTyping && (
                    <div className="flex justify-start animate-in fade-in slide-in-from-bottom-2 duration-300">
                      <div className="bg-white dark:bg-zinc-800 border border-zinc-100 dark:border-zinc-700 px-4 py-3 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-1">
                        <div className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                        <div className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                        <div className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce"></div>
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>

                {/* Message Input */}
                <div className="p-4 lg:p-6 bg-white dark:bg-zinc-900 border-t border-zinc-200 dark:border-zinc-800">
                  <form onSubmit={handleSendMessage} className="flex gap-3">
                    <input 
                      type="text" 
                      value={newMessage}
                      onChange={(e) => {
                        setNewMessage(e.target.value);
                        handleTyping();
                      }}
                      placeholder="Type a message..." 
                      className="flex-1 bg-zinc-100 dark:bg-zinc-800 border-none rounded-2xl py-3 px-6 text-sm focus:ring-2 focus:ring-zinc-900 dark:focus:ring-zinc-100 transition-all"
                    />
                    <button 
                      type="submit"
                      disabled={!newMessage.trim()}
                      className="w-12 h-12 bg-zinc-900 dark:bg-zinc-50 text-white dark:text-zinc-900 rounded-2xl flex items-center justify-center hover:scale-105 active:scale-95 transition-all disabled:opacity-50 disabled:hover:scale-100 cursor-pointer"
                    >
                      <Send size={18} />
                    </button>
                  </form>
                </div>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                <div className="w-20 h-20 bg-zinc-100 dark:bg-zinc-800 rounded-3xl flex items-center justify-center mb-6 text-zinc-300 dark:text-zinc-700">
                  <MessageSquare size={40} />
                </div>
                <h3 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">Your Conversations</h3>
                <p className="text-zinc-500 max-w-xs text-sm">Select a chat from the sidebar to view messages or start a new conversation by applying to jobs.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
};

export default Messages;
