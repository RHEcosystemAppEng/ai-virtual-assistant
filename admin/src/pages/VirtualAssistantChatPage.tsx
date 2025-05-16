import React, { useState, useEffect, JSX } from 'react';
import axios from '../api/axios';

interface VirtualAssistant {
  id: string;
  name: string;
  prompt: string;
  model_name: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface Components {
  model_server: {
    id: string;
    name: string;
    provider_name: string;
    model_name: string;
    endpoint_url: string;
  };
  knowledge_bases: Array<{
    id: string;
    name: string;
    version: string;
    embedding_model: string;
    vector_db_name: string;
    is_external: boolean;
    source?: string;
    source_configuration?: any;
  }>;
  tools: Array<{
    id: string;
    name: string;
    title: string;
    description: string;
    endpoint_url: string;
    configuration: any;
  }>;
}

export default function VirtualAssistantChatPage(): JSX.Element {
  const [virtualAssistants, setVirtualAssistants] = useState<VirtualAssistant[]>([]);
  const [selectedAssistant, setSelectedAssistant] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [components, setComponents] = useState<Components | null>(null);

  useEffect(() => {
    const fetchVirtualAssistants = async () => {
      try {
        const response = await axios.get('/virtual_assistants/');
        setVirtualAssistants(response.data);
        if (response.data.length > 0) {
          setSelectedAssistant(response.data[0].id);
        }
      } catch (err) {
        console.error('Error fetching virtual assistants:', err);
        setError('Failed to load virtual assistants');
      }
    };
    fetchVirtualAssistants();
  }, []);

  useEffect(() => {
    const fetchComponents = async () => {
      if (!selectedAssistant) return;
      
      try {
        const response = await axios.get(`/virtual_assistants/${selectedAssistant}/components`);
        setComponents(response.data);
      } catch (err) {
        console.error('Error fetching components:', err);
        setError('Failed to load components');
      }
    };
    fetchComponents();
  }, [selectedAssistant]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !selectedAssistant) return;

    setIsLoading(true);
    setError('');

    // Add user message immediately
    const userMessage: Message = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      role: 'user',
      content: input
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');

    try {
      console.log('Sending request with:', {
        virtualAssistantId: selectedAssistant,
        messages: [...messages, userMessage]
      });

      const response = await fetch('http://localhost:8000/llama_stack/vachat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          virtualAssistantId: selectedAssistant,
          messages: [...messages, userMessage].map(msg => ({
            id: msg.id,
            role: msg.role,
            content: msg.content,
            parts: []
          }))
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No reader available');

      let assistantMessage = '';
      const messageId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = new TextDecoder().decode(value);
        const lines = text.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;
            
            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                assistantMessage += parsed.content;
                setMessages(prev => {
                  const lastMessage = prev[prev.length - 1];
                  if (lastMessage && lastMessage.id === messageId) {
                    return [...prev.slice(0, -1), { ...lastMessage, content: assistantMessage }];
                  }
                  return [...prev, { id: messageId, role: 'assistant', content: assistantMessage }];
                });
              }
            } catch (e) {
              console.error('Error parsing message:', e);
            }
          }
        }
      }
    } catch (err) {
      console.error('Error in chat:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Virtual Assistant Chat</h1>
      
      <div className="mb-4">
        <select
          value={selectedAssistant}
          onChange={(e) => setSelectedAssistant(e.target.value)}
          className="w-full p-2 border rounded"
        >
          <option value="">Select an assistant</option>
          {virtualAssistants.map(va => (
            <option key={va.id} value={va.id}>{va.name}</option>
          ))}
        </select>
      </div>

      {components && (
        <div className="mb-4 p-4 bg-gray-50 rounded-lg">
          <h2 className="text-lg font-semibold mb-2">Components</h2>
          
          <div className="mb-2">
            <h3 className="font-medium">Model Server</h3>
            <p className="text-sm text-gray-600">
              {components.model_server.name} ({components.model_server.provider_name})
            </p>
          </div>

          <div className="mb-2">
            <h3 className="font-medium">Knowledge Bases</h3>
            <ul className="text-sm text-gray-600">
              {components.knowledge_bases.map(kb => (
                <li key={kb.id}>{kb.name} (v{kb.version})</li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="font-medium">Tools</h3>
            <ul className="text-sm text-gray-600">
              {components.tools.map(tool => (
                <li key={tool.id}>{tool.title}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {error && (
        <div className="mb-4 p-2 bg-red-100 text-red-700 rounded">
          {error}
        </div>
      )}

      <div className="mb-4 h-96 overflow-y-auto border rounded p-4">
        {messages.map(msg => (
          <div
            key={msg.id}
            className={`mb-2 p-2 rounded ${
              msg.role === 'user' ? 'bg-blue-100 ml-12' : 'bg-gray-100 mr-12'
            }`}
          >
            <div className="font-semibold">{msg.role === 'user' ? 'You' : 'Assistant'}</div>
            <div className="whitespace-pre-wrap">{msg.content}</div>
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          className="flex-1 p-2 border rounded"
          disabled={isLoading}
        />
        <button
          type="submit"
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-blue-300"
          disabled={isLoading || !input.trim()}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  );
}
