import { CHAT_SESSIONS_API_ENDPOINT } from '@/config/api';

type ImageContentItemImage = {
  data?: string,
  uri?: string,
};

export type ImageContentItem = {
  image: ImageContentItemImage
  type: 'image',
};

export type TextContentItem = {
  text: string,
  type: 'text',
};

export type InterleavedContent = TextContentItem | ImageContentItem | Array<TextContentItem | ImageContentItem>;

export interface ChatSessionSummary {
  id: string;
  title: string;
  agent_name: string;
  updated_at: string;
  created_at: string;
}

export interface ChatSessionDetail {
  id: string;
  title: string;
  agent_name: string;
  agent_id: string;
  messages: Array<{
    role: 'user' | 'assistant';
    content: InterleavedContent;
  }>;
  created_at: string;
  updated_at: string;
}

export async function fetchChatSessions(agentId?: string): Promise<ChatSessionSummary[]> {
  const url = agentId
    ? `${CHAT_SESSIONS_API_ENDPOINT}?agent_id=${agentId}`
    : CHAT_SESSIONS_API_ENDPOINT;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error('Failed to fetch chat sessions');
  }
  return response.json() as Promise<ChatSessionSummary[]>;
}

export async function fetchChatSession(
  sessionId: string,
  agentId: string
): Promise<ChatSessionDetail> {
  const response = await fetch(`${CHAT_SESSIONS_API_ENDPOINT}${sessionId}?agent_id=${agentId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch chat session');
  }
  return response.json() as Promise<ChatSessionDetail>;
}

export async function deleteChatSession(sessionId: string, agentId: string): Promise<void> {
  const response = await fetch(`${CHAT_SESSIONS_API_ENDPOINT}${sessionId}?agent_id=${agentId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete chat session');
  }
}

export async function createChatSession(
  agentId: string,
  sessionName?: string
): Promise<ChatSessionDetail> {
  const response = await fetch(CHAT_SESSIONS_API_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      agent_id: agentId,
      session_name: sessionName,
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to create chat session');
  }
  return response.json() as Promise<ChatSessionDetail>;
}
