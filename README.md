# PurviewCopilot

A hybrid AI-powered data governance assistant that combines **Microsoft 365 Graph Connector** (or **Microsoft Purview API**), **Azure AI Search**, and **Azure OpenAI** to provide intelligent search, deep reasoning analysis, and dynamic knowledge graph capabilities for data governance and compliance insights.

## 🚀 Overview

PurviewCopilot enables organizations to:
- **Search across data assets** indexed through Microsoft Graph Connectors or Purview API
- **Perform hybrid search** combining semantic vector search with traditional keyword search
- **Generate AI-powered insights** using Azure OpenAI for data governance decisions
- **Build dynamic knowledge graphs** to visualize relationships between data assets
- **Automate compliance analysis** with deep reasoning capabilities

## 🏗️ Architecture

```
┌─────────────────────┐
│  M365 Graph         │
│  Connector          │
│  (External Items)   │
│  OR                 │
│  Purview API        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Azure AI Search    │
│  (Vector + Text)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Azure OpenAI       │
│  (Embeddings +      │
│   GPT Reasoning)    │
└─────────────────────┘
```

## ✨ Key Features

### 1. **Hybrid Search**
- Combines vector similarity search with full-text search
- Uses Azure OpenAI embeddings (text-embedding-3-large) for semantic understanding
- HNSW algorithm for efficient vector search

### 2. **Deep Reasoning Analysis**
- Leverages GPT-4o-mini for contextual analysis
- Provides insights on data sensitivity, compliance risks, and recommended actions
- Interprets search results with domain-specific governance knowledge

### 3. **Knowledge Graph Generation**
- Automatically infers relationships between data assets
- Extracts semantic connections (e.g., "contains", "references", "derived_from")
- Returns structured JSON graph data for visualization

### 4. **Microsoft Authentication**
- MSAL-based device code flow for secure authentication
- Supports both managed identity and API key authentication modes
- Token caching for improved performance

### 5. **Flexible Data Source Integration**
- **Microsoft Graph Connector**: Index external items from various sources
- **Microsoft Purview API**: Direct integration with Purview data catalog (optional)
- Choose the data source that best fits your architecture

## 📋 Prerequisites

- **Azure Subscription** with the following resources:
  - Azure OpenAI Service
  - Azure AI Search
  - Microsoft Purview (optional, depending on your data source)
- **Microsoft 365** tenant with Graph Connector configured (if using Graph API)
- **Python 3.8+**

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ikanwal/PurviewCopilot.git
   cd PurviewCopilot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   
   Create a `.env` file in the project root:
   ```env
   # Azure AD Configuration
   TENANT_ID=your-tenant-id
   PURVIEW_CLIENT_ID=your-client-id
   GRAPH_CONNECTION_ID=PurviewNASA  # Only needed if using Graph Connector
   
   # Azure OpenAI Configuration
   AZURE_OPENAI_ENDPOINT=https://your-openai-endpoint.openai.azure.com
   AZURE_OPENAI_API_KEY=your-api-key
   AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
   AZURE_OPENAI_API_VERSION=2024-02-15-preview
   AZURE_OPENAI_AUTH_MODE=key  # or managed_identity
   
   # Azure AI Search Configuration
   AZURE_AI_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
   AZURE_AI_SEARCH_API_KEY=your-search-key
   AZURE_AI_SEARCH_AUTH_MODE=key  # or managed_identity
   AZURE_AI_SEARCH_INDEX_NAME=purview-items
   AZURE_AI_SEARCH_VECTOR_FIELD=contentVector
   AZURE_AI_SEARCH_TEXT_FIELD=content
   AZURE_AI_SEARCH_TITLE_FIELD=title
   AZURE_AI_SEARCH_URL_FIELD=url
   ```

## 🎯 Usage

### Index Data from Graph Connector

```python
from hybrid_m365_graph_deep_reasoning_2025 import get_token, index_graph_connector_items

# Authenticate
auth_result = get_token()
token = auth_result['access_token']

# Index items from Graph Connector
index_graph_connector_items(token, size=50)
```

### Perform Hybrid Search

```python
from hybrid_m365_graph_deep_reasoning_2025 import hybrid_search

# Search for data assets
results = hybrid_search("customer data sensitivity", top=5)

for result in results:
    print(f"Title: {result['title']}")
    print(f"Content: {result['content']}\n")
```

### Deep Reasoning Analysis

```python
from hybrid_m365_graph_deep_reasoning_2025 import hybrid_search, deep_reasoning_analysis

# Search and analyze
query = "What PII data exists in our systems?"
results = hybrid_search(query, top=3)
insights = deep_reasoning_analysis(query, results)

print(insights)
```

### Generate Knowledge Graph

```python
from hybrid_m365_graph_deep_reasoning_2025 import hybrid_search, infer_knowledge_graph_relationships

# Get search results
results = hybrid_search("database schemas", top=5)

# Infer relationships
graph = infer_knowledge_graph_relationships(results)
print(graph)
# Output: [{"source": "CustomerDB", "relation": "contains", "target": "UserTable"}, ...]
```

## 📁 Project Structure

```
PurviewCopilot/
├── hybrid_m365_graph_deep_reasoning_2025.py  # Main application logic
├── fetch_response.py                          # Helper functions
├── requirements.txt                           # Python dependencies
├── host.json                                  # Azure Functions configuration
├── local.settings.json                        # Local development settings
├── openapi.json                               # API specification
├── openapi.zip                                # Packaged API spec
├── .funcignore                                # Azure Functions ignore file
└── README.md                                  # This file
```

## 🔧 Configuration Options

### Data Source Options

**Option 1: Microsoft Graph Connector** (Current Implementation)
- Use the Graph API to query external items
- Requires `GRAPH_CONNECTION_ID` configuration
- Ideal for federated search across multiple sources

**Option 2: Microsoft Purview API** (Alternative)
- Direct integration with Purview data catalog
- Query assets, glossaries, and lineage directly
- Modify the `graph_search()` function to use Purview REST API endpoints

### Authentication Modes

- **Key-based**: Set `AZURE_OPENAI_AUTH_MODE=key` and `AZURE_AI_SEARCH_AUTH_MODE=key`
- **Managed Identity**: Set both to `managed_identity` (recommended for production)

### Search Index Schema

The default index includes:
- `id` (key)
- `title`, `content`, `userDescription` (searchable text fields)
- `tags`, `classifications`, `qualifiedName` (metadata fields)
- `contentVector` (3072-dimensional embedding vector)

## 🔐 Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use managed identities** in production environments
3. **Rotate API keys** regularly
4. **Enable Azure RBAC** for fine-grained access control
5. **Monitor Azure OpenAI usage** to prevent cost overruns

## 🚀 Deployment

### Deploy to Azure Functions

1. Package the application:
   ```bash
   func azure functionapp publish <your-function-app-name>
   ```

2. Configure application settings in Azure Portal:
   - Add all environment variables from `.env`
   - Enable managed identity
   - Assign appropriate RBAC roles

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Microsoft Graph API** for external item search
- **Microsoft Purview API** for data catalog integration
- **Azure OpenAI Service** for embeddings and reasoning
- **Azure AI Search** for hybrid search capabilities

## 📞 Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Built with ❤️ by [ikanwal](https://github.com/ikanwal)**