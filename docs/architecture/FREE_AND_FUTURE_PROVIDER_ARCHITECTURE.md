# Mizan AI Provider Abstraction and RAG Foundation Architecture

**Milestone:** 5 — AI Providers & RAG Foundation (Free-Only Infrastructure)  
**Authoritative Baseline:** Mizan High-Level Design (`docs/reference/mizan_hld.png`)  
**Status:** ACTIVE  
**Updated:** 2026-11-08  

---

## 1. Architectural Mission

Milestone 5 establishes Mizan's provider-independent AI core. It connects approved masked datasets from **Gate 1** into an efficient, sovereign, cost-free **Retrieval-Augmented Generation (RAG)** pipeline.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       GATE 1 APPROVED MASKED DATASET                         │
│                    StorageBucket.MASKED_DATASETS                            │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             DOCUMENT CHUNKER                                │
│  - Bounded Sliding Window (Character/Token Bounds)                          │
│  - Source Span Offset Tracing (Links Chunks to Document & Version)          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FASTEMBED EMBEDDING PROVIDER (LOCAL CPU)                 │
│  - Model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2       │
│  - ONNX Runtime (384 Dimensions, Multilingual English + Arabic)              │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   QDRANT LOCAL VECTOR STORE (SINGLE PROCESS)                │
│  - Persistent Local Path: storage/development/qdrant                        │
│  - Strict Payload Filtering: workspace_id, dataset_version_id               │
│  - Zero External Daemons / Zero Docker                                      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     RETRIEVAL & CITATION CONTEXT ENGINE                     │
│  - Semantic Search with Top-K and Score Thresholding                        │
│  - Verifiable Source Attribution [Doc: ..., Chunk: ...]                     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI PROVIDER ABSTRACTION                           │
│  ├─ MockProvider (Default: deterministic, 100% free, test harness)          │
│  ├─ OllamaProvider (Optional local CPU/GPU daemon via REST API)             │
│  ├─ GeminiFreeProvider (Optional experimental free-tier via REST API)       │
│  └─ vLLMProvider (Future high-scale GPU server stub)                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Interfaces

### A. `EmbeddingProvider`
```python
class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for input strings."""

    @abstractmethod
    def get_dimension(self) -> int:
        """Return embedding vector dimensions (e.g. 384)."""

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """Return model metadata, license, and version."""
```

### B. `VectorStoreProvider`
```python
class VectorStoreProvider(ABC):
    @abstractmethod
    def create_collection(self, collection_name: str, dimension: int) -> None:
        """Initialize collection with specified dimension and Cosine metric."""

    @abstractmethod
    def upsert_chunks(self, collection_name: str, chunks: list[VectorChunk]) -> None:
        """Insert or update embedded chunks with metadata payload."""

    @abstractmethod
    def search_chunks(
        self,
        collection_name: str,
        query_vector: list[float],
        workspace_id: str,
        dataset_version_id: str,
        top_k: int = 5,
        score_threshold: float = 0.5,
    ) -> list[ScoredChunk]:
        """Query vectors with mandatory tenant and version isolation filters."""

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        """Safely drop collection."""
```

### C. `LLMProvider`
```python
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str | None = None, **kwargs) -> LLMResponse:
        """Generate synchronous completion."""

    @abstractmethod
    def check_availability(self) -> ProviderStatus:
        """Check provider operational status and free quota availability."""
```

---

## 3. Privacy, Free Cost & Gate 1 Invariant Enforcement

1. **Gate 1 Prerequisite:** The RAG indexing pipeline strictly invokes `require_gate1_approval(db, workspace_id, dataset_version_id)`. Unapproved raw datasets are blocked with `HTTP 403 Forbidden`.
2. **Cost Gate:** Prior to any inference or retrieval request, `CostPolicy.validate_provider(provider_type)` verifies that `ALLOW_PAID_PROVIDERS == False` and rejects any billable operations.
3. **External Sharing Gate:** If an external provider (Gemini free tier) is called, it verifies that input text is marked non-confidential or has been fully masked under an approved Gate 1 run.
