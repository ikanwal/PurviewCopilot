
# -------------------------------------------------------------
# Hybrid M365 Graph Connector + Azure AI Search + Azure OpenAI
# Deep Reasoning + Dynamic Knowledge Graph Version (2025)
# -------------------------------------------------------------

import os, requests, msal, json
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType, VectorizedQuery
from azure.search.documents.indexes import SearchIndexClient
from azure.core.exceptions import HttpResponseError
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchField, SearchFieldDataType,
    VectorSearch, VectorSearchProfile, HnswAlgorithmConfiguration, VectorSearchAlgorithmKind,
    SemanticConfiguration, SemanticField, SemanticPrioritizedFields
)

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("PURVIEW_CLIENT_ID")
GRAPH_CONNECTION_ID = os.getenv("GRAPH_CONNECTION_ID", "PurviewNASA")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
AZURE_OPENAI_AUTH_MODE = os.getenv("AZURE_OPENAI_AUTH_MODE", "managed_identity").lower()
AZURE_OPENAI_SCOPE = "https://cognitiveservices.azure.com/.default"

SEARCH_ENDPOINT = os.getenv("AZURE_AI_SEARCH_ENDPOINT", "")
SEARCH_API_KEY = os.getenv("AZURE_AI_SEARCH_API_KEY", "")
AZURE_AI_SEARCH_AUTH_MODE = os.getenv("AZURE_AI_SEARCH_AUTH_MODE", "managed_identity").lower()
SEARCH_INDEX_NAME = os.getenv("AZURE_AI_SEARCH_INDEX_NAME", "purview-items")
SEARCH_VECTOR_FIELD = os.getenv("AZURE_AI_SEARCH_VECTOR_FIELD", "contentVector")
SEARCH_TEXT_FIELD = os.getenv("AZURE_AI_SEARCH_TEXT_FIELD", "content")
SEARCH_TITLE_FIELD = os.getenv("AZURE_AI_SEARCH_TITLE_FIELD", "title")
SEARCH_URL_FIELD = os.getenv("AZURE_AI_SEARCH_URL_FIELD", "url")

CACHE_FILE = ".token_cache.json"
SCOPES = ["https://graph.microsoft.com/ExternalItem.Read.All"]

_azure_credential: Optional[DefaultAzureCredential] = None


def get_azure_credential() -> DefaultAzureCredential:
    global _azure_credential
    if _azure_credential is None:
        _azure_credential = DefaultAzureCredential()
    return _azure_credential


def get_search_credential():
    if AZURE_AI_SEARCH_AUTH_MODE == "key":
        if not SEARCH_API_KEY:
            raise ValueError("AZURE_AI_SEARCH_AUTH_MODE is 'key' but AZURE_AI_SEARCH_API_KEY is not set.")
        return AzureKeyCredential(SEARCH_API_KEY)
    return get_azure_credential()


def get_openai_headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if AZURE_OPENAI_AUTH_MODE == "key":
        if not AZURE_OPENAI_API_KEY:
            raise ValueError("AZURE_OPENAI_AUTH_MODE is 'key' but AZURE_OPENAI_API_KEY is not set.")
        headers["api-key"] = AZURE_OPENAI_API_KEY
        return headers

    token = get_azure_credential().get_token(AZURE_OPENAI_SCOPE).token
    headers["Authorization"] = f"Bearer {token}"
    return headers

# ---------------------------------------------------------------------
# Helper: Ensure Search Index Exists
# ---------------------------------------------------------------------
def ensure_index_exists():
    index_client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=get_search_credential())
    try:
        existing = index_client.get_index(SEARCH_INDEX_NAME)
        print(f"Index '{SEARCH_INDEX_NAME}' already exists.")
        return
    except Exception:
        print(f"Creating index '{SEARCH_INDEX_NAME}' from scratch...")

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchField(name="title", type=SearchFieldDataType.String, searchable=True),
        SearchField(name="content", type=SearchFieldDataType.String, searchable=True),
        SearchField(name="userDescription", type=SearchFieldDataType.String, searchable=True),
        SearchField(name="tags", type=SearchFieldDataType.String, searchable=True),
        SearchField(name="classifications", type=SearchFieldDataType.String, searchable=True),
        SearchField(name="qualifiedName", type=SearchFieldDataType.String, searchable=True),
        SearchField(
            name="contentVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=3072,
            vector_search_profile_name="default-vector-profile",
        ),
    ]
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(name="default-hnsw", kind=VectorSearchAlgorithmKind.HNSW, metric="cosine")
        ],
        profiles=[VectorSearchProfile(name="default-vector-profile", algorithm_configuration_name="default-hnsw")],
    )
    semantic_config = SemanticConfiguration(
        name="default-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            content_fields=[SemanticField(field_name="content"), SemanticField(field_name="userDescription")],
        ),
    )
    index = SearchIndex(name=SEARCH_INDEX_NAME, fields=fields, vector_search=vector_search, semantic_configurations=[semantic_config])
    index_client.create_or_update_index(index)
    print(f"Index '{SEARCH_INDEX_NAME}' created successfully.")

