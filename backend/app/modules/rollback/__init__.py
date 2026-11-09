"""Rollback module package."""

from app.modules.rollback.regression_detector import detect_post_activation_regression
from app.modules.rollback.rollback_eligibility import check_rollback_eligibility
from app.modules.rollback.rollback_executor import execute_rollback, list_rollback_history
from app.modules.rollback.rollback_policy_service import (
    get_or_create_rollback_policy,
    list_rollback_policies,
    update_rollback_policy,
)

__all__ = [
    "check_rollback_eligibility",
    "detect_post_activation_regression",
    "execute_rollback",
    "get_or_create_rollback_policy",
    "list_rollback_history",
    "list_rollback_policies",
    "update_rollback_policy",
]
