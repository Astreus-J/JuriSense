# Privacy Boundary — What Never Goes On-Chain

> Related: `docs/03-domain/business-rules.md` (`BR-EVD-002`), `docs/06-blockchain/evidence-model.md`
> (how hashes are built), `docs/06-blockchain/anchoring-providers.md`,
> `docs/06-blockchain/verification.md`, `docs/07-engineering/security.md` (tenant isolation controls
> this document cross-references for evidence-at-rest).

## The boundary, stated once, unambiguously

Blockchain is immutable by design — that is exactly why it is useful as a Trust Layer
(`docs/06-blockchain/blockchain-purpose.md`) and exactly why it is dangerous to put anything on it
that might ever need to be corrected, hidden, or forgotten. **No confidential data and no personal
data is ever placed on-chain. Only hashes and commitments of an `EvidencePackage` are anchored**
(`BR-EVD-002`, `docs/03-domain/business-rules.md`). This rule has no exceptions and no
"just this once" carve-out anywhere in the product: not in the Contract Hash, not in the Policy
Hash, not in the Evidence Hash, not in the Decision Hash, not in the Approval Hash
(`docs/06-blockchain/evidence-model.md`). Every one of those five categories is reduced to a SHA-256
digest before it ever reaches an `AnchoringProvider`.

## Hashing strategy

### Canonicalization

A hash is only useful for recomputation (`BR-EVD-001`) if the same logical content always produces
the same hash. JSON has no single canonical byte representation (key order, whitespace, and number
formatting can all vary), so every evidence payload is canonicalized before hashing:

- Object keys are sorted lexicographically at every nesting level.
- Whitespace, insignificant formatting, and trailing zeros are normalized away.
- This follows the same intent as RFC 8785 (JSON Canonicalization Scheme) — a deterministic,
  implementation-independent byte string for a given logical JSON value.

`content_hash = SHA-256(canonicalize(evidence_payload))` is then computed per `Evidence` item, and
the resulting leaves feed the Merkle tree described in `docs/06-blockchain/evidence-model.md`.

### Salting — and why it is mandatory, not optional

A bare hash of a small, guessable payload is not confidential just because it is "hashed." If an
`Evidence` item's underlying content is drawn from a small or enumerable space — for example, a
`Supplier`'s `tax_id` (CNPJ, a public-format, brute-forceable identifier) combined with a decision
outcome from the three-value set `{APPROVE, REVIEW, BLOCK}` — an attacker does not need to reverse
the hash function at all. They only need to **guess candidate inputs and hash them forward**:

```
guess: "CNPJ:12.345.678/0001-99|status:APPROVED"  → SHA-256(...) → compare to on-chain hash
```

Given a list of known or suspected CNPJs (CNPJ registries are public in Brazil) and the small,
fixed set of possible statuses, an attacker can precompute the hash for every `(CNPJ, status)`
combination and match the result against any hash observed on a public ledger — a classic
dictionary/rainbow-table attack against a **low-entropy** hash input. This would defeat the entire
purpose of hashing: it would let an outside observer learn exactly the confidential fact (which
supplier, what decision) that `BR-EVD-002` exists to keep off-chain.

**Mitigation**: every evidence payload is salted with a high-entropy, per-`EvidencePackage` random
value (a 256-bit nonce, generated fresh for each package, never reused) before hashing:

```
content_hash = SHA-256(canonicalize(evidence_payload) || package_salt)
```

The salt is stored only in tenant-isolated internal storage — never on-chain, never in any
externally reachable API response by default. Without the salt, an attacker's precomputed dictionary
of `(CNPJ, status)` hashes is worthless: the search space effectively becomes "guess the payload
*and* the 256-bit salt," which is computationally infeasible. A legitimate verifier does not need to
guess the salt — they receive it as part of the original `EvidencePackage` content (e.g., via a
Decision Passport export, or because they are the tenant who created the decision), the same way
they receive the rest of the canonical payload they are recomputing the hash from
(`docs/06-blockchain/evidence-model.md` §5). Verification requires *possessing* the source data, not
guessing it.

## Correlation risk: can an outside observer link anchors to specific companies or deals?

Even with salted, individually meaningless hash values, a public ledger is, by nature, public — and
metadata *around* an anchor can leak more than the hash itself does if left unmanaged. The risks
considered, and their mitigations:

- **Content correlation.** Risk: if JuriSense (or a customer) ever published raw `EvidencePackage`
  contents alongside the fact that "this hash was anchored," an observer could match them and, over
  time, build a map from on-chain hashes to real evidence. Mitigation: raw `EvidencePackage`
  contents are never published or exposed by default. The public verification page
  (`docs/06-blockchain/verification.md`) only ever returns a hash, a timestamp, a network name, and
  a boolean verification result — never the underlying payload — and only in response to a request
  that already supplies the specific Decision id or hash being checked (no public, browsable
  directory of all anchors exists to scrape and correlate against).
