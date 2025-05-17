const baseUrl = import.meta.env.VITE_API_BASE_URL || ''; // fallback to '' for relative paths in prod

export default baseUrl;

export const AI_MODELS_API_ENDPOINT = '/api/llama_stack/llms';
export const KNOWLEDGE_BASES_API_ENDPOINT = '/api/llama_stack/knowledge_bases';
export const TOOLS_API_ENDPOINT = '/api/llama_stack/mcp_servers';
// export const AGENTS_API_ENDPOINT = '/api/virtual_assistants/';
export const AGENTS_API_ENDPOINT = 'http://localhost:8000/virtual_assistants/';
