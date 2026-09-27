# Competitive Landscape

> Per-competitor analysis across the categories JuriSense Gate overlaps with: compliance automation,
> privacy/GRC, CLM, legal-AI drafting, and agentic compliance. Company facts (funding, valuation,
> positioning) are taken as given from prior research per this task's brief and are not re-verified
> here. For the synthesized moat argument built on this analysis, see `differentiation.md`; for how
> this shapes the sales narrative, see `business-case.md`.

## How to read this document

For each competitor: primary use case, target customer, product category, strengths, overlap with
JuriSense Gate, where JuriSense differs, what has become commodity in that space, and — the point
most useful for prioritization — what JuriSense should **not** try to build as a differentiator
because it is already commodity or already owned elsewhere.

## Compliance automation: Vanta, Drata

**Primary use case**: automating SOC 2, ISO 27001, HIPAA, and similar security/compliance
*certification* evidence collection — continuously monitoring internal systems (cloud config, HR
systems, device management) and mapping the results to audit-framework controls.

**Target customer**: engineering-led startups and scale-ups that need to pass a security audit to
close enterprise deals — the buyer is frequently a CTO/Head of Security/Head of Compliance focused on
*the company's own* certification status, not on evaluating third-party vendors.

**Product category**: compliance automation / audit-readiness tooling.

**Strengths**: category-defining continuous-monitoring integrations (hundreds of system connectors),
very strong product-led growth motion, mature trust with the exact engineering-adjacent buyer they
target, fast time-to-first-value (connect systems, see gaps immediately).

**Overlap with JuriSense Gate**: both produce structured, auditable evidence trails; both position
around "prove compliance, don't just claim it"; both increasingly touch vendor risk (Vanta and Drata
have both expanded into vendor-risk-management modules as an adjacency to their core certification
product).

**Where JuriSense differs**: Vanta/Drata's vendor-risk features are an *adjacency* to their core
product (helping a company pass its own audit by demonstrating it manages vendor risk), not a
purpose-built supplier + contract + policy + approval workflow. They do not do contract intelligence
(clause extraction, liability/DPA/termination analysis), do not have an executable company-specific
policy engine driving `APPROVE/REVIEW/BLOCK` decisions, and are not Brazil-first (no CNPJ/CEIS/CNEP
integration, no LGPD-specific policy templates). JuriSense Gate's core object is the vendor/contract
decision itself; Vanta/Drata's core object is the company's own control posture.

**What has become commodity here**: continuous evidence-collection integrations against common SaaS
systems (Okta, AWS, Google Workspace, HR systems) are now a baseline expectation across the whole
compliance-automation category, not a differentiator — multiple vendors (Vanta, Drata, and smaller
challengers) offer largely comparable coverage.

**What JuriSense should NOT try to build as a differentiator**: a broad, general-purpose internal
control-evidence-collection platform competing head-on with Vanta/Drata's connector breadth. That
market is already commoditizing among well-funded specialists; JuriSense's evidence/audit layer
should stay scoped to *vendor and contract decision* evidence (per `docs/03-domain/domain-model.md`'s
`EvidencePackage`), not generalize into "SOC2 audit readiness for your own company."

## Privacy / GRC: OneTrust

**Primary use case**: enterprise privacy management and broader GRC (governance, risk, compliance),
including a mature Third-Party Risk Management module, consent management, and data-mapping —
essentially the incumbent full-suite GRC platform.

**Target customer**: enterprise and legal/privacy-office buyers, typically at large companies with
dedicated privacy/GRC functions and budgets that can absorb enterprise software pricing and
multi-month implementation projects; explicitly handles LGPD alongside GDPR/CPRA as part of its
global privacy-regulation coverage.

**Product category**: enterprise privacy/GRC suite.

**Strengths**: category incumbency, breadth (privacy + TPRM + GRC + consent + data mapping in one
suite), global regulatory coverage including LGPD, deep enterprise sales and implementation
capability, strong brand recognition with General Counsel/Chief Privacy Officer buyers.

**Overlap with JuriSense Gate**: TPRM is a direct, named overlap — OneTrust's TPRM module addresses
exactly the "should we approve this vendor" question JuriSense Gate is built around, and OneTrust
already supports LGPD as a jurisdiction, which is the same regulatory hook `brazil-market.md` builds
on.

**Where JuriSense differs**: OneTrust is priced, packaged, and implemented for enterprise buyers —
multi-month implementations, enterprise-scale contracts, and a suite-wide commitment that is a poor
fit for a 50–1,000-employee company without a dedicated GRC function or budget (exactly the gap named
in `docs/00-project/overview.md`'s target-segment definition). OneTrust is also not purpose-built
around an *executable, versioned, company-authored policy engine* producing a single explainable
`APPROVE/REVIEW/BLOCK` decision with full evidence provenance per decision — its strength is breadth
of GRC coverage, not a sharp, auditable, contract-and-clause-level decision engine. It is also not
combined with AI-driven contract clause extraction as a first-class, structured pipeline output in the
way `docs/03-domain/domain-model.md`'s `Clause`/`ContractVersion` model is.

**What has become commodity here**: basic third-party risk *questionnaire* automation (send a vendor
a security/privacy questionnaire, track responses, flag missing answers) is now a widely available
feature across GRC and even lighter-weight TPRM point solutions — it is not, by itself, a
differentiator.

**What JuriSense should NOT try to build as a differentiator**: a broad, general-purpose GRC suite
matching OneTrust's full breadth (consent management, cookie compliance, full data-mapping platform,
etc.) — that is a multi-year enterprise-suite build that would dilute focus away from the sharper
supplier+contract+policy+evidence decision loop that is JuriSense's actual wedge. Vendor-questionnaire
automation specifically should be treated as table stakes to have, not a feature to over-invest in as
a selling point.

