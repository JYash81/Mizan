"""Safe administrative cleanup script for synthetic E2E test data.

Defaults to --dry-run. Pass --commit to actually remove synthetic records.
Never removes or modifies non-synthetic organizations or real customer accounts.
"""

import argparse
import os
import sys

# Ensure backend root is on Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import engine
from sqlalchemy import text


def main():
    parser = argparse.ArgumentParser(description="Prune synthetic test records from database.")
    parser.add_argument("--commit", action="store_true", help="Actually execute the deletion.")
    args = parser.parse_args()

    print("=" * 60)
    print("MIZAN SYNTHETIC TEST DATA CLEANUP AUDIT")
    print("=" * 60)
    print(f"Mode: {'COMMIT (DESTRUCTIVE TO SYNTHETIC RECORDS)' if args.commit else 'DRY RUN (READ ONLY)'}")

    with engine.connect() as conn:
        # 1. Identify synthetic users
        synthetic_users = conn.execute(
            text("SELECT id, email, full_name, created_at FROM users WHERE email LIKE 'e2e_tester_%'")
        ).fetchall()
        print(f"\nSynthetic E2E Users ({len(synthetic_users)} found):")
        for u in synthetic_users:
            print(f" - [{u[0]}] {u[1]} ({u[2]})")

        # 2. Identify synthetic organizations
        synthetic_orgs = conn.execute(
            text("SELECT id, name, slug, created_at FROM organizations WHERE name LIKE 'Test Org %' AND name != 'hennt'")
        ).fetchall()
        print(f"\nSynthetic E2E Organizations ({len(synthetic_orgs)} found):")
        for o in synthetic_orgs:
            print(f" - [{o[0]}] {o[1]} ({o[2]})")

        if not args.commit:
            print("\n[DRY RUN COMPLETE] Zero database records were modified.")
            print("To delete the synthetic records identified above, re-run with: python cleanup_synthetic_e2e_data.py --commit")
            return

        # 3. Perform scoped deletion
        trans = conn.begin()
        try:
            # Delete synthetic organizations (cascades workspaces, datasets, runs)
            if synthetic_orgs:
                org_ids = [o[0] for o in synthetic_orgs]
                # Cascading delete
                for oid in org_ids:
                    # Clean memberships and workspaces
                    ws_list = conn.execute(text("SELECT id FROM workspaces WHERE organization_id = :oid"), {"oid": oid}).fetchall()
                    for ws in ws_list:
                        wid = ws[0]
                        conn.execute(text("DELETE FROM workspace_memberships WHERE workspace_id = :wid"), {"wid": wid})
                        conn.execute(text("DELETE FROM datasets WHERE workspace_id = :wid"), {"wid": wid})
                        conn.execute(text("DELETE FROM evaluation_suites WHERE workspace_id = :wid"), {"wid": wid})
                        conn.execute(text("DELETE FROM experiments WHERE workspace_id = :wid"), {"wid": wid})
                        conn.execute(text("DELETE FROM workspaces WHERE id = :wid"), {"wid": wid})
                    conn.execute(text("DELETE FROM organization_memberships WHERE organization_id = :oid"), {"oid": oid})
                    conn.execute(text("DELETE FROM organizations WHERE id = :oid"), {"oid": oid})
                print(f"Successfully pruned {len(synthetic_orgs)} synthetic organizations and their child records.")

            # Delete synthetic users
            if synthetic_users:
                for u in synthetic_users:
                    uid = u[0]
                    conn.execute(text("DELETE FROM auth_tokens WHERE user_id = :uid"), {"uid": uid})
                    conn.execute(text("DELETE FROM auth_sessions WHERE user_id = :uid"), {"uid": uid})
                    conn.execute(text("DELETE FROM audit_events WHERE actor_id = :uid"), {"uid": uid})
                    conn.execute(text("DELETE FROM organization_memberships WHERE user_id = :uid"), {"uid": uid})
                    conn.execute(text("DELETE FROM workspace_memberships WHERE user_id = :uid"), {"uid": uid})
                    conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": uid})
                print(f"Successfully pruned {len(synthetic_users)} synthetic user records.")

            trans.commit()
            print("\n[COMMIT SUCCESSFUL] All synthetic test data has been pruned safely.")
        except Exception as e:
            trans.rollback()
            print(f"\n[ERROR] Transaction failed, rolled back cleanly: {e}")
            raise


if __name__ == "__main__":
    main()
