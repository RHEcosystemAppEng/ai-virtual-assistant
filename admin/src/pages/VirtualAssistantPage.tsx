import React, { useEffect, useState } from 'react';
import axios from '../api/axios';

interface VirtualAssistant {
  id?: string;
  name: string;
  prompt: string;
  model_name: string;
  created_by?: string;
  knowledge_base_ids: string[];
  mcp_server_ids: string[];
}

export default function VirtualAssistantPage() {
  const [form, setForm] = useState<VirtualAssistant>({
    name: '',
    prompt: '',
    model_name: '',
    created_by: '',
    knowledge_base_ids: [],
    mcp_server_ids: []
  });
  const [assistants, setAssistants] = useState<VirtualAssistant[]>([]);
  const [knowledgeBases, setKnowledgeBases] = useState<any[]>([]);
  const [mcpServers, setMcpServers] = useState<any[]>([]);
  const [models, setModels] = useState<{id: string, name: string}[]>([]);

  useEffect(() => {
    // Fetch models from LlamaStack
    axios.get('/llama_stack/llms')
      .then(res => {
        console.log('Models response:', res.data);
        setModels(res.data);
      })
      .catch(err => {
        console.error('Error fetching models:', err);
        alert('Failed to fetch models: ' + err.message);
      });
    axios.get('/llama_stack/knowledge_bases')
      .then(res => {
        console.log('Knowledge bases response:', res.data);
        setKnowledgeBases(res.data);
      })
      .catch(err => {
        console.error('Error fetching knowledge bases:', err);
        alert('Failed to fetch knowledge bases: ' + err.message);
      });
    axios.get('/llama_stack/mcp_servers')
      .then(res => {
        console.log('MCP servers response:', res.data);
        setMcpServers(res.data);
      })
      .catch(err => {
        console.error('Error fetching MCP servers:', err);
        alert('Failed to fetch MCP servers: ' + err.message);
      });
    fetchAssistants();
  }, []);

  const fetchAssistants = async () => {
    const res = await axios.get('/virtual_assistants');
    setAssistants(res.data);
  };

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setForm(prev => ({
      ...prev,
      model_name: e.target.value
    }));
  };

  const handleSubmit = async () => {
    try {
      if (form.id) {
        await axios.put(`/virtual_assistants/${form.id}`, form);
      } else {
        await axios.post('/virtual_assistants', form);
      }
      setForm({ name: '', prompt: '', model_name: '', created_by: '', knowledge_base_ids: [], mcp_server_ids: [] });
      fetchAssistants();
    } catch (err) {
      alert('Failed to save virtual assistant');
    }
  };

  const handleEdit = (a: VirtualAssistant) => {
    setForm({ ...a });
  };

  const handleDelete = async (id: string) => {
    await axios.delete(`/virtual_assistants/${id}`);
    fetchAssistants();
  };

  const toggleSelection = (id: string, type: 'kb' | 'mcp') => {
    if (type === 'kb') {
      setForm(prev => ({
        ...prev,
        knowledge_base_ids: prev.knowledge_base_ids.includes(id)
          ? prev.knowledge_base_ids.filter(kb => kb !== id)
          : [...prev.knowledge_base_ids, id]
      }));
    } else {
      setForm(prev => ({
        ...prev,
        mcp_server_ids: prev.mcp_server_ids.includes(id)
          ? prev.mcp_server_ids.filter(mcp => mcp !== id)
          : [...prev.mcp_server_ids, id]
      }));
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Virtual Assistants</h1>

      <div className="space-y-4 mb-8">
        <input className="w-full border p-2 rounded" placeholder="Name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
        <textarea className="w-full border p-2 rounded" placeholder="Prompt" value={form.prompt} onChange={e => setForm({ ...form, prompt: e.target.value })} rows={4} />
        <select 
          className="w-full border p-2 rounded bg-white" 
          value={form.model_name} 
          onChange={handleModelChange}
        >
          <option value="">Select a model</option>
          {models.map(model => (
            <option key={model.id} value={model.id}>{model.name}</option>
          ))}
        </select>
       
        <div>
          <h2 className="font-semibold">Select Knowledge Bases</h2>
          <div className="space-y-1">
            {knowledgeBases.map(kb => (
              <label key={kb.id} className="flex items-center space-x-2">
                <input type="checkbox" checked={form.knowledge_base_ids.includes(kb.id)} onChange={() => toggleSelection(kb.id, 'kb')} />
                <span>{kb.name}</span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <h2 className="font-semibold">Select MCP Servers</h2>
          <div className="space-y-1">
            {mcpServers.map(mcp => (
              <label key={mcp.id} className="flex items-center space-x-2">
                <input type="checkbox" checked={form.mcp_server_ids.includes(mcp.id)} onChange={() => toggleSelection(mcp.id, 'mcp')} />
                <span>{mcp.name}</span>
              </label>
            ))}
          </div>
        </div>

        <button onClick={handleSubmit} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          {form.id ? 'Update' : 'Create'}
        </button>
      </div>

      <ul className="space-y-3">
        {assistants.map(assistant => (
          <li key={assistant.id} className="bg-white p-4 rounded shadow flex justify-between items-start">
            <div>
              <strong>{assistant.name}</strong>
              <p className="text-sm text-gray-600">Model: {assistant.model_name}</p>
              <p className="text-sm text-gray-500 whitespace-pre-wrap">{assistant.prompt}</p>
            </div>
            <div className="space-x-2">
              <button onClick={() => handleEdit(assistant)} className="text-yellow-600 hover:underline">Edit</button>
              <button onClick={() => handleDelete(assistant.id!)} className="text-red-600 hover:underline">Delete</button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
