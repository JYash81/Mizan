# Mizan Production E2E Audit — Follow-up (2026-11-11)

## Executive result

This follow-up extended the earlier production smoke audit through synthetic document upload, parsing, freeze, and a masking run. It stopped before any finding decision or Gate 1 human approval, in accordance with the stated governance boundary. The live workspace has **one completed masking run, four findings (all pending), and zero signed Gate 1 attestations**. Therefore RAG, evaluation, model building, release, and runtime flows that require Gate 1 approval remain blocked and are not claimed as tested.

A masking defect was observed: the synthetic email-shaped test value was not recognized as `EMAIL_ADDRESS`; the URL recognizer replaced only part of its domain, leaving a partial email string in the masked preview. This was reproduced locally and addressed with a syntax-based email fallback plus regression coverage for reserved `.invalid` and `.test` domains. The local cost estimator also returns `PRICE_UNAVAILABLE` for the local workstation despite its catalog row showing `$0.000/hour`. The email patch and tests remain local; no deployment was performed.

## Environment and test safety

- App: `https://mizan.hennt.in` — production, authenticated `hennt` / `Default Workspace`.
- Browser viewport: approximately 1146 × 947.
- The page initially displayed empty/loading states; after waiting for workspace data, the existing synthetic dataset v1 appeared. The initial empty display was transient and was not treated as proof that v1 was absent.
- Dataset testing used the existing account; a session expiry occurred during the v2 creation attempt, and private reauthentication succeeded before retry. Signup inspection showed required name/email/password/confirmation fields and an unchecked Terms/Privacy agreement. The user confirmed `Hero` / `yeswanthjanne81@gmail.com` is intentional and accessible (connected Gmail is `yeswanthjanne86@gmail.com`). The form is staged with name/email only; the user still needs to privately enter a password, decide on the agreement, and submit. No new account or verification email has been created/sent.
- All uploaded content in this follow-up was generated, fictional test content. No real customer or personal data was used.
- The user authorized v2 creation and masking testing, asked that the synthetic dataset be retained, and required stopping before Gate 1 approval. No finding was confirmed/dismissed, no Gate 1 decision was submitted, and no cloud compute was provisioned.
- Original v1 was not changed. New v2 and its synthetic document remain in production for review.

## Test flow and evidence

### Dataset and parsing

1. Opened existing dataset **Mizan QA Synthetic — 2026-11-11**, slug `mizan-qa-synthetic-2026-11-11`. Version v1 was frozen/READY with one parsed 338-byte synthetic policy document.
2. Created v2 with description noting synthetic-only E2E scope and no Gate 1 approval/external processing.
3. Uploaded `mizan-qa-synthetic-e2e-v2.txt` (622 bytes; 79 words). UI reported **“Successfully uploaded and parsed 1 document.”** The document status was `Parsed`.
4. Froze v2. It transitioned from `DRAFT` to `READY` and displayed a cumulative SHA-256 digest beginning `03cdf7b55f4fc937…`.

IDs for support/reproduction (non-secret): dataset `613dd093-efeb-4502-845c-caee44926f7e`; v2 `b4073a9c-6a5c-4716-86f5-e0ce11eb2688`; document `119b033d-cc1f-4fae-9c1b-9425ba01f6bf`.

### Masking and Gate 1 state

- The Approvals page states that upload + version finalization triggers detection/masking, but after v2 freeze the page continued to show no run. Local source inspection shows dataset finalization sets the version to `READY` and computes its digest; the frontend has no masking-run creation action. To test the expressly authorized masking function, a single authenticated `POST /workspaces/{workspace_id}/masking-runs` was invoked for this synthetic v2 through the live browser session. It returned HTTP 201.
- Run `ad800e7f-7b85-420c-93d0-8e2f92deca20` completed: **1 document processed, 0 failed, extraction coverage `EXTRACTION_COMPLETE`, 4 findings, 4 unresolved**.
- The Approvals page subsequently showed **1 masking run, 4 sensitive spans, 4 pending reviews, 0 Gate 1 signed attestations**. The review screen showed `Awaiting Human Review`.
- Finding categories were `DATE_TIME`, `URL`, `UAE_EMIRATES_ID`, and `UAE_PHONE_NUMBER`. The masked preview tokenized the Emirates-ID-shaped and phone-shaped placeholders. The deliberately invalid-checksum IBAN-shaped placeholder was not detected; this does not establish behavior for a valid IBAN.
- The synthetic email placeholder using the reserved `.invalid` domain was not classified as `EMAIL_ADDRESS`. The `URL` finding replaced only part of the domain; the preview showed `qa.e2e@[URL]valid`, leaving a partial email-shaped string. This was reproduced locally using the live fixture text. A syntax-based fallback now detects the complete reserved-domain address and produces one `[EMAIL_ADDRESS]` mask. The QA fixture also produced a `DATE_TIME` finding from the test date and a `URL` finding from the email-like placeholder; these may be false positives, but no reviewer decision was made.
- No finding action and no Gate 1 approval/rejection was submitted. **Exact governance blocker:** the 4 findings on run `ad800e7f-7b85-420c-93d0-8e2f92deca20` remain unresolved/awaiting human review, and the current Gate 1 approvals API list is empty (0 signed attestations). v2 approval remains unverified; downstream protected actions were not attempted.

