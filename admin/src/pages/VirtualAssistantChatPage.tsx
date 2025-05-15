import React, { useState, useEffect, JSX} from 'react';
import axios from '../api/axios';

interface VirtualAssistant {
  id: string;
  name: string;
  prompt: string;
  model_name: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export default function VirtualAssistantChatPage(): JSX.Element {
  const [virtualAssistants, setVirtualAssistants] = useState<VirtualAssistant[]>([]);
  const [selectedAssistant, setSelectedAssistant] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

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

        // Convert the chunk to text
        const chunk = new TextDecoder().decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;

            try {
              const parsed = JSON.parse(data);
              if (parsed.choices?.[0]?.delta?.content) {
                assistantMessage += parsed.choices[0].delta.content;
                setMessages(prev => {
                  const lastMessage = prev[prev.length - 1];
                  if (lastMessage.role === 'assistant') {
                    return [
                      ...prev.slice(0, -1),
                      { ...lastMessage, content: assistantMessage }
                    ];
                  } else {
                    return [
                      ...prev,
                      {
                        id: messageId,
                        role: 'assistant',
                        content: assistantMessage
                      }
                    ];
                  }
                });
              }
            } catch (e) {
              console.error('Error parsing chunk:', e);
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
    <div className="max-w-4xl mx-auto p-4 flex flex-col min-h-screen">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-4 text-center">Virtual Assistant Chat</h1>
        <select
          value={selectedAssistant}
          onChange={(e) => {
            console.log('Selecting assistant:', e.target.value);
            setSelectedAssistant(e.target.value);
          }}
          className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 mb-4"
          disabled={isLoading}
        >
          <option value="">Select a virtual assistant</option>
          {virtualAssistants.map((assistant) => (
            <option key={assistant.id} value={assistant.id}>
              {assistant.name} ({assistant.id})
            </option>
          ))}
        </select>
        {error && <div className="text-red-500 text-center mb-4">{error}</div>}
      </div>
      
      <div className="flex-1 overflow-y-auto mb-4 space-y-4">
        {messages.map((message, index) => (
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
          disabled={isLoading}
          className={`px-4 py-2 text-white rounded-lg focus:outline-none ${
            isLoading ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-500 hover:bg-blue-600'
          }`}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  );
}
