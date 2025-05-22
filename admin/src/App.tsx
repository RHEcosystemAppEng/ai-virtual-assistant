import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import VirtualAssistantPage from './pages/VirtualAssistantPage';
import MCPServerPage from './pages/MCPServerPage';
import KnowledgeBasePage from './pages/KnowledgeBasePage';
import ModelServerPage from './pages/ModelServerPage';
import ChatPage from './pages/ChatPage';
import Navbar from './components/Navbar';

export default function App() {
  return (
    <Router>
      <Navbar />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/virtual_assistants" element={<VirtualAssistantPage />} />
        <Route path="/mcp_servers" element={<MCPServerPage />} />
        <Route path="/knowledge_bases" element={<KnowledgeBasePage />} />
        <Route path="/model_servers" element={<ModelServerPage />} />
        <Route path="/chat" element={<ChatPage />} />
      </Routes>
    </Router>
  );
}
