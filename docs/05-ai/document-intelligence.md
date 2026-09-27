# Document Intelligence

This document specifies the document-processing pipeline in implementation detail: supported
formats, OCR handling, text extraction, chunking strategy for long contracts, and how the pipeline's
output maps to the `Clause` entity (`docs/03-domain/domain-model.md`). It is the concrete pipeline
that `agent-architecture.md` names as "the reference pipeline" and that `structured-extraction.md`'s
schema is extracted from.

## Supported formats

| Format | Handling |
|---|---|
| **PDF** | Primary format. Two sub-cases (see OCR section): native text-layer PDFs and scanned/image-only PDFs. |
| **DOCX** | Parsed from the document's XML content (paragraphs, tables, headers). DOCX has no native concept of a rendered "page" — see "Pagination for non-paginated formats" below for how page provenance is still produced. |
| **TXT** | Parsed as plain text. No native pagination; synthetic pagination is applied identically to the DOCX case. |

Any other format uploaded through `Document` (`docs/03-domain/domain-model.md`) is rejected at
upload time with a clear error — JuriSense Gate does not attempt best-effort parsing of arbitrary
file types (this is also a security boundary; see `SEC-003` in
`docs/01-product/functional-requirements.md`, which requires malware/type-spoofing validation before
processing).

## Pipeline overview

```
Document uploaded (content_hash computed, storage_key set — ADR-008)
        │
        ▼
1. Format detection & validation (MIME sniffing, not just extension trust — SEC-003)
        │
        ▼
2. Text extraction
   ├─ PDF with a usable text layer  → direct text extraction, page-accurate by construction
   ├─ PDF without a usable text layer (scanned) → OCR route (see below)
   ├─ DOCX  → XML parse + synthetic pagination
   └─ TXT   → raw read + synthetic pagination
        │
        ▼
3. Chunking (only if the extracted text exceeds the extraction model's practical input budget)
        │
        ▼
4. Single structured-extraction call (structured-extraction.md) — one call, or one call per chunk
   set merged deterministically, per agent-architecture.md's "no model-driven branching" rule
        │
        ▼
5. Provenance tagging: every field's {document_id, page, text_span, confidence} is attached
        │
        ▼
6. Clause mapping: each identified clause becomes a Clause row (below)
        │
        ▼
document.processed / contract.analysis_completed emitted
```

## Detecting whether a PDF needs OCR

A PDF is routed to OCR when its extracted native text layer is **absent or below a text-density
threshold** relative to the page count (a scanned PDF with an accidental text layer artifact — e.g.
a single OCR'd header line per page from the scanner software — should still be treated as
image-only). Concretely: extract native text per page; if the ratio of extractable characters to
page count falls below a configured minimum, or a page yields zero extractable characters while
containing image content, that page (and by default the whole document, to keep extraction
consistent) is routed to OCR instead of being extracted natively.

## OCR handling

Scanned/image-only PDF pages are run through an OCR step before structured extraction, producing
per-page text plus (where the OCR engine supports it) per-word/per-line bounding boxes, which are
used to derive `text_span` provenance the same way native-text extraction does (see "Text span
provenance" below). OCR output is treated as **lower-trust input**: OCR errors (misread digits in a
contract value, misread dates) are a known failure mode, so:

- Contracts routed through OCR should carry a lower baseline confidence multiplier applied to
  extracted fields sourced from OCR'd pages, reflected in the field's `confidence` score
  (`structured-extraction.md`), which in turn interacts with the human-confirmation guardrail
  (`guardrails.md`, `BR-CON-003`).
