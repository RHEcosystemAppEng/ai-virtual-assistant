import { useState, useCallback, useEffect } from 'react';
import { LlamaStackParser, extractSessionId } from '../adapters/llamaStackAdapter';
import { CHAT_API_ENDPOINT } from '../config/api';
import { fetchChatSession, InterleavedContent, TextContentItem } from '@/services/chat-sessions';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: InterleavedContent;
  timestamp: Date;
}

export interface UseLlamaChatOptions {
  onError?: (error: Error) => void;
  onFinish?: (message: ChatMessage) => void;
}

/**
 * Simple chat hook that directly handles LlamaStack without the AI SDK overhead
 */
export function useChat(agentId: string, options?: UseLlamaChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [attachedFiles, setAttachedFiles] = useState<string[]>([]);

  const handleInputChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, value?: string | number) => {
      const newValue = value !== undefined ? String(value) : event.target.value;
      setInput(newValue);
    },
    []
  );
  interface SessionMessage {
    role: 'user' | 'assistant' | 'system';
    content: InterleavedContent;
  }
  const loadSession = useCallback(
    async (sessionId: string) => {
      try {
        setIsLoading(true);
        console.log(`Loading session ${sessionId} for agent ${agentId}`);
        const sessionDetail = await fetchChatSession(sessionId, agentId);
        if (!sessionDetail) {
          throw new Error(`Session ${sessionId} not found for agent ${agentId}`);
        }
        console.log('Session detail:', sessionDetail);
        // Set the session ID
        setSessionId(sessionId);

        // Convert messages to our format
        const convertedMessages: ChatMessage[] = sessionDetail.messages.map(
          (msg: SessionMessage, index: number) => ({
            id: `${msg.role}-${sessionId}-${index}`,
            role: msg.role,
            content: msg.content,
            timestamp: new Date(),
          })
        );

        setMessages(convertedMessages);
        console.log('Loaded messages:', convertedMessages);
        // Update agent if different
        if (sessionDetail.agent_id && sessionDetail.agent_id !== agentId) {
          console.warn(`Loaded session for different agent: ${sessionDetail.agent_id}`);
          // Optionally handle this case, e.g., notify user or reset state
        }
      } catch (error) {
        console.error('Error loading session:', error);
        options?.onError?.(error as Error);
      } finally {
        setIsLoading(false);
      }
    },
    [agentId, options]
  );

  const clearAttachedFiles = useCallback(() => {
    setAttachedFiles([]);
  }, []);

  const sendMessage = useCallback(
    async (content: InterleavedContent) => {
      if (isLoading) return;

      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: content,
        timestamp: new Date(),
      };

      // Add user message immediately
      setMessages((prev) => [...prev, userMessage]);
      setInput('');
      setIsLoading(true);

      try {
        // Prepare request
        const requestBody = {
          virtualAssistantId: agentId,
          messages: [...messages, userMessage].map((msg) => ({
            role: msg.role,
            content: msg.content,
          })),
          stream: true,
          ...(sessionId ? { sessionId } : {}),
        };

        const response = await fetch(CHAT_API_ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
        });

        if (!response.ok) {
          throw new Error(`API error: ${response.statusText}`);
        }

        if (!response.body) {
          throw new Error('No response body');
        }

        // Create assistant message
        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: {
            text: '',
            type: 'text',
          },
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);

        // Process stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim();

              if (data === '[DONE]') {
                // Stream finished
                setMessages((prev) => {
                  const updated = [...prev];
                  const lastMsg = updated[updated.length - 1];
                  if (lastMsg && lastMsg.role === 'assistant') {
                    options?.onFinish?.(lastMsg);
                  }
                  return updated;
                });
                continue;
              }

              // Check for session ID
              const newSessionId = extractSessionId(data);
              if (newSessionId) {
                setSessionId(newSessionId);
                continue;
              }

              // Parse content
              const parsed = LlamaStackParser.parse(data);
              if (parsed) {
                setMessages((prev) => {
                  const updated = [...prev];
                  const lastMsg = updated[updated.length - 1];
                  if (lastMsg && lastMsg.role === 'assistant') {
                    // The assistant will only ever reply with a text message, never an image
                    let c: TextContentItem = lastMsg.content as TextContentItem;
                    c.text += parsed;
                    lastMsg.content = c;
                  }
                  return updated;
                });
              }
            }
          }
        }
      } catch (error) {
        console.error('Chat error:', error);
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        options?.onError?.(new Error(errorMessage));

        // Remove the loading assistant message on error
        setMessages((prev) => prev.filter((msg) => {
          msg.role !== 'assistant' || msg.content instanceof Array || msg.content.type !== 'text' || msg.content.text !== ''
        }));
      } finally {
        setIsLoading(false);
      }
    },
    [agentId, messages, sessionId, isLoading, options, attachedFiles]
  );

  const handleAttach = useCallback(
    async (data: File[]) => {
      const fileToBase64 = (file: File): Promise<string> => {
        return new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => {
            const result = reader.result as string;
            const base64 = result.split(',')[1];
            resolve(base64);
          };
          reader.onerror = () => {
            reject(new Error('Failed to read file'));
          };
          reader.readAsDataURL(file);
        });
      }
      setIsLoading(true);
      const processedData: string[] = await Promise.all(data.map(fileToBase64));
      setAttachedFiles((prev: string[]) => [...prev, ...processedData]);
      setIsLoading(false);
    },
    []
  );


  const append = useCallback(
    (message: { role: 'user' | 'assistant'; content: InterleavedContent }) => {
      void sendMessage(message.content);
    },
    [sendMessage]
  );

  // Reset state when agentId changes
  useEffect(() => {
    setMessages([]);
    setInput('');
    setAttachedFiles([]);
    setIsLoading(false);
    setSessionId(null);
  }, [agentId]);

  return {
    messages,
    input,
    handleInputChange,
    handleAttach,
    append,
    isLoading,
    loadSession,
    sessionId,
    attachedFiles,
    setAttachedFiles,
    clearAttachedFiles,
  };
}