# ---------------------------------------------------------------------
# Microsoft Authentication (MSAL)
# ---------------------------------------------------------------------
def get_token():
    cache = msal.SerializableTokenCache()
    app = msal.PublicClientApplication(CLIENT_ID, authority=f"https://login.microsoftonline.com/{TENANT_ID}", token_cache=cache)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            return result
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise ValueError("Device code flow failed.")
    print(f"Authenticate at {flow['verification_uri']} and enter code {flow['user_code']}")
    return app.acquire_token_by_device_flow(flow)

# ---------------------------------------------------------------------
# Azure OpenAI Embeddings
# ---------------------------------------------------------------------
def get_embedding(text: str) -> List[float]:
    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_EMBEDDING_DEPLOYMENT}/embeddings?api-version={AZURE_OPENAI_API_VERSION}"
    headers = get_openai_headers()
    body = {"input": text}
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]

# ---------------------------------------------------------------------
# Microsoft Graph Connector Query
# ---------------------------------------------------------------------
def graph_search(query: str, token: str, size: int = 10) -> List[Dict[str, Any]]:
    url = "https://graph.microsoft.com/v1.0/search/query"
    payload = {
        "requests": [{"entityTypes": ["externalItem"], "contentSources": [f"/external/connections/{GRAPH_CONNECTION_ID}"], "query": {"queryString": query}, "size": size}]
    }
    resp = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=payload)
    resp.raise_for_status()
    data = resp.json()
    hits = data.get("value", [{}])[0].get("hitsContainers", [{}])[0].get("hits", [])
    return [h.get("resource", {}).get("properties", {}) for h in hits]

# ---------------------------------------------------------------------
# Index Graph Data
# ---------------------------------------------------------------------
def index_graph_connector_items(token: str, size: int = 20):
    ensure_index_exists()
    items = graph_search("*", token, size=size)
    client = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=SEARCH_INDEX_NAME, credential=get_search_credential())
    docs = []
    for item in items:
        title = item.get("title") or "Untitled"
        desc = item.get("description") or ""
        content = f"{title}\n{desc}"
        emb = get_embedding(content)
        docs.append({"id": title, "title": title, "content": content, "userDescription": desc, "contentVector": emb})
    client.upload_documents(docs)
    print(f"Indexed {len(docs)} items.")

# ---------------------------------------------------------------------
# Hybrid Search
# ---------------------------------------------------------------------
def hybrid_search(query: str, top: int = 2):
    ensure_index_exists()
    client = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=SEARCH_INDEX_NAME, credential=get_search_credential())
    vector = get_embedding(query)
    vq = VectorizedQuery(vector=vector, k_nearest_neighbors=top, fields=SEARCH_VECTOR_FIELD)
    results = client.search(search_text=query, vector_queries=[vq], top=top)
    return [{"title": r.get("title"), "content": r.get("content")} for r in results]

# ---------------------------------------------------------------------
# Deep Reasoning Analysis
# ---------------------------------------------------------------------
def deep_reasoning_analysis(query: str, search_results: List[Dict[str, Any]]) -> str:
    if not search_results:
        return "No data available for reasoning."
    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/gpt-4o-mini/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"
    headers = get_openai_headers()
    context = "\n\n".join([f"Title: {r['title']}\nContent: {r['content']}" for r in search_results])
    prompt = f"Analyze the query '{query}' and the context below to provide insights, sensitivity, and actions:\n{context}"
    body = {"messages": [{"role": "system", "content": "You are an AI data governance reasoning assistant."}, {"role": "user", "content": prompt}], "temperature": 0.3}
    resp = requests.post(url, headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

# ---------------------------------------------------------------------
# Knowledge Graph Reasoning
# ---------------------------------------------------------------------
def infer_knowledge_graph_relationships(search_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    if not search_results:
        return []
    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/gpt-4o-mini/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"
    headers = get_openai_headers()
    context = "\n".join([f"Title: {r['title']}\nContent: {r['content']}" for r in search_results])
    prompt =f"Find logical relationships among data assets in this context. Return JSON edges with 'source', 'relation', 'target'. Context:\n{context}"

    # import pandas as pd
    # df = pd.DataFrame(resp['choices'][0]['message']['content'])
    # st.dataframe(df)

    body = {"messages": [{"role": "system", "content": "You are an AI building semantic knowledge graphs."}, {"role": "user", "content": prompt}]}
    resp = requests.post(url, headers=headers, json=body)
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    try:
        return json.loads(text)
    except Exception:
        return [{"raw_output": text}]