- OCR failures (engine error, unreadable/corrupted scan, non-Latin script the engine can't handle)
  route the `Document` to `document.processing_failed` rather than silently producing empty/garbage
  extraction — a human is notified to re-upload or manually key the contract's key terms.

> Status: TBD / Current preferred option: a managed cloud OCR API (e.g. a provider already used
> elsewhere in the AI Gateway's provider set, to minimize the number of vendor integrations) rather
> than a self-hosted OCR engine, consistent with the API-first default in `ADR-005`. / Why
> undecided: the right choice depends on a cost/accuracy benchmark across candidate OCR providers on
> a representative sample of real (or realistically scanned) Brazilian commercial contracts —
> Portuguese-language accuracy and layout-preservation quality vary meaningfully between providers
> and have not been benchmarked yet. / Resolution: run 2–3 candidate OCR providers against a sample
> of scanned contracts from the golden dataset (`evaluation.md`) and compare character error rate
> and downstream extraction accuracy, not just raw OCR accuracy in isolation. / Decision artifact: a
> dated addendum to this section (or a new ADR if the choice has broader infrastructure
> implications, e.g. a new vendor dependency).

## Pagination for non-paginated formats (DOCX, TXT)

`Clause` provenance requires a `page` value (`BR-CON-004`: "a clause without provenance cannot be
used as evidence"), but DOCX and TXT have no intrinsic page boundaries. JuriSense Gate applies
**synthetic pagination**: the extracted text is segmented into fixed-size synthetic "pages" (a
configured character/line budget approximating a typical rendered page), and provenance for these
formats records the synthetic page index consistently for a given `Document`. This is recorded as a
`pagination_mode: native | synthetic` flag alongside the extraction result so downstream consumers
(reviewer UI, evidence package) can display "page 3" vs. "approx. page 3" honestly rather than
implying rendered-page fidelity that doesn't exist for these formats.

## Text extraction detail

- **Native PDF**: extract per-page text preserving reading order; retain per-character or per-word
  offset information suf ficient to compute a `text_span` (character offset range within the page's
  extracted text) for any substring the extraction model cites.
- **DOCX**: parse paragraphs and tables in document order; table cells are flattened to text with
  a structural marker (so a clause embedded in a table, e.g. an SLA matrix, is not silently
  dropped) and offsets are tracked against the synthetic page text stream.
- **TXT**: read as UTF-8 (with encoding-detection fallback for legacy encodings common in older
  Brazilian corporate documents); offsets tracked against the synthetic page text stream.

## Text span provenance

Every extracted field and every `Clause` carries a `text_span`: `{start, end}` character offsets
into the page's (native or synthetic) extracted text, plus the `page` number and the source
`document_id`. This is what makes `BR-CON-004` and `AI-002`
(`docs/01-product/functional-requirements.md`) enforceable in practice — a reviewer or auditor can
always jump from a `Clause` or extracted field straight to the exact substring of the source document
that produced it, and `evaluation.md`'s citation-correctness check (does the cited span actually
contain the claimed clause) is only possible because this offset is recorded precisely, not
approximated after the fact.

## Chunking strategy for long contracts

Most contracts fit within a single extraction call's input budget; long contracts (master service
agreements with many schedules/exhibits, multi-hundred-page frameworks) do not. When chunking is
needed:

1. **Chunk boundaries follow structural cues first**: numbered sections/clauses, headings, schedule/
   exhibit breaks. This keeps a clause from being split across two chunks, which would otherwise
   corrupt both its extraction and its `text_span`.
2. **Fallback to token-budget-based splitting** with a small overlap window (enough to catch a
   clause whose heading and body straddle a fallback split point) when no clean structural boundary
   exists within the budget.
3. **Chunk metadata always carries its absolute page range and character-offset base** relative to
   the whole document, so a `text_span` computed within a chunk is translated back to
   document-absolute coordinates before being persisted — reviewers and the evidence package only
   ever see document-absolute provenance, never chunk-relative offsets.
4. **Merging is deterministic, not another LLM call**: per-chunk extraction results for
   document-level fields (e.g. `parties`, `value`) are reconciled by straightforward rules (prefer
   the chunk with higher confidence; flag a conflict for human review if two chunks disagree beyond
   a tolerance) rather than by asking a model to "resolve" them — consistent with
   `agent-architecture.md`'s "no model-driven branching" principle for this pipeline.
5. **Clause-level fields do not need merging** — each identified clause belongs to exactly one chunk
   by construction (structural chunking), so clause extraction is naturally chunk-local.

## Mapping to the `Clause` entity

Each clause the extraction step identifies becomes one `Clause` row (`docs/03-domain/domain-model.md`):

| Extraction output field | `Clause` attribute |
|---|---|
| Clause category (e.g. `liability`, `dpa`, `termination`, `confidentiality`) | `clause_type` |
| Page (native or synthetic, with `pagination_mode` recorded at the `ContractVersion` level) | `page` |
| Character offset range within that page's text | `text_span` |
| Model confidence for this specific clause identification | `confidence` |
| — (always present) | `contract_version_id` (the parent `ContractVersion`) |

`Clause` rows are immutable once created (`docs/03-domain/domain-model.md`) and are the only thing a
`RuleEvaluation` may cite as clause-level evidence (`BR-CON-004`) — a value that isn't traceable to a
`Clause` with valid provenance cannot participate in policy evaluation as clause evidence.

## Failure handling

| Failure | Handling |
|---|---|
| Corrupt / unreadable file | `document.processing_failed` emitted; `ContractVersion` stays out of `analyzed`; human notified to re-upload. |
| OCR engine error or unsupported script | Same as above — never silently proceed with empty/garbage text. |
| Extraction call schema-invalid response | Handled by the AI Gateway's validate/retry loop (`guardrails.md`), not by this pipeline directly. |
| Confidence below threshold on required fields | `ContractVersion` is flagged for human confirmation rather than marked `analyzed` (`BR-CON-003`, `guardrails.md`). |
