// src/components/Navbar.tsx
import React from 'react';
import { Link } from 'react-router-dom';

export default function Navbar() {
  return (
    <nav className="bg-white border-b shadow-sm sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <div className="text-xl font-bold text-blue-600">Agent Admin</div>
          <ul className="flex space-x-6 text-sm font-medium text-gray-700">
            <li>
              <Link to="/" className="hover:text-blue-600 transition">Dashboard</Link>
            </li>
            <li>
              <Link to="/virtual_assistants" className="hover:text-blue-600 transition">Virtual Assistants</Link>
            </li>
            <li>
              <Link to="/mcp_servers" className="hover:text-blue-600 transition">MCP Servers</Link>
            </li>
            <li>
              <Link to="/knowledge_bases" className="hover:text-blue-600 transition">Knowledge Bases</Link>
            </li>
            <li>
              <Link to="/model_servers" className="hover:text-blue-600 transition">Model Servers</Link>
            </li>
            <li>
              <Link to="/chat" className="hover:text-blue-600 transition">Chat</Link>
            </li>
          </ul>
        </div>
      </div>
    </nav>
  );
}
