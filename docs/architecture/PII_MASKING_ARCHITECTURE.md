# Mizan PII Detection and Sensitive Data Masking Architecture

**Authoritative Baseline:** Mizan High-Level Design (`docs/reference/mizan_hld.png`)  
**Milestone:** 4 — Data Protection, Masking & Gate 1 Human Approval  
**Status:** ACTIVE  
**Updated:** 2026-11-08  

---

## 1. Architectural Mission & Invariants

In Mizan's architecture, the **Data Plane — Workshop** is where private business documentation is ingested and prepared for experimentation.

### The Immutable Boundary
1. **Raw Business Data Sovereignty:** Original uploaded business documents in `raw_uploads` are strictly isolated within the Workshop Data Plane and **NEVER** leave this plane.
2. **Outside Services Receive Only Masked Data:** External LLMs (e.g. Gemini, OpenAI, Claude) and pay-as-you-go GPU clouds (RunPod, Lambda) are allowed to receive **ONLY** approved, masked text.
3. **Mandatory Human Gate 1:** An automated detection score or successful masking job does not constitute authorization. An authorized human (Data Protection Officer or AI Lead) must inspect the detections, review unmasked snippets, make required corrections, and execute a cryptographically verifiable **Gate 1 Approval** before any external trial can commence.
4. **Zero-PII Metadata Invariant:** Raw personal identifiers are never stored in relational metadata, application logs, audit logs, or error responses.

---

## 2. Presidio Analyzer & Custom UAE Recognizers

Mizan utilizes **Microsoft Presidio Analyzer** as its extensible detection foundation, augmented with authoritative, localized recognizers for the United Arab Emirates business context.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            PRESIDIO ANALYZER ENGINE                         │
├──────────────────────────────────────┬──────────────────────────────────────┤
│       BUILT-IN GLOBAL PATTERNS       │          CUSTOM UAE PATTERNS         │
│  - EMAIL_ADDRESS                     │  - UAE_EMIRATES_ID                   │
│  - PHONE_NUMBER                      │  - UAE_IBAN                          │
│  - PERSON (Context / NER)            │  - UAE_PHONE_NUMBER                  │
│  - LOCATION                          │  - Organization Custom Identifiers   │
│  - CREDIT_CARD                       │                                      │
│  - IBAN_CODE                         │                                      │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

