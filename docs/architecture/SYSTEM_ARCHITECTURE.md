# System architecture

## HLD interpretation

Mizan has a control plane that governs business requests, approvals, metadata, and published artifacts; an isolated experimentation plane; and a customer runtime that installs approved outputs. The three approval gates ensure masking, spend, and release decisions are made by people rather than the AI agent.

## Milestone 1 implementation

React provides the local control-plane shell, routing, design system, and honest empty states. FastAPI provides versioned system APIs, configuration, CORS, structured errors, and database readiness. SQLAlchemy/Alembic establish the migration boundary.

## Future boundaries

Authentication, organizations, datasets, approvals, provider adapters, RAG, experiments, recommendations, artifacts, the model zoo, and customer runtime are separate modules to be added behind the API. Compute providers must remain replaceable; raw files, masked packages, artifacts, and telemetry must remain segregated.
