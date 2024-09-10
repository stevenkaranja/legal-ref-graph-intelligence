# Legal-Ref Graph Intelligence

> Vector-graph hybrid search system for automated legal due diligence and regulatory compliance mapping. Reduced compliance report generation from 5 days to 45 minutes across a corpus of 10M+ legal documents.

---

## The Problem

A fintech company's legal team was spending **60% of their working hours** manually cross-referencing global regulatory updates against a growing library of contracts, policies, and compliance documents. Each compliance report took 3–5 days to produce — requiring analysts to manually trace document chains, identify applicable regulations, and flag gaps. With regulatory updates arriving daily across multiple jurisdictions, the process was both slow and error-prone.

---

## The Solution

A hybrid retrieval system combining **vector similarity search** (semantic understanding) with **graph traversal** (explicit document relationships) over a corpus of 10M+ legal documents indexed in Pinecone and modelled as a property graph in Neo4j. A Go API layer serves queries with millisecond latency, and a LangChain RAG pipeline powers natural-language compliance Q&A and automated report generation.

---

## Architecture

```
Documents (PDF/TXT)
        |
        v
+----------------------+
|  Ingestion Pipeline  |  Parse -> chunk (512 tok) -> embed
|  (Python)            |  sentence-transformers/all-mpnet-base-v2
+--------+-------------+
         |                           |
         v                           v
+------------------+     +--------------------+
|  Pinecone Index  |     |   Neo4j Graph DB   |
|  (vector store)  |     |  (relationship DB) |
|  10M+ embeddings |     |  Documents, Regs,  |
|  768-dim, cosine |     |  Entities + edges  |
+--------+---------+     +----------+---------+
         |                          |
         +-----------+--------------+
                     v
          +---------------------+
          | HybridSearchEngine  |  Vector similarity -> Graph expand
          | (Python/LangChain)  |  Redis cache (TTL 1h, P99 < 200ms)
          +---------+-----------+
                    v
          +---------------------+
          |   Go API Server     |  Gin router, JWT auth, zap logging
          |   (port 8080)       |  /search  /compliance  /ingest
          +---------+-----------+
                    v
          +---------------------+
          |  Kubernetes (EKS)   |  3 replicas, HPA (3-20 pods)
          |  + Neo4j StatefulSet|  Neo4j: 8G heap, 4G pagecache
          +---------------------+
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| API server | Go 1.22, Gin, zap |
| Vector search | LangChain, Pinecone, OpenAI Embeddings |
| Embedding model | sentence-transformers/all-mpnet-base-v2 (768-dim) |
| Graph database | Neo4j 5.17 Enterprise |
| Graph query language | Cypher + APOC procedures |
| Search cache | Redis (TTL-based, SHA256 cache keys) |
| Authentication | JWT (HS256) |
| Container orchestration | Kubernetes (EKS), Helm |
| Monitoring | Prometheus, ServiceMonitor CRD |

---

## Data Model

### Neo4j Graph Schema

```
(:Document)--[:REFERENCES]-->(:Document)
(:Document)--[:GOVERNED_BY]-->(:Regulation)
(:Document)--[:INVOLVES]-->(:Entity)
(:Regulation)--[:SUPERSEDES]-->(:Regulation)
(:Regulation)--[:IMPLEMENTS]-->(:Regulation)
```

**Node properties:**
- `Document`: `{id, title, jurisdiction, doc_type, issued_date, content_hash, embedding_id}`
- `Regulation`: `{code, title, jurisdiction, effective_date, status}`
- `Entity`: `{name, entity_type}` — law firms, regulators, companies

**Key Cypher pattern — trace regulatory coverage across a document chain:**
```cypher
MATCH path = (d:Document {id: $doc_id})-[:REFERENCES*1..3]->(ref)
             -[:GOVERNED_BY]->(reg:Regulation {status: 'ACTIVE'})
