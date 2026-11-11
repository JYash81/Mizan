# Mizan Product-Flow Audit — 2026-11-11

## Executive result
Production UI smoke audit completed for the authenticated Mizan workspace. Two local input-validation fixes and regression tests are now in the checkout; nothing was deployed. Frontend validation (55 tests), lint, TypeScript check, and production build passed. Targeted backend regressions passed 23/23. The full backend test run did not produce a final pytest summary and is inconclusive. This is not a full release sign-off: governed downstream flows requiring Gate approvals, existing model artifacts, or a ready customer runtime were not exercised.

## Local fixes (not deployed)
- `frontend/src/features/hardware/components/ResourceEstimatorForm.tsx`: changed the parameter input step from 100 to 10 so the 8000 default and all built-in presets (1100, 3800, 7000, 8000, 70000) are valid from min=10.
- `frontend/src/features/hardware/components/CostCentreView.tsx`: changed the duration step from 0.5 to 0.1 so the default 2-hour value is valid from min=0.1.
- `frontend/src/features/hardware/HardwarePage.test.tsx`: added tests checking browser-native validity for the default and all presets, and for the default cost duration.
- Validation: focused hardware test file 6/6 passed; full frontend suite 13 files / 55 tests passed; ESLint, TypeScript check, and Vite production build passed.
- No deployment or production write occurred as part of these fixes. `git` diff/status could not be read because Git rejected the repo under its safe-directory ownership guard; I did not change Git configuration.

## Environment and authority
- App: https://mizan.hennt.in (production; authenticated browser session)
- API: https://mizan-api-mq0i.onrender.com (production; read-only health/readiness/version probes)
- Active workspace: `hennt` / `Default Workspace`
- Authenticated user confirmed by the user as their account; the Team/Settings screens identify `yeswanthjanne86@gmail.com` as owner.
- Testing used synthetic-only content. No deletes, invitations, publishing, runtime deployments, paid compute, or third-party notifications were performed.
- One synthetic dataset and its document were created and remain in production (details below); no cleanup was performed because deletion was not authorized.

## Findings

### Confirmed regression — hardware estimator rejects its built-in sizes
The Resource Estimator prepopulates `Llama-3-8B` with `8000` million parameters and includes a “1B (e.g. TinyLlama)” preset of `1100`. Both values were rejected by browser number-input validation. The browser indicated the nearest valid values were `7910`/`8010` for 8000 and `1010`/`1110` for 1100. Using `8010` and `1110` respectively allowed the backend calculation to return results. Local source confirms `step="100"` with `min="10"` while the built-in defaults/presets include 8000 and 1100, which do not align to that step base. This is reproducible and should be fixed by aligning the step/base with the advertised preset values or changing the preset/default values.

### Confirmed validation mismatch — cost estimator default duration
The Workload Cost Estimator initializes to 2.0 hours but declares `min="0.1"` and `step="0.5"`. Under native HTML number-input stepping, 2.0 is not a valid step from 0.1; the valid sequence is 0.1, 0.6, 1.1, 1.6, 2.1, etc. Local source confirms the default/step mismatch. While attempting to edit the number field through the browser, the field ended up at an invalid `0.12` value and the browser showed its validation prompt; I did not complete a clean direct check of the untouched 2.0 default. I did not submit a cloud estimate or initiate any billable operation. The local cost estimate was not completed due this UI/validation issue.

