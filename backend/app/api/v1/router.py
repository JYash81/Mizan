"""Version 1 API router registration."""

from fastapi import APIRouter

from app.api.v1.endpoints.app_zoo import router as app_zoo_router
from app.api.v1.endpoints.artifact_registry import router as artifact_registry_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.cost import router as cost_router
from app.api.v1.endpoints.customer_runtime import router as customer_runtime_router
from app.api.v1.endpoints.datasets import router as datasets_router
from app.api.v1.endpoints.documents import router as documents_router
from app.api.v1.endpoints.evaluation import router as evaluation_router
from app.api.v1.endpoints.experiments import router as experiments_router
from app.api.v1.endpoints.gate1 import router as gate1_router
from app.api.v1.endpoints.gate2 import router as gate2_router
from app.api.v1.endpoints.gate3 import router as gate3_router
from app.api.v1.endpoints.hardware import router as hardware_router
from app.api.v1.endpoints.invitations import router as inv_router
from app.api.v1.endpoints.masking import router as masking_router
from app.api.v1.endpoints.model_building import router as model_building_router
from app.api.v1.endpoints.model_zoo import router as model_zoo_router
from app.api.v1.endpoints.operations import router as operations_router
from app.api.v1.endpoints.organizations import router as org_router
from app.api.v1.endpoints.rag import router as rag_router
from app.api.v1.endpoints.recommendations import router as recommendations_router
from app.api.v1.endpoints.sentinel import router as sentinel_router
from app.api.v1.endpoints.site_agent import router as site_agent_router
from app.api.v1.endpoints.sites import router as sites_router
from app.api.v1.endpoints.system import router as system_router
from app.api.v1.endpoints.workspaces import router as ws_router

router = APIRouter(prefix="/api/v1")
router.include_router(system_router)
router.include_router(auth_router)
router.include_router(org_router)
router.include_router(ws_router)
router.include_router(inv_router)
router.include_router(datasets_router)
router.include_router(documents_router)
router.include_router(masking_router)
router.include_router(gate1_router)
router.include_router(gate2_router)
router.include_router(hardware_router)
router.include_router(cost_router)
router.include_router(rag_router)
router.include_router(evaluation_router)
router.include_router(experiments_router)
router.include_router(recommendations_router)
router.include_router(model_building_router)
router.include_router(artifact_registry_router)
router.include_router(gate3_router)
router.include_router(model_zoo_router)
router.include_router(app_zoo_router)
router.include_router(sites_router)
router.include_router(site_agent_router)
router.include_router(customer_runtime_router)
router.include_router(operations_router)
router.include_router(sentinel_router)
