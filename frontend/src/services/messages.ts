import api from '../lib/axios';

export interface Conversation {
  id: number;
  participant_1: { id: number; username: string; email: string };
  participant_2: { id: number; username: string; email: string };
  job: { id: number; position?: string; work?: string; company?: string };
  last_message: Message | null;
  unread_count: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  conversation: number;
  sender: number;
  sender_username: string;
  receiver: number;
  content: string;
  is_read: boolean;
  created_at: string;
}

export const messagesService = {
  getConversations: async (): Promise<Conversation[]> => {
    const response = await api.get('/messages/conversations/');
    return response.data;
  },

  getMessages: async (conversationId: number): Promise<Message[]> => {
    const response = await api.get(`/messages/conversations/${conversationId}/messages/`);
    return response.data;
  },

  sendMessage: async (conversationId: number, content: string): Promise<Message> => {
    const response = await api.post('/messages/', {
      conversation: conversationId,
      content: content
    });
    return response.data;
  }
};