- **Submission-pattern / traffic analysis.** Risk: on an EVM-style path, if JuriSense always
  submitted anchors from the same wallet address, an observer could cluster every transaction from
  that address, infer submission volume and timing per organization (e.g., correlating anchor
  timestamps with a company's public earnings calendar or a known M&A announcement), and build an
  activity profile even without ever seeing a single evidence payload. Mitigation: submission timing
  and key/address management are treated as part of the adapter's design, not left to chance —
  batching or jitter on submission timing, and avoiding a single long-lived, easily fingerprinted
  submitter address tied 1:1 to a customer, are both design constraints carried into the Phase-8
  spike (`docs/06-blockchain/anchoring-providers.md`) alongside SDK and cost criteria; the exact
  key/relayer architecture is an implementation detail of whichever adapter is ultimately built, not
  a property of the `AnchoringProvider` interface itself.
- **Volume/frequency leakage.** Risk: even fully anonymized, a sudden spike in anchor volume from a
  customer could itself be a signal (e.g., of a large acquisition requiring bulk supplier
  re-review). This is a residual, inherent property of any public-ledger anchoring approach and is
  accepted as a known trade-off: the alternative (not anchoring at all) forfeits the entire
  verifiability benefit described in `docs/06-blockchain/blockchain-purpose.md`. It is mitigated,
  not eliminated, by the measures above.

## Metadata leakage beyond content

Beyond the hash value itself, anything else attached to an anchoring transaction is potential
metadata leakage: a submitter address, a memo/calldata field, a canister call's caller principal, or
even just precise transaction timing. The rule applied consistently across every candidate provider
in `docs/06-blockchain/anchoring-providers.md` is: **nothing beyond the salted hash, and the minimum
technical fields the network requires to process a transaction (e.g., a submitter address that pays
gas), is ever included in a submission.** No free-text fields, no tenant identifiers, no
human-readable labels of any kind are embedded in calldata, canister arguments, or Constellation data
submissions.

## LGPD / GDPR: the "right to erasure" vs. blockchain immutability

This is the most commonly raised objection to any blockchain-adjacent design under LGPD (Brazil) or
GDPR (EU): if personal data cannot be deleted from an immutable ledger, doesn't anchoring anything
derived from personal data violate the right to erasure (LGPD Art. 18, GDPR Art. 17)?

**The resolution is structural, not procedural**: JuriSense never places personal data — or anything
else confidential — on-chain in the first place (`BR-EVD-002`). What is anchored is a *salted hash*
of evidence that may have been derived, in part, from personal data (e.g., a named approver in the
Approval Hash, or a supplier's registered legal representative in the Contract Hash). A salted hash
of a value is not the value: it cannot be reversed to recover the original input, and — critically,
because of the salting discussed above — it cannot even be matched against a guessed candidate input
without also knowing the salt.

This means that once JuriSense deletes the **source data and its salt** from off-chain storage (in
response to an LGPD/GDPR erasure request, or per its own retention policy), the corresponding
on-chain hash becomes **permanently unlinkable and meaningless**: it is a fixed-length string of
bytes that no longer corresponds, provably or practically, to anything anyone can reconstruct. There
is nothing left on-chain to "erase" because nothing personal or confidential was ever stored there —
only an opaque commitment whose meaning depended entirely on off-chain material that has now been
removed. This is the actual LGPD/GDPR-compatibility argument: **compliance is achieved through data
minimization at the point of anchoring, not through an (impossible) promise to alter the ledger
later.**

One practical consequence follows directly: JuriSense's off-chain retention policy for the salt and
canonical payloads underlying an anchored hash must itself be deliberate — deleting a salt earlier
than a customer's own audit-retention needs would prematurely make that customer's own verification
capability unusable (they would no longer be able to recompute the hash to prove *their own*
evidence to *their own* auditor, even though the fact of the data being non-recoverable by outsiders
is exactly what makes the design LGPD-compatible in the first place). Retention windows for evidence
payloads and salts are a data-governance decision tracked alongside the organization's own audit and
compliance retention requirements, not a blockchain-specific concern.

## Tenant isolation for evidence at rest

Everything this document depends on — canonical payloads, per-package salts, and the mapping from a
`BlockchainAnchor` back to the `EvidencePackage` it represents — is stored off-chain, and therefore
is only as safe as the storage layer's tenant isolation. Every relevant record (`Evidence`,
`EvidencePackage`, `BlockchainAnchor`) carries tenant ownership transitively through `Decision` →
`ComplianceReview` → `Contract.organization_id` (`docs/03-domain/domain-model.md`'s "Tenant
ownership" field on each entity), so that:

- No query path can return another organization's evidence payloads, salts, or hashes without an
  explicit, audited cross-tenant operation (which the product does not expose in normal operation).
- The same row-level/`organization_id`-scoped access controls, encryption-at-rest, and access-logging
  practices that protect contract and supplier data generally also protect the evidence material
  underlying every anchor.

The concrete tenant-isolation mechanisms (database-level row scoping, storage-key namespacing under
`/dados/empresas/{organizacao_id}/`-style per-tenant paths, encryption key management, and access
controls) are specified once, for the whole platform, in `docs/07-engineering/security.md` — this
document does not duplicate that specification; it states that evidence-and-anchor data at rest is
in scope for it and receives the same guarantees as every other tenant-owned record.
