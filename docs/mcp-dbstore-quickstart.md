# MCP DBStore Quick Start

## 🚀 Deploy in 5 Minutes

### Prerequisites
- Kubernetes cluster with Helm 3.2+
- `kubectl` configured

### 1. Deploy
```bash
# Clone and deploy
git clone <your-repo>
cd ai-virtual-assistant

# Deploy with Helm
helm install mcp-dbstore ./deploy/helm/mcp-dbstore

# Wait for pods (2-3 minutes)
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=mcp-dbstore --timeout=300s
```

### 2. Test
```bash
# Port forward
kubectl port-forward svc/mcp-dbstore-mcp-server 8002:8002 &

# Install and run MCP inspector
pip install mcp-inspector
mcp-inspector http://localhost:8002
```

### 3. Verify Sample Data
The deployment includes 10 sample products:
- Super Widget ($29.99, 100 units)
- Mega Gadget ($79.50, 50 units)  
- Quantum Sprocket ($199.00, 30 units)
- And 7 more...

### 4. Available Tools
1. **get_products** - Browse product catalog
2. **get_product_by_id** - Get specific product
3. **search_products** - Search by name/description
4. **add_product** - Create new product
5. **remove_product** - Delete product  
6. **order_product** - Place order (updates inventory)
7. **get_product_by_name** - Exact name lookup

## 🔧 Common Configurations

### Production Deployment
```bash
helm install prod-mcp ./deploy/helm/mcp-dbstore \
  --set postgresql.persistence.size=50Gi \
  --set mcpServer.replicaCount=3 \
  --set postgresql.auth.password="$(openssl rand -base64 32)"
```

### Custom Namespace
```bash
kubectl create namespace mcp-servers
helm install mcp-dbstore ./deploy/helm/mcp-dbstore -n mcp-servers
```

### External Access
```bash
# LoadBalancer service
helm upgrade mcp-dbstore ./deploy/helm/mcp-dbstore \
  --set mcpServer.service.type=LoadBalancer
```

## 🛠️ Troubleshooting

### Pods not starting?
```bash
kubectl get pods -l app.kubernetes.io/name=mcp-dbstore
kubectl describe pod -l app.kubernetes.io/name=mcp-dbstore
```

### Database connection issues?
```bash
kubectl logs -f deployment/mcp-dbstore-postgresql
kubectl logs deployment/mcp-dbstore-mcp-server -c wait-for-db
```

### Can't connect to MCP server?
```bash
kubectl logs -f deployment/mcp-dbstore-mcp-server
kubectl get svc mcp-dbstore-mcp-server
```

## 🔗 Integration Patterns

### With LlamaStack (Actual Commands)
```bash
# Register MCP server via HTTP API
curl -X POST localhost:8321/v1/toolgroups \
  -H "Content-Type: application/json" \
  --data '{
    "provider_id": "model-context-protocol",
    "toolgroup_id": "mcp::dbstore",
    "mcp_endpoint": {
      "uri": "http://mcp-dbstore-mcp-server.default.svc.cluster.local:8002/sse"
    }
  }'

# Or via CLI (requires llama-stack-client)
llama-stack-client toolgroups register mcp::dbstore \
  --provider-id model-context-protocol \
  --mcp-config '{"uri": "http://mcp-dbstore-mcp-server.default.svc.cluster.local:8002/sse"}'

# Verify registration
llama-stack-client toolgroups list

# Use in agent (Python)
from llama_stack_client.lib.agents.agent import Agent

agent = Agent(
    client,
    model="llama-3-8b-instruct",
    instructions="You are an inventory management assistant.",
    tools=["mcp::dbstore"]
)
```

### Direct API Usage
```python
import aiohttp

async def test_tools():
    async with aiohttp.ClientSession() as session:
        # Get all products
        async with session.post("http://localhost:8002/tools/get_products") as resp:
            products = await resp.json()
        
        # Search products
        async with session.post(
            "http://localhost:8002/tools/search_products",
            json={"query": "widget"}
        ) as resp:
            results = await resp.json()
```

## 📝 Next Steps

1. **Replace Sample Data**: Update database with real inventory
2. **Scale**: Configure replicas for production load  
3. **Monitor**: Set up logging and metrics
4. **Extend**: Add new tools using existing patterns
5. **Secure**: Configure TLS and access controls

## 📚 More Info

- Helm Chart: `deploy/helm/mcp-dbstore/README.md`
- Code: `mcpservers/mcp_dbstore/`
- MCP Protocol: https://modelcontextprotocol.io/docs/