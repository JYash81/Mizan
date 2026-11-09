"""REST API endpoints for the Customer Runtime (Inference, Probes, Slots, Golden Tests)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.runtime.customer_runtime_engine import (
    execute_chat_completion,
    execute_rag_query,
    get_health_diagnostics,
    get_live_probe,
    get_ready_probe,
    list_runtime_models,
)
from app.modules.runtime.exceptions import (
    GoldenTestFailedError,
    InferenceEngineError,
    InvalidSlotStateTransitionError,
    PackageVerificationError,
    SlotActivationBlockedError,
    SlotNotFoundError,
)
from app.modules.runtime.golden_test_runner import execute_golden_tests
from app.modules.runtime.schemas import (
    GoldenTestRunRead,
    RuntimeActivationEventRead,
    RuntimeChatCompletionRequest,
    RuntimeChatCompletionResponse,
    RuntimeHealthResponse,
    RuntimeLiveResponse,
    RuntimeModelsResponse,
    RuntimeRagQueryRequest,
    RuntimeRagQueryResponse,
    RuntimeReadyResponse,
    RuntimeSlotRead,
    SlotActivateRequest,
    SlotRollbackRequest,
    SlotStageRequest,
)
from app.modules.runtime.slot_manager_service import (
    get_application_slots,
    list_activation_events,
    promote_slot,
    rollback_slot,
    stage_candidate_to_slot,
)

router = APIRouter(prefix="/runtime", tags=["Customer Runtime"])


# =========================================================================
# 1. Health & Readiness Probes
# =========================================================================


@router.get("/live", response_model=RuntimeLiveResponse)
def live_probe_endpoint() -> RuntimeLiveResponse:
    """Liveness probe: returns 200 OK when process is running and event loop is alive."""
    return get_live_probe()


@router.get("/ready", response_model=RuntimeReadyResponse)
def ready_probe_endpoint(
    app_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> RuntimeReadyResponse:
    """Readiness probe: returns 200 with 'ready' or 'unready' based on active slot state."""
    probe = get_ready_probe(db, app_id)
    if probe.status != "ready":
        # We return the response with 503 SERVICE UNAVAILABLE or 200 with status="unready"
        # Standard k8s readiness probe checks HTTP status:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=probe.model_dump(mode="json"),
        )
    return probe


@router.get("/health", response_model=RuntimeHealthResponse)
def health_endpoint(
    app_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> RuntimeHealthResponse:
    """Diagnostic health summary of runtime engine, memory usage, and slots."""
    return get_health_diagnostics(db, app_id)


# =========================================================================
# 2. Local Inference & RAG API
# =========================================================================


@router.get("/v1/models", response_model=RuntimeModelsResponse)
def list_models_endpoint(
    app_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> RuntimeModelsResponse:
    """OpenAI-compatible models catalog endpoint."""
    return list_runtime_models(db, app_id)


@router.post("/v1/chat/completions", response_model=RuntimeChatCompletionResponse)
def chat_completions_endpoint(
    payload: RuntimeChatCompletionRequest,
    app_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> RuntimeChatCompletionResponse:
    """Execute local offline chat completion via active runtime slot."""
    try:
        return execute_chat_completion(db=db, payload=payload, runtime_app_id=app_id)
    except SlotActivationBlockedError as err:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(err)) from err
    except InferenceEngineError as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)) from err


@router.post("/v1/rag/query", response_model=RuntimeRagQueryResponse)
def rag_query_endpoint(
    payload: RuntimeRagQueryRequest,
    app_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> RuntimeRagQueryResponse:
    """Execute local RAG retrieval and synthesis with citations."""
    try:
        return execute_rag_query(db=db, payload=payload, runtime_app_id=app_id)
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)) from err


# =========================================================================
# 3. Blue/Green Slots & Golden Tests Management
# =========================================================================


@router.get("/applications/{app_id}/slots", response_model=list[RuntimeSlotRead])
def get_slots_endpoint(
    app_id: str,
    db: Session = Depends(get_db),
) -> list[RuntimeSlotRead]:
    """Get status of Blue and Green slots for an application."""
    return get_application_slots(db, app_id)


@router.post("/applications/{app_id}/slots/stage", response_model=RuntimeSlotRead)
def stage_slot_endpoint(
    app_id: str,
    payload: SlotStageRequest,
    db: Session = Depends(get_db),
) -> RuntimeSlotRead:
    """Stage a candidate package into the inactive blue/green slot."""
    try:
        return stage_candidate_to_slot(db, app_id, payload)
    except SlotNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except PackageVerificationError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.post("/slots/{slot_id}/golden-tests/run", response_model=GoldenTestRunRead)
def run_golden_tests_endpoint(
    slot_id: str,
    suite_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> GoldenTestRunRead:
    """Run golden test suite against candidate slot before activation."""
    try:
        return execute_golden_tests(db=db, slot_id=slot_id, suite_id=suite_id)
    except SlotNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except GoldenTestFailedError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.post("/applications/{app_id}/slots/activate", response_model=RuntimeSlotRead)
def activate_slot_endpoint(
    app_id: str,
    payload: SlotActivateRequest,
    actor_id: str = Query("operator"),
    db: Session = Depends(get_db),
) -> RuntimeSlotRead:
    """Promote candidate slot to active traffic serving. Gated by Golden Tests."""
    try:
        return promote_slot(db=db, runtime_app_id=app_id, payload=payload, actor_id=actor_id)
    except SlotNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except SlotActivationBlockedError as err:
        raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=str(err)) from err


@router.post("/applications/{app_id}/slots/rollback", response_model=RuntimeSlotRead)
def rollback_slot_endpoint(
    app_id: str,
    payload: SlotRollbackRequest,
    actor_id: str = Query("operator"),
    db: Session = Depends(get_db),
) -> RuntimeSlotRead:
    """Manually rollback active traffic serving to alternate slot."""
    try:
        return rollback_slot(db=db, runtime_app_id=app_id, payload=payload, actor_id=actor_id)
    except SlotNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except InvalidSlotStateTransitionError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.get("/applications/{app_id}/activations", response_model=list[RuntimeActivationEventRead])
def get_activation_events_endpoint(
    app_id: str,
    db: Session = Depends(get_db),
) -> list[RuntimeActivationEventRead]:
    """Retrieve immutable audit log of slot activation and rollback events."""
    return list_activation_events(db, app_id)
