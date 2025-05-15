import React, { useState, useEffect, FormEvent, JSX } from 'react';
import axios from '../api/axios';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface Model {
  id: string;
  name: string;
}

interface VirtualAssistant {
  id: string;
  name: string;
  prompt: string;
  model_name: string;
}

export default function ChatPage(): JSX.Element {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [availableModels, setAvailableModels] = useState<Model[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [virtualAssistants, setVirtualAssistants] = useState<VirtualAssistant[]>([]);
  const [selectedAssistant, setSelectedAssistant] = useState<string>('');
  const [sessionId, setSessionId] = useState<string>('');

  // Fetch available models on component mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await axios.get('/llama_stack/llms');
        const models = response.data as Model[];
        if (models && models.length > 0) {
          setAvailableModels(models);
          setSelectedModel(models[0].id);
        }
      } catch (err) {
        console.error('Error fetching models:', err);
        setError(new Error('Failed to load LLM models'));
      } finally {
        setIsLoading(false);
      }
    };
    fetchModels();
  }, []);

  // Fetch available virtual assistants on component mount
  useEffect(() => {
    const fetchVirtualAssistants = async () => {
      try {
        const response = await axios.get('/virtual_assistants/');
        const vas = response.data as VirtualAssistant[];
        if (vas && vas.length > 0) {
          setVirtualAssistants(vas);
          setSelectedAssistant(vas[0].id);
        }
      } catch (err) {
        console.error('Error fetching models:', err);
        setError(new Error('Failed to load LLM models'));
      } finally {
        setIsLoading(false);
      }
    };
    fetchVirtualAssistants();
  }, []);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim() || isLoading || !selectedModel) {
      if (!selectedModel) {
        setError(new Error('No model selected'));
      }
      return;
    }

    const userMessage = { role: 'user' as const, content: input.trim() };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput('');
    setIsLoading(true);
    setError(null);

    // Create empty assistant message
    const assistantMessage = { role: 'assistant' as const, content: '' };
    const allMessages = [...updatedMessages, assistantMessage];
    setMessages(allMessages);

    try {
      // Use fetch for streaming
      const chatResponse = await fetch('http://localhost:8000/llama_stack/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'SessionId': sessionId
        },
        body: JSON.stringify({
          virtualAssistantId: selectedAssistant,
          messages: updatedMessages,
          stream: true,
          sessionId: sessionId
        })
      });

      if (!chatResponse.ok) {
        throw new Error(`HTTP error! status: ${chatResponse.status}`);
      }

      const reader = chatResponse.body?.getReader();
      if (!reader) throw new Error('No reader available');

      let buffer = '';
      const decoder = new TextDecoder('utf-8'); // Specify the encoding
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          // Decode the chunk and process any complete SSE messages
          const chunk = decoder.decode(value, { stream: true });
          // Split on double newlines to preserve message boundaries
          const lines = chunk.split('\n\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const text = line.slice(6);
              if (text.trim() === '[DONE]') {
                break;
              } else if (text.trim().startsWith('Error:')) {
                throw new Error(text.trim().slice(7));
              } else {
                let json;
                try {
                  json = JSON.parse(text);
                } catch (e) {
                  console.error('Error parsing JSON:', e);
                  console.log('Skipped processing text:', text);
                  continue
                }
                if (json.type === 'session' && json.sessionId) {
                  setSessionId(json.sessionId);
                }
                if (json.type === 'text' && json.content) {
                  const text = json.content;
                  // Add space after sentence endings if next chunk doesn't start with space
                  if (buffer.match(/[.!?]$/) && text && !text.startsWith(' ')) buffer += ' ';
                  buffer += text;
                  setMessages(prev => {
                    const newMessages = [...prev];
                    const lastMessage = newMessages[newMessages.length - 1];
                    if (lastMessage && lastMessage.role === 'assistant') {
                      lastMessage.content = buffer;
                    }
                    return newMessages;
                  });
                }
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    } catch (err) {
      console.error('Chat error:', err);
      setError(err instanceof Error ? err : new Error('An error occurred'));
    } finally {
      setIsLoading(false);
    }
  };

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-red-500">Error: {error.toString()}</div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-4 flex flex-col min-h-screen">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-4 text-center">Chat with LlamaStack</h1>
        <select
          value={selectedAssistant}
          onChange={(e) => setSelectedAssistant(e.target.value)}
          className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
          disabled={isLoading}
        >
          {virtualAssistants.map((assistant: VirtualAssistant, index: number) => (
            <option key={assistant.id} value={assistant.id}>
              {assistant.name || assistant.id}
            </option>
          ))}
        </select>
      </div>
      <div className="flex-1 overflow-y-auto mb-4 space-y-4">
        {messages.map((message: Message, index: number) => (
          <div
            key={index}
            className={`p-4 rounded-lg ${
              message.role === 'user' 
                ? 'bg-blue-100 ml-auto' 
                : 'bg-gray-100'
            } max-w-[80%]`}
          >
            <p className="text-sm font-semibold mb-1">
              {message.role === 'user' ? 'You' : 'Assistant'}
            </p>
            <pre className="whitespace-pre-wrap font-sans">{message.content}</pre>
          </div>
        ))}
      </div>
      <form
        onSubmit={handleSubmit}
        className="flex gap-2 sticky bottom-0 bg-white p-4 border-t">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          className="flex-1 p-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !selectedModel}
          className={`px-4 py-2 text-white rounded-lg focus:outline-none ${
            isLoading || !selectedModel ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-500 hover:bg-blue-600'
          }`}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  );
}
