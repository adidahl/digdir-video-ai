export interface MessageSource {
  video_id: string;
  video_title: string;
  timestamp: number;
  text: string;
  url: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  sources?: MessageSource[];
  created_at: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  organization_id: string;
  title: string | null;
  created_at: string;
  updated_at: string | null;
  message_count?: number;
}

export interface ConversationWithMessages extends Conversation {
  messages: Message[];
}

export interface ChatRequest {
  message: string;
  conversation_id?: string | null;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  answer: string;
  sources: MessageSource[];
  created_at: string;
}

