# Repository audit

Audit date: 2026-11-08.

## Initial state

The repository directory was empty: no Git repository, source code, dependency manifests, configuration, tests, or documentation existed. The supplied HLD was available outside the workspace and was reviewed as the product reference.

## Technology inventory

The development machine exposes Python 3.12.10, Node.js 24.19.0, npm 11.17.0, and Git 2.56.0. No existing application dependency or database configuration was present.

## Risks and corrections

The primary risk was overbuilding the HLD as microservices or requiring compute services unavailable on an 8 GB local machine and Hostinger shared hosting. The foundation therefore uses one FastAPI modular monolith, SQLite locally, and a separate React application. AI execution, file storage, and artifact processing are deliberately deferred.

## Proposed structure

`frontend/` is the React control plane; `backend/` owns API and relational metadata; `ml-lab/` holds future manual research assets; `storage/development/` is local-only and ignored; `docs/` contains durable design decisions.