## CLM: Ironclad

**Primary use case**: enterprise Contract Lifecycle Management — contract creation, negotiation
(redlining/collaboration), execution (e-signature integration), and post-signature obligation
tracking, spanning the full contract lifecycle from drafting to renewal.

**Target customer**: enterprise legal and procurement/sales-ops teams managing high contract volume,
frequently with dedicated legal-ops functions.

**Product category**: Contract Lifecycle Management (CLM).

**Strengths**: mature workflow coverage across the entire contract lifecycle (not just review),
strong e-signature and CRM/ERP integrations, established enterprise trust and deep negotiation-
workflow tooling (clause libraries, playbooks, redlining).

**Overlap with JuriSense Gate**: both deal with contract structure, clauses, obligations, and
approval workflows; both aim to reduce contract-related risk and cycle time.

**Where JuriSense differs**: Ironclad's core value is *authoring and negotiating* the contract
(creation → negotiation → execution) and tracking obligations post-signature; JuriSense Gate's core
value is *evaluating whether to approve* a supplier/contract against company policy, combined with
supplier-side compliance verification Ironclad does not do at all (no CNPJ/sanctions-list checking,
no supplier-entity risk scoring). JuriSense is not a drafting or negotiation tool and does not
compete on redlining workflows; it complements a CLM by providing the compliance-gate decision a
company would apply before or alongside using a CLM for the paperwork itself. Ironclad is also
enterprise-priced and enterprise-implemented, the same segment-fit gap as OneTrust for this product's
target buyer.

**What has become commodity here**: e-signature integration and basic clause-library/template
management are now baseline CLM features across many vendors (Ironclad, DocuSign CLM, PandaDoc, and
others), not a differentiator on their own.

**What JuriSense should NOT try to build as a differentiator**: a full contract-authoring/redlining/
negotiation product. That is Ironclad's (and several others') core competency and a large, separate
product surface; JuriSense Gate should integrate with e-signature/CLM tools where useful rather than
rebuild contract negotiation workflows.

## Legal AI drafting: Harvey, Spellbook

**Primary use case (Harvey)**: AI-assisted legal work for BigLaw and large legal departments — legal
research, drafting, and analysis across a broad range of legal tasks, positioned as a general legal-AI
platform for large, sophisticated legal teams.

**Primary use case (Spellbook)**: AI-assisted contract drafting and redlining inside Microsoft Word,
comparing clauses against a large benchmark set (2,000+ benchmarks) to suggest edits during contract
negotiation.

**Target customer**: Harvey targets BigLaw firms and large in-house legal departments at a scale
reflected in its reported reach (100,000+ lawyers, 1,300+ organizations) and its 2026 valuation
(~$11B); Spellbook targets individual lawyers/legal teams doing contract drafting and negotiation work
inside their existing Word-based workflow.

**Product category**: legal AI (drafting/research assistance for Harvey; contract drafting/redlining
copilot for Spellbook).

**Strengths**: Harvey has deep legal-domain model tuning, brand trust with elite legal buyers, and
massive scale/capital advantage; Spellbook has a sharp, well-loved point-solution wedge (redlining
inside the tool lawyers already use) and a large clause-benchmark dataset.

**Overlap with JuriSense Gate**: both use AI to read, interpret, and reason about contract language;
both aim to reduce the manual burden of contract review.

**Where JuriSense differs**: neither Harvey nor Spellbook is a *decision/workflow* product — they
assist a human who is actively drafting or researching, not automate a company's *own* internal
approve/review/block decision against its *own* policy, and neither does supplier-side verification,
policy-engine-driven aggregation, approval routing, or blockchain-anchored evidence. Harvey's buyer
(BigLaw, large legal departments) and price point are also structurally mismatched with JuriSense's
target segment (50–1,000-employee companies without a large in-house legal team, let alone a BigLaw
relationship for this specific workflow). Spellbook's Word-based drafting-copilot model is a different
moment in the contract lifecycle (drafting/negotiating the document) than JuriSense's (deciding
whether to approve the vendor/contract combination against policy, with an audit trail).

**What has become commodity here**: basic AI-assisted clause identification and summarization
("what does this contract say about liability") is now widely available — offered by legal AI tools,
general-purpose LLM products, and increasingly as a feature inside broader CLM/GRC suites. Raw
extraction/summarization quality alone is not a durable differentiator.

