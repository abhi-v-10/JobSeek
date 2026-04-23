import api from '../lib/axios';

export interface Conversation {
  id: number;
  participant_1: { id: number; username: string; email: string; profile_picture?: string };
  participant_2: { id: number; username: string; email: string; profile_picture?: string };
  job: { id: number; position?: string; work?: string; company?: string; posted_by?: number };
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
  content: string | null;
  attachment?: string | null;
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

  sendMessage: async (conversationId: number, content: string, file?: File | null): Promise<Message> => {
    if (file) {
      const formData = new FormData();
      formData.append('conversation', conversationId.toString());
      if (content) formData.append('content', content);
      formData.append('attachment', file);
      
      const response = await api.post('/messages/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      return response.data;
    } else {
      const response = await api.post('/messages/', {
        conversation: conversationId,
        content: content
      });
      return response.data;
    }
  }
};