### Hardware and cost estimator

- Production resource estimator defaulted to `Llama-3-8B`, `8000` million parameters, Q4_K_M, CPU inference, 2048-token context, batch 1, local 8-GB workstation. Calculate completed and reported `NOT FEASIBLE` with negative headroom, consistent with the displayed hardware profile. This verifies the default can be submitted in the production UI; it does not establish the production source step attribute or that a local source change was deployed.
- Preset checks showed matching name/parameter values for 3.8B (`Phi-3-Mini-3.8B` / 3800), 7B (`Mistral-7B` / 7000), 8B (`Llama-3-8B` / 8000), and 70B (`Llama-3-70B` / 70000). Recalculating after selecting 70B updated the result to the 70B model and correctly marked it not feasible on the local 8-GB profile.
- Workload Cost Estimator default duration was **2 hours**. Under the visible free-only policy, calculating the local workstation returned **`$UNKNOWN USD` / `PRICE_UNAVAILABLE`**, with the message that no verified/reference pricing record exists for `local/local-i5` in region `local`, even though the catalog displays `LOCAL_CPU_I5_8GB` at `$0.000/hour`. This is a confirmed production inconsistency; its root cause is not established.
- A reference-only A100 estimate returned `$6.12` for 2 hours at the displayed `$3.060/hour`; UI clearly labeled the rate `REFERENCE_ONLY` and said it was not independently verified. No spending or provisioning occurred.

## Local regression validation (no deploy)

- Reproduced the production partial-email result locally: `qa.e2e@example.invalid` yielded only a `URL` span for `example.in`, masking to `qa.e2e@[URL]valid`.
- Added `MizanEmailSyntaxRecognizer` as a fallback using Presidio's email syntax pattern without public-suffix validation, plus `tests/test_email_masking_regression.py` for reserved `.invalid` and `.test` domains. The test verifies the complete email is one `EMAIL_ADDRESS` finding and the masked output contains no original or partial address.
- Focused run of the new test, UAE recognizer tests, masking service tests, Gate 1 API tests, and tenant-isolation tests: **15 passed**. Ruff on the changed registry and test: **all checks passed**. Pytest emitted existing cache-permission and Starlette deprecation warnings; no test failed.
- Existing frontend validation from the prior audit: 13 files / 55 tests passed; ESLint, TypeScript check, and production build passed.
- Follow-up backend estimator/policy tests: 21 passed across `tests/test_hardware_and_gate2.py` and `tests/test_cost_and_privacy_policy.py`.
- The standalone runtime module previously passed 7/7. The broader backend run remains inconclusive: one fail-fast run reported 108 passed and a rollback assertion failure (expected `ROLLBACK`, observed `Production promotion after golden test pass`); running that runtime module alone passed. Other full-suite runs ended without a final pytest summary. Do not characterize the full backend suite as passing.
- Local hardware-step and cost-duration fixes/regression tests remain local only. No deployment was performed.

## Stop conditions and exclusions

Testing stopped after the synthetic masking review revealed the missing Gate 1 attestation. No RAG indexing/query, evaluation-suite generation or benchmark, experiment, model training/build, artifact release, Gate 2/Gate 3 action, customer-site enrollment, runtime deployment/rollback, or external processing was attempted. The live runtime still had no active runtime slots or Golden Acceptance Tests in the prior audit; a harmless offline completion request failed closed with “Customer runtime has no active ready slot. Model inference unavailable.”

Registration form validation was inspected and staged with user-authorized name/email; the user chose to enter the password privately and submit themselves. No account has yet been created and no verification email has been sent or verified. Password-reset, logout, load/performance, accessibility, cross-device, destructive recovery, and production multi-tenant isolation flows were not tested. Some module pages showed delayed or persistent loading during navigation; route-level smoke inspection should not be mistaken for functional coverage.

## Overall assessment

The live application supports synthetic dataset upload/parse/freeze and a backend masking run, but the Gate 1 overview implies freeze automatically starts masking while the UI has no visible run-creation action; the run appeared only after an authenticated API call. A partial-email masking gap was reproduced and a local fallback plus regression test now pass; this change is not deployed. The production local cost estimate remains unavailable despite a zero-cost catalog row. With 4 findings pending and no signed Gate 1 attestation, the governed E2E chain is not complete. The v2 fixture is retained for human review; approval remains solely for the designated reviewer. Signup has not been submitted and verification remains pending the user's private step.