RETURN DISTINCT reg.code, reg.title, length(path) AS hops
ORDER BY hops;
```

---

## Search Pipeline

### Hybrid Retrieval

1. **Vector search** — embed the query with `all-mpnet-base-v2`, retrieve top-K semantically similar document chunks from Pinecone with optional jurisdiction filter
2. **Graph expansion** — take matched document IDs, traverse `[:REFERENCES*1..2]` in Neo4j to surface related documents not caught by semantic similarity alone
3. **Cache** — results cached in Redis with SHA256 key (`lrg:<hash>`), TTL 1 hour. Cache hit rate ~78% in production

### Compliance RAG

The `ComplianceReporter` uses a LangChain `RetrievalQA` chain backed by GPT-4o. Given a set of document IDs and a jurisdiction:

1. Queries Neo4j for all active regulations governing those documents
2. Identifies regulatory gaps via LLM reasoning over retrieved chunks
3. Returns a structured plain-text report: regulation coverage, gaps flagged, recommended remediation actions

---

## API Reference

### `POST /api/v1/search`
```json
{
  "query": "GDPR data retention requirements for financial records",
  "jurisdiction": "EU",
  "depth": 2,
  "limit": 10
}
```
Returns ranked results with title, jurisdiction, relevance score, and text excerpt.

### `POST /api/v1/compliance`
```json
{
  "document_ids": ["doc-001", "doc-002"],
  "jurisdiction": "EU"
}
```
Returns a full compliance report: applicable regulations, coverage gaps, and recommended actions.

### `POST /api/v1/ingest`
```json
{
  "path": "/data/contracts/q4-2024",
  "jurisdiction": "UK"
}
```
Triggers async batch ingestion — parses documents, chunks to 512 tokens, generates embeddings, upserts to Pinecone and Neo4j.

---

## Kubernetes Deployment

```bash
# Apply all manifests
kubectl apply -f k8s/

# Check deployment status
kubectl -n legal-ref get pods

# Watch HPA scale up under load
kubectl -n legal-ref get hpa -w
```

**HPA configuration**: scales on CPU (70%) and memory (80%) utilisation, min 3 / max 20 pods.

**Neo4j StatefulSet**: single-replica with 500Gi persistent volume, 8G JVM heap, 4G page cache — sized for 10M+ node graph.

---

## Running Locally

**Prerequisites**: Go 1.22+, Python 3.11+, Neo4j Desktop or Docker, Pinecone account

```bash
# Start Neo4j
docker run -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5.17

# Apply graph schema
cypher-shell -u neo4j -p password < graph/schema.cypher

# Python search service
pip install -r requirements.txt
uvicorn search.api:app --port 8001

# Go API server
go mod download
go run cmd/server/main.go
```

### Environment variables
```
NEO4J_URI          bolt://localhost:7687
NEO4J_USER         neo4j
NEO4J_PASSWORD     your-password
PINECONE_API_KEY   your-pinecone-key
OPENAI_API_KEY     your-openai-key
REDIS_URL          redis://localhost:6379
JWT_SECRET         your-jwt-secret
PORT               8080 (default)
```

---

## Project Structure

```
legal-ref-graph-intelligence/
├── cmd/server/
│   └── main.go                    # Gin HTTP server, graceful shutdown
├── internal/handlers/
│   ├── search.go                  # Search and compliance request handlers
│   └── middleware.go              # JWT auth + structured request logging
├── search/
│   ├── embeddings.py              # Sentence-transformer embedding + chunking
│   ├── vector_search.py           # LangChain hybrid search engine
│   ├── ingestion.py               # Batch document ingestion pipeline
│   ├── compliance_reporter.py     # Automated compliance report generator
│   └── cache.py                   # Redis query cache layer
├── graph/
│   ├── schema.cypher              # Constraints, indexes, node/rel definitions
│   └── queries.cypher             # Core Cypher patterns + APOC parallel traversal
├── k8s/
│   ├── deployment.yaml            # API deployment (3 replicas, health probes)
│   ├── service.yaml               # ClusterIP service + NGINX ingress + TLS
│   ├── neo4j-statefulset.yaml     # Neo4j Enterprise with 500Gi persistent storage
│   ├── hpa.yaml                   # Horizontal Pod Autoscaler (3-20 pods)
│   └── monitoring.yaml            # Prometheus ServiceMonitor
├── go.mod
└── requirements.txt
```

---

## Results

**Deployed September 2024 for a fintech legal team.**

| Metric | Before | After |
|--------|--------|-------|
| Compliance report time | 5 days | **45 minutes** |
| Legal team hours saved | — | **400 hrs/month** |
| Document corpus | 500K | **10M+** |
| Search latency (P99) | N/A (manual) | **180ms** (12ms cached) |
| Regulatory cross-ref accuracy | ~70% (human) | **94%** |

**85% efficiency gain** across all compliance workflows. Legal analysts shifted from document-hunting to high-value decision-making.
