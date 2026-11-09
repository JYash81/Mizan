"""RAG and AI Provider REST API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.identity import User
from app.models.organization import OrganizationMembership, Workspace, WorkspaceRole
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import require_ws_permission
from app.modules.authorization.permissions import WorkspacePermission
from app.modules.rag.cost_policy import CostPolicyViolationError
from app.modules.rag.embeddings.fastembed_provider import FastEmbedProvider
from app.modules.rag.evaluation.eval_service import evaluate_rag_execution
from app.modules.rag.pipeline.rag_service import (
    index_approved_dataset_version,
    query_rag,
)
from app.modules.rag.privacy_policy import PrivacyPolicyViolationError
from app.modules.rag.providers.registry import get_llm_provider, list_registered_providers
from app.modules.rag.schemas import (
    ProviderInfoResponse,
    RAGEvalRequest,
    RAGEvalResponse,
    RAGIndexRequest,
    RAGIndexResponse,
    RAGQueryRequest,
    RAGQueryResponse,
)
from app.modules.rag.vector_store.qdrant_local import QdrantLocalVectorStore
from app.modules.storage import get_storage_provider

router = APIRouter(tags=["AI Providers & RAG Foundation"])

# Singleton local vector store instance
_vector_store: QdrantLocalVectorStore | None = None
_embedding_provider: FastEmbedProvider | None = None


def get_vector_store() -> QdrantLocalVectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = QdrantLocalVectorStore()
    return _vector_store


def get_embedding_provider() -> FastEmbedProvider:
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = FastEmbedProvider()
    return _embedding_provider


@router.get(
    "/workspaces/{workspace_id}/rag/providers",
    status_code=status.HTTP_200_OK,
)
def list_providers(
    workspace_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
) -> list[ProviderInfoResponse]:
    """List all registered free AI providers and their operational status."""
    statuses = list_registered_providers()
    return [
        ProviderInfoResponse(
            provider_name=s.provider_name,
            is_available=s.is_available,
            is_free=s.is_free,
            status_message=s.status_message,
            cost_per_million_input_cents=s.cost_per_million_input_cents,
            cost_per_million_output_cents=s.cost_per_million_output_cents,
        )
        for s in statuses
    ]


@router.post(
    "/workspaces/{workspace_id}/rag/index",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def index_dataset(
    workspace_id: str,
    payload: RAGIndexRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_CREATE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> RAGIndexResponse:
    """Index an approved masked dataset version into the workspace vector store.

    INVARIANT: Fails closed with HTTP 403 if Gate 1 approval is missing or unverified.
    """
    ws, _, _ = context
    storage = get_storage_provider()
    v_store = get_vector_store()
    embedder = get_embedding_provider()

    try:
        summary = index_approved_dataset_version(
            db=db,
            workspace_id=ws.id,
            dataset_version_id=payload.dataset_version_id,
            vector_store=v_store,
            embedding_provider=embedder,
            storage=storage,
            chunk_size_chars=payload.chunk_size_chars,
            chunk_overlap_chars=payload.chunk_overlap_chars,
        )
        return RAGIndexResponse(**summary)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/workspaces/{workspace_id}/rag/query",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_csrf)],
)
def execute_rag_query(
    workspace_id: str,
    payload: RAGQueryRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_CREATE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> RAGQueryResponse:
    """Execute RAG question-answering with citation attribution under cost policy enforcement."""
    ws, _, _ = context
    v_store = get_vector_store()
    embedder = get_embedding_provider()

    try:
        llm = get_llm_provider(payload.provider)
    except CostPolicyViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cost policy violation: {exc}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    try:
        result = query_rag(
            workspace_id=ws.id,
            query=payload.query,
            dataset_version_id=payload.dataset_version_id,
            vector_store=v_store,
            embedding_provider=embedder,
            llm_provider=llm,
            top_k=payload.top_k,
            score_threshold=payload.score_threshold,
        )
        return RAGQueryResponse(**result)
    except (CostPolicyViolationError, PrivacyPolicyViolationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/workspaces/{workspace_id}/rag/evaluate",
    status_code=status.HTTP_200_OK,
)
def evaluate_rag(
    workspace_id: str,
    payload: RAGEvalRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
) -> RAGEvalResponse:
    """Evaluate retrieval recall, context relevance, faithfulness, and citation completeness."""
    report = evaluate_rag_execution(
        query=payload.query,
        answer=payload.answer,
        retrieved_chunks=payload.retrieved_chunks,
        expected_keywords=payload.expected_keywords,
    )
    return RAGEvalResponse(
        query=report.query,
        retrieval_recall=report.retrieval_recall,
        context_relevance=report.context_relevance,
        faithfulness=report.faithfulness,
        citation_completeness=report.citation_completeness,
        overall_score=report.overall_score,
        citations_count=report.citations_count,
        retrieved_chunks_count=report.retrieved_chunks_count,
        details=report.details,
    )