### A. UAE Emirates ID Recognizer (`UAE_EMIRATES_ID`)
* **Authoritative Reference:** UAE Government Design System ([designsystem.gov.ae/docs/patterns/emirates-id-input](https://designsystem.gov.ae/docs/patterns/emirates-id-input)).
* **Structural Specification:**
  - Exactly 15 digits.
  - Prefix is always `784` (ISO 3166-1 numeric code for the UAE).
  - Next 4 digits represent the 4-digit segment (often birth year).
  - Next 7 digits represent the sequence number.
  - Final 1 digit represents the check/verification digit.
  - Standard display formatting: `784-XXXX-XXXXXXX-X`.
* **Validation Rules:**
  - Matches formatted (`784-1945-1234567-0`) and unformatted (`784194512345670`) sequences with word boundaries.
  - Arbitrary 15-digit numbers lacking prefix `784` are rejected.
  - Masked presentation: `784-1945-XXXXXXX-X`.

### B. UAE IBAN Recognizer (`UAE_IBAN`)
* **Authoritative Reference:** Central Bank of the UAE Regulations & Standards ([centralbank.ae](https://centralbank.ae/en/our-operations/payments-and-settlements/regulations-and-standards/iban/)) and ISO 13616.
* **Structural Specification:**
  - Total length: exactly 23 characters.
  - Characters 1–2: Country code `AE`.
  - Characters 3–4: Two check digits.
  - Characters 5–7: Three-digit bank identifier code.
  - Characters 8–23: Sixteen-digit account number.
* **Validation Rules:**
  - Case-insensitive regex matching with boundary checks.
  - Normalization (removing spaces).
  - Full **ISO 13616 MOD-97** check-digit algorithmic validation:
    1. Move first 4 characters (`AE` + check digits) to the end.
    2. Convert letters to numbers ($A=10, B=11, \dots, Z=35$; `AE` becomes `1014`).
    3. Interpret the resulting string as a decimal integer.
    4. Compute remainder modulo 97. The IBAN is valid if and only if:
       $$\text{Integer} \pmod{97} == 1$$

### C. UAE Telephone Recognizer (`UAE_PHONE_NUMBER`)
* **Authoritative Reference:** UAE Telecommunications and Digital Government Regulatory Authority (TDRA) ([tdra.gov.ae](https://tdra.gov.ae/en/Pages/ict-dictionary)).
* **Structural Specification:**
  - National format: `05X XXXXXXX` (9 digits).
  - International format: `+971 5X XXXXXXX` or `00971 5X XXXXXXX`.
  - Authorized TDRA mobile prefixes: `050`, `052`, `054`, `055`, `056`, `058`.
  - Landline ranges: `02` (Abu Dhabi), `04` (Dubai), `06` (Sharjah/Ajman/UAQ), `07` (RAK), `09` (Fujairah).
* **Validation Rules:**
  - Parsed using Google `phonenumbers` library configured with regional default `"AE"`.
  - Validates country code `+971`, length, and active operator allocation.

### D. Person Names & Multilingual Handling
* Supported via Presidio's `SpacyRecognizer` or context-word recognizers.
* Separate language profiles for English and Arabic.
* On local 8 GB RAM machines, lightweight spaCy models (`en_core_web_sm`) or heuristic context recognizers are used. If full Arabic NER models are uninstalled, detection coverage is documented as requiring manual reviewer spot-checking, and the UI provides full support for adding manual PII spans.

---

## 3. Character-Level Unicode Code-Point Offsets & Overlap Handling

### Canonical Offset Specification
* `start_offset`: 0-based index of the first character of the detected entity (inclusive).
* `end_offset`: 0-based index immediately following the last character (exclusive).
* `offset_unit`: Unicode code points (scalar values).
* Boundary constraint:
  $$0 \le \text{start\_offset} < \text{end\_offset} \le \text{len}(\text{canonical\_text})$$

### Overlap Resolution Algorithm
Multiple detectors may produce overlapping spans (e.g. an Emirates ID substring matching a general number detector).
1. **Overlap Identification:** Spans $A$ and $B$ overlap if:
   $$\max(A.\text{start}, B.\text{start}) < \min(A.\text{end}, B.\text{end})$$
2. **Grouping:** All transitively overlapping spans are assigned a shared `overlap_group_id`.
3. **Conservative Redaction:** For automated replacement, overlapping spans within a group are merged into a single spanning interval covering $[\min(\text{starts}), \max(\text{ends})]$.
4. **Descending-Offset Replacement:** When mutating text into masked form, spans are applied in **strictly descending order of start offset** ($\text{span}_{n}, \text{span}_{n-1}, \dots, \text{span}_{1}$) to ensure that preceding text offsets remain stable throughout transformation.

---

## 4. Deterministic Masking Engine

The masking engine takes the canonical extracted text and the validated findings, producing an immutable masked document:
* **Strategies:**
  1. `REPLACE_WITH_ENTITY_LABEL`: Default strategy. Replaces sensitive span with bracketed entity tag (e.g. `[UAE_EMIRATES_ID]`, `[UAE_IBAN]`, `[PERSON]`).
  2. `REDACT`: Replaces text with a uniform blackout block (e.g. `[REDACTED]`).
  3. `PARTIAL_MASK`: Preserves non-sensitive prefix/suffix (e.g. `784-1945-XXXXXXX-X`).
* **Integrity Digest:**
  - A SHA-256 digest is computed over the resulting masked text string.
  - The masked text is stored in `StorageBucket.MASKED_DATASETS`.
  - The digest is permanently recorded in `MaskingRun.masked_output_digest`.

---

## 5. Extraction Coverage & OCR Safety Guard

A document with zero extracted text cannot be assumed to contain zero personal information (e.g. a scanned PDF or photographic contract).
* **Coverage Status Categories:**
  - `EXTRACTION_COMPLETE`: Full text extracted and analyzed.
  - `PARTIALLY_EXTRACTED`: Some pages or elements could not be parsed.
  - `OCR_REQUIRED`: Image-only PDF or scanned image file lacking OCR text.
  - `UNSUPPORTED_FORMAT`: Format cannot be parsed.
  - `EXCLUDED_BY_AUTHORIZED_REVIEWER`: Explicitly excluded from the dataset version by an authorized reviewer with a documented rationale.
* **Gate 1 Invariant:** Any document with `OCR_REQUIRED` or `EXTRACTION_FAILED` **strictly blocks Gate 1 approval** unless explicitly excluded by an authorized reviewer.
