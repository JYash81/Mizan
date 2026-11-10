"""Safe administrative cleanup module for synthetic E2E test data.

Defaults to --dry-run. Pass --commit and --confirm-delete-synthetic-data-only to execute.
Never removes or modifies non-synthetic organizations, customer workspaces, or customer accounts.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Any

from sqlalchemy import Engine, text

SYNTHETIC_USER_EMAIL_REGEX = re.compile(r"^e2e_tester_[0-9a-f]{8}@example\.com$")
SYNTHETIC_ORG_SLUG_REGEX = re.compile(r"^test-org-[0-9a-f]{8}$")
SYNTHETIC_WS_SLUG_REGEX = re.compile(r"^ws-[0-9a-f]{8}$")


def identify_synthetic_records(conn) -> dict[str, list[dict[str, Any]]]:
    """Identify strictly matched synthetic users and their owned organizations and workspaces."""
    # 1. Fetch potential candidate users
    raw_users = conn.execute(
        text("SELECT id, email, full_name, created_at FROM users WHERE email LIKE 'e2e_tester_%@example.com'")
    ).fetchall()

    synthetic_users = [
        {"id": u[0], "email": u[1], "full_name": u[2], "created_at": str(u[3])}
        for u in raw_users
        if SYNTHETIC_USER_EMAIL_REGEX.match(u[1])
    ]
    synthetic_user_ids = {u["id"] for u in synthetic_users}

    synthetic_orgs: list[dict[str, Any]] = []
    synthetic_workspaces: list[dict[str, Any]] = []

    if synthetic_user_ids:
        # 2. Fetch candidate organizations created by synthetic users
        raw_orgs = conn.execute(
            text(
                "SELECT id, name, slug, created_by, created_at FROM organizations "
                "WHERE slug LIKE 'test-org-%'"
            )
        ).fetchall()

        for o in raw_orgs:
            org_id, name, slug, created_by, created_at = o[0], o[1], o[2], o[3], o[4]
            # Must strictly match slug format AND creator must be in synthetic_user_ids
            if SYNTHETIC_ORG_SLUG_REGEX.match(slug) and created_by in synthetic_user_ids:
                synthetic_orgs.append({
                    "id": org_id,
                    "name": name,
                    "slug": slug,
                    "created_by": created_by,
                    "created_at": str(created_at),
                })

        synthetic_org_ids = {o["id"] for o in synthetic_orgs}
        if synthetic_org_ids:
            # 3. Fetch candidate workspaces belonging to synthetic organizations
            raw_ws = conn.execute(
                text("SELECT id, organization_id, name, slug, created_at FROM workspaces WHERE slug LIKE 'ws-%'")
            ).fetchall()
            for w in raw_ws:
                ws_id, org_id, name, slug, created_at = w[0], w[1], w[2], w[3], w[4]
                if org_id in synthetic_org_ids and SYNTHETIC_WS_SLUG_REGEX.match(slug):
                    synthetic_workspaces.append({
                        "id": ws_id,
                        "organization_id": org_id,
                        "name": name,
                        "slug": slug,
                        "created_at": str(created_at),
                    })

    return {
        "users": synthetic_users,
        "organizations": synthetic_orgs,
        "workspaces": synthetic_workspaces,
    }


def execute_synthetic_cleanup(
    engine: Engine,
    commit: bool = False,
    confirmed: bool = False,
) -> dict[str, Any]:
    """Execute dry-run or atomic transactional deletion of synthetic records."""
    if commit and not confirmed:
        raise ValueError(
            "Destructive deletion requires explicit confirmation. Pass confirmed=True or --confirm-delete-synthetic-data-only."
        )

    # DRY RUN (Read-Only)
    if not commit:
        with engine.connect() as conn:
            records = identify_synthetic_records(conn)
            return {
                "mode": "DRY_RUN",
                "modified": False,
                "users_count": len(records["users"]),
                "orgs_count": len(records["organizations"]),
                "workspaces_count": len(records["workspaces"]),
                "users": records["users"],
                "organizations": records["organizations"],
                "workspaces": records["workspaces"],
            }

    # COMMIT MODE (Single Atomic Transaction)
    with engine.connect() as conn:
        with conn.begin():
            records = identify_synthetic_records(conn)
            users = records["users"]
            orgs = records["organizations"]
            workspaces = records["workspaces"]

            user_ids = [u["id"] for u in users]
            org_ids = [o["id"] for o in orgs]
            ws_ids = [w["id"] for w in workspaces]

            if not user_ids and not org_ids and not ws_ids:
                return {
                    "mode": "COMMIT",
                    "modified": False,
                    "deleted_counts": {"users": 0, "orgs": 0, "workspaces": 0},
                }

            # 1. Clean workspace child records in dependency order
            for wid in ws_ids:
                conn.execute(text("DELETE FROM documents WHERE workspace_id = :wid"), {"wid": wid})
                conn.execute(text("DELETE FROM dataset_versions WHERE dataset_id IN (SELECT id FROM datasets WHERE workspace_id = :wid)"), {"wid": wid})
                conn.execute(text("DELETE FROM datasets WHERE workspace_id = :wid"), {"wid": wid})
                conn.execute(text("DELETE FROM evaluation_cases WHERE suite_id IN (SELECT id FROM evaluation_suites WHERE workspace_id = :wid)"), {"wid": wid})
                conn.execute(text("DELETE FROM evaluation_suite_versions WHERE suite_id IN (SELECT id FROM evaluation_suites WHERE workspace_id = :wid)"), {"wid": wid})
                conn.execute(text("DELETE FROM evaluation_suites WHERE workspace_id = :wid"), {"wid": wid})
                conn.execute(text("DELETE FROM experiments WHERE workspace_id = :wid"), {"wid": wid})
                conn.execute(text("DELETE FROM masking_runs WHERE workspace_id = :wid"), {"wid": wid})
                conn.execute(text("DELETE FROM masking_profiles WHERE workspace_id = :wid"), {"wid": wid})
                conn.execute(text("DELETE FROM workspace_memberships WHERE workspace_id = :wid"), {"wid": wid})
                conn.execute(text("DELETE FROM workspaces WHERE id = :wid"), {"wid": wid})

            # 2. Clean organization child records
            for oid in org_ids:
                conn.execute(text("DELETE FROM organization_memberships WHERE organization_id = :oid"), {"oid": oid})
                conn.execute(text("DELETE FROM organizations WHERE id = :oid"), {"oid": oid})

            # 3. Clean user child records and users
            for uid in user_ids:
                conn.execute(text("DELETE FROM auth_tokens WHERE user_id = :uid"), {"uid": uid})
                conn.execute(text("DELETE FROM auth_sessions WHERE user_id = :uid"), {"uid": uid})
                conn.execute(text("DELETE FROM audit_events WHERE actor_user_id = :uid"), {"uid": uid})
                conn.execute(text("DELETE FROM organization_memberships WHERE user_id = :uid"), {"uid": uid})
                conn.execute(text("DELETE FROM workspace_memberships WHERE user_id = :uid"), {"uid": uid})
                conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": uid})

            return {
                "mode": "COMMIT",
                "modified": True,
                "deleted_counts": {
                    "users": len(user_ids),
                    "orgs": len(org_ids),
                    "workspaces": len(ws_ids),
                },
                "pruned_user_ids": user_ids,
                "pruned_org_ids": org_ids,
            }


def main():
    parser = argparse.ArgumentParser(description="Prune synthetic test records from database safely.")
    parser.add_argument("--commit", action="store_true", help="Execute deletion inside transaction.")
    parser.add_argument(
        "--confirm-delete-synthetic-data-only",
        action="store_true",
        help="Required confirmation flag to prevent accidental deletion.",
    )
    args = parser.parse_args()

    # Ensure backend root is on Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app.db.session import engine

    print("=" * 60)
    print("MIZAN SYNTHETIC TEST DATA CLEANUP AUDIT")
    print("=" * 60)

    if args.commit and not args.confirm_delete_synthetic_data_only:
        print("[ERROR] Destructive execution aborted: --commit requires --confirm-delete-synthetic-data-only.")
        sys.exit(1)

    result = execute_synthetic_cleanup(
        engine=engine,
        commit=args.commit,
        confirmed=args.confirm_delete_synthetic_data_only,
    )

    if result["mode"] == "DRY_RUN":
        print(f"Mode: DRY RUN (READ ONLY)\n")
        print(f"Identified Synthetic Users ({result['users_count']}):")
        for u in result["users"]:
            print(f" - [{u['id']}] {u['email']} (Created: {u['created_at']})")
        print(f"\nIdentified Synthetic Organizations ({result['orgs_count']}):")
        for o in result["organizations"]:
            print(f" - [{o['id']}] {o['name']} (Slug: {o['slug']}, Owner: {o['created_by']})")
        print(f"\nIdentified Synthetic Workspaces ({result['workspaces_count']}):")
        for w in result["workspaces"]:
            print(f" - [{w['id']}] {w['name']} (Slug: {w['slug']})")
        print("\n[DRY RUN COMPLETE] Zero database records were modified.")
        print("To delete the synthetic records identified above, re-run with: python cleanup_synthetic_e2e_data.py --commit --confirm-delete-synthetic-data-only")
    else:
        print(f"Mode: COMMIT (ATOMIC TRANSACTION EXECUTED)\n")
        counts = result["deleted_counts"]
        print(f"Pruned {counts['users']} users, {counts['orgs']} organizations, {counts['workspaces']} workspaces.")
        print("[COMMIT SUCCESSFUL] All verified synthetic test records have been deleted.")


if __name__ == "__main__":
    main()