### Passed / observed
- Public website loaded with the expected marketing and account entry points.
- API `GET /api/v1/health`: `ok`; `GET /api/v1/ready`: `ready`, database connected; `GET /api/v1/version`: production `0.1.0`.
- Production API `/docs` and `/openapi.json` returned `NOT_FOUND`.
- Authenticated app shell and major module routes loaded: Overview, Team, Workspaces, Datasets, Gate 1 approvals, Evaluation, Experiments, RAG, Hardware & Cost, Recommendations, Model Building, Artifact Registry, Model Zoo, App Zoo, Customer Sites, Customer Runtime, Operations Centre, Settings.
- Team page settled from a transient loading/empty state to one active owner member and zero invitations; rechecked after navigation. Workspaces showed one active Default Workspace.
- Hardware profiles listed four reference options; cross-hardware comparison returned cards/results for all four hardware profiles.
- Local Q4 resource estimates completed for an 8B model and a 1.1B TinyLlama after entering the nearest accepted step values. The 8B model was correctly marked not feasible on the local 8 GB profile; TinyLlama was marked feasible. These are estimates, not physical benchmark measurements.
- Synthetic dataset flow: created dataset `Mizan QA Synthetic — 2026-11-11` (slug `mizan-qa-synthetic-2026-11-11`), uploaded `mizan-qa-synthetic-2026-11-11.txt` (338 B), received “Successfully uploaded and parsed 1 document”; preview showed 41 words and SHA-256; froze version v1, which became `READY` with a version digest. This validates create/upload/parse/preview/freeze only, not Gate 1 approval.
- Free-only cost policy was visible; catalog clearly differentiated local $0/hour from reference-only cloud rates. No paid estimate or spend approval was submitted.
- Account Security & Sessions showed one current web browser session.
- Frontend Vitest after local fixes: 13 files, 55 tests passed. ESLint passed; TypeScript `tsc -b` passed; production Vite build passed (1,740 modules transformed).
- Backend targeted pytest: 23 passed across system health/version, authentication, dataset/document API, and hardware/Gate 2 suites. Backend Ruff: “All checks passed!”.

## Blocked or not exercised
- Full backend pytest suite: multiple invocations ended without a pytest completion summary (last visible progress was partial). Do not treat as a full-suite pass or failure. Targeted backend tests above did complete successfully.
- Login/logout, password reset, new registration, and verification-email flow were not re-authenticated end-to-end; an existing browser session was already active. The mailbox was searched for prior Mizan messages but no message body/token was opened or used.
- Gate 1 was not verified as approved. After the user indicated they had approved the synthetic dataset, I rechecked the production Approvals page: it still showed 0 masking runs, 0 pending reviews, and 0 Gate 1 signed attestations. I therefore did not treat the confirmation as a successful signed state and did not launch RAG indexing/query, evaluation suite generation/runs, or any workflow requiring an approved dataset. The dataset detail still showed v1 `READY`.
- No experiments, model builds, artifact registrations, Gate 2/Gate 3 approvals, catalog publication, invitations, customer-site enrollment, runtime slot activation/rollback, or operations remediation were performed.
- Runtime’s offline test returned: “Customer runtime has no active ready slot. Model inference unavailable.” Tenant had no runtime slots, no registered sites, and no published model/app assets. Local grounded RAG was disabled without a ready local index.
- No destructive, concurrency, multi-tenant race, penetration, recovery, performance/load, accessibility, or cross-device viewport tests were run.

## Runtime smoke-test outcome
The page showed `Offline Execution Active`, `Zero Outbound Telemetry`, and `MOCK_ENGINE`, but its synthetic chat completion request failed because the customer runtime has no active ready slot. This is a confirmed blocked path for this tenant; no root cause is asserted beyond the visible response and lack of a ready slot.

## Retained production test data / cleanup state
- Created: dataset `Mizan QA Synthetic — 2026-11-11`
- Slug: `mizan-qa-synthetic-2026-11-11`
- Contents: one synthetic TXT fixture only; it contains no real customer, personal, or confidential information.
- Version v1: `READY`/frozen; document parsed successfully. Gate 1 remains unsigned/unapproved.
- No deletion was attempted. The dataset and uploaded document remain in production for your review; deletion would require a separate explicit instruction.

## Evidence and source context
- Product manual: `docs/MIZAN_USER_MANUAL.md`
- Current app routes: `frontend/src/app/App.tsx`
- Estimator implementation: `frontend/src/features/hardware/components/ResourceEstimatorForm.tsx`
- Cost input implementation: `frontend/src/features/hardware/components/CostCentreView.tsx`
- Project status and production runbook: `docs/PROJECT_STATUS.md`, `docs/deployment/PRODUCTION_RUNBOOK.md`
- The project status report claims 52 frontend tests; this checkout run found 53, suggesting that count is stale or the test set changed.

## Overall assessment
The public surface, authenticated shell, several read-only modules, file ingestion/parsing, dataset freezing, and deterministic hardware comparisons are operational in this account. The hardware default/preset constraint mismatch is the clearest confirmed regression. The cost duration default also conflicts with its native step constraint. The larger governed AI lifecycle remains unverified in production because this tenant has no approved dataset, evaluation evidence, model release, enrolled site, or ready runtime slot—and I deliberately did not create approvals, releases, or deployments just to force those paths.