**What JuriSense should NOT try to build as a differentiator**: a general-purpose legal drafting or
research assistant competing with Harvey's breadth, or a redlining/negotiation copilot competing with
Spellbook inside Word. JuriSense's AI investment should stay scoped to structured extraction feeding a
deterministic policy decision (`docs/05-ai/ai-strategy.md`), not general legal reasoning or drafting
assistance — that is a different (and, for Harvey especially, heavily capitalized) competitive game.

## Agentic compliance: Norm AI

**Primary use case**: "agentic law" — AI compliance agents that operationalize regulatory and internal
policy as ongoing, autonomous monitoring/enforcement agents, with a notable enterprise-software
distribution move (Microsoft 365 Copilot integration) and a large recent raise ($120M Series C, July
2026, $1.2B valuation) signaling strong investor conviction in the "compliance-as-agents" thesis.

**Target customer**: large enterprises adopting agentic AI for regulatory/compliance monitoring
broadly (not vendor/contract-specific), reachable in part through the Microsoft 365 ecosystem given
the Copilot integration.

**Product category**: agentic compliance / regulatory-AI agents.

**Strengths**: strong capital position and investor validation of the agentic-compliance category,
enterprise distribution leverage via Microsoft 365 Copilot, a general and extensible "compliance
agent" framing that can in principle be pointed at many regulatory domains.

**Overlap with JuriSense Gate**: closest conceptual competitor of everything analyzed here —
Norm AI's core idea (operationalize policy/regulation into an executable, monitored agent) is
philosophically similar to JuriSense's Policy Engine + Compliance Engine combination
(`docs/03-domain/domain-model.md`, `ADR-004`, `ADR-010`).

**Where JuriSense differs**: Norm AI is general-purpose and enterprise/Microsoft-ecosystem-distributed,
not specifically built around the supplier-verification + contract-intelligence + approval-workflow +
blockchain-evidence combination for the vendor-compliance use case, and is not Brazil-first (no
CNPJ/CEIS/CNEP integration, no LGPD-specific tooling evidenced). JuriSense's scope is deliberately
narrower and deeper — one workflow (vendor/contract approval) done completely, including the parts
Norm AI does not appear to cover (supplier registry/sanctions verification, contract clause-level
citation, blockchain-anchored evidence) — rather than a general "compliance agent" framework applied
broadly.

**What has become commodity here**: the *idea* of "AI applies policy rules automatically" is
increasingly well understood and is being pursued by multiple well-funded players (Norm AI being the
clearest example) — the abstract concept of an executable policy engine is not, by itself, a
differentiator anymore; execution depth and domain specificity are what remain differentiable.

**What JuriSense should NOT try to build as a differentiator**: a general-purpose, domain-agnostic
"compliance agent platform" positioned to compete with Norm AI's breadth and enterprise-distribution
strategy. JuriSense does not have Norm AI's capital or Microsoft-ecosystem distribution advantage, and
trying to out-generalize a $1.2B-valuation, Series-C-funded competitor on breadth would be a losing
strategy; the durable position is narrow, deep, and Brazil-first supplier/contract-specific execution
(see `differentiation.md`), not a broader compliance-agent platform race.

## Summary table

| Competitor | Category | Core overlap | Sharpest JuriSense difference | Commodity to avoid competing on |
|---|---|---|---|---|
| Vanta / Drata | Compliance automation | Auditable evidence trails; vendor-risk adjacency | Purpose-built vendor/contract decision engine vs. their own-company audit-readiness focus | Broad system-integration evidence collection |
| OneTrust | Privacy / GRC | Direct TPRM overlap, LGPD coverage | Mid-market fit + sharp policy-engine decision loop vs. enterprise GRC suite breadth | Vendor questionnaire automation |
| Ironclad | CLM | Contract structure/approval workflow | Compliance-gate decision vs. drafting/negotiation/execution lifecycle | E-signature + clause-library management |
| Harvey | Legal AI (BigLaw) | AI contract/legal reading | Mid-market workflow product vs. BigLaw legal-research/drafting platform | Basic clause summarization |
| Spellbook | Legal AI (drafting) | AI contract analysis | Approval-decision workflow vs. in-Word drafting/redlining copilot | Basic clause summarization |
| Norm AI | Agentic compliance | Executable policy-as-code philosophy | Narrow, deep, Brazil-first vendor/contract execution vs. general enterprise compliance-agent platform | The abstract "AI applies policy automatically" concept itself |

## The synthesis

No competitor above combines: (1) Brazil-first official-source supplier verification, (2) structured
contract clause extraction with provenance, (3) an executable, versioned, company-authored policy
engine producing a single explainable decision, and (4) blockchain-anchored evidence — for the
50–1,000-employee segment. Every individual *ingredient* of that combination exists somewhere in this
landscape (evidence automation at Vanta/Drata, TPRM at OneTrust, contract structure at Ironclad,
AI contract reading at Harvey/Spellbook, policy-as-code philosophy at Norm AI) — none combine them for
this buyer. This is the basis for the moat hypothesis in `differentiation.md`, stated there explicitly
as a hypothesis to validate, not a settled competitive claim.
