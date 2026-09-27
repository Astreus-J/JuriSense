# Brazil Market

> Why Brazil is the launch market, not a limitation; the sizing logic; the concrete public data
> sources that make Brazil-first supplier verification possible; and the procurement-culture context
> a seller needs to understand. For the technical Jurisdiction Pack architecture, see
> `docs/04-architecture/architecture-overview.md`; for what comes after Brazil, see
> `international-market.md`.

## Why Brazil first

Three independent reasons converge, not one:

1. **Regulatory forcing function (LGPD).** Brazil's Lei Geral de Proteção de Dados (LGPD) creates a
   direct, standing legal obligation for companies to know and document how their vendors handle
   personal data — a Data Processing Agreement is not optional paperwork, it is a compliance
   requirement with real enforcement exposure via the ANPD (Autoridade Nacional de Proteção de
   Dados). This gives JuriSense Gate's core pitch — "systematically check every supplier/contract
   against your policy, including data-processing exposure, with an audit trail" — a regulatory
   backstop that makes the sale easier than in a market with weaker enforcement pressure: the buyer
   is not just avoiding an abstract risk, they are managing a specific, named legal obligation. LGPD
   also structurally mirrors GDPR closely enough that the domain modeling done for the Brazil
   Jurisdiction Pack (DPA-clause extraction, data-processing risk rules) transfers with modification,
   not a rewrite, to a future EU pack (`international-market.md`).
2. **Home-market founder advantage.** Building for the market the team is embedded in means direct
   access to design partners, native-language sales conversations (Portuguese, per this repository's
   own documentation convention), and lived understanding of how Brazilian companies actually run
   procurement (see "Procurement culture context" below) — an advantage that does not transfer to a
   market entered cold.
3. **Underserved segment, not an underserved country.** Brazil is not chosen because the *TPRM
   category* is absent globally (Vanta/Drata/OneTrust are mature US-born products) — it is chosen
   because **no identified competitor combines Brazil-first supplier compliance data + contract
   intelligence + an executable policy engine + blockchain evidence for the 50–1,000-employee
   segment** (`docs/00-project/overview.md`, `competitive-landscape.md`). The large global players
   are enterprise-priced, English-first, and do not integrate Brazilian official sources
   (CNPJ/CEIS/CNEP/CEPIM) as first-class data — so a Brazil-first product does not compete head-on
   with them for this segment, it occupies space they have not prioritized.

## Target segment sizing — logic, not invented numbers

The qualitative sizing logic: Brazil has a large and growing base of technology companies (SaaS,
fintechs, digital-native retailers, tech-enabled services) in the 50–1,000-employee band — the band
where a company has enough vendor/contract volume to feel real pain (dozens of concurrent SaaS,
cloud, consultancy, and outsourcing relationships with periodic renewals) but has not yet reached the
size where it would default to an enterprise GRC suite like OneTrust, and has not yet built or bought
dedicated TPRM tooling. This is a structurally sound segment definition: it excludes both companies
too small to have a real procurement operation and companies large enough to already be served by
incumbents built for bigger budgets and more complex compliance regimes (bank/insurance-grade GRC).

What is *not* stated here as fact: exact counts of companies matching this profile, exact addressable
revenue, or exact expected penetration.

- Status: TBD / Current preferred option: build a bottom-up estimate using public Brazilian business
  registries (Receita Federal CNPJ data, segmented by CNAE codes for technology/SaaS-adjacent
  activities) cross-referenced with employee-count proxies (e.g., LinkedIn company data, RAIS/CAGED
  labor data where accessible) rather than citing a top-down "market size" figure that cannot be
  sourced / Why undecided: TAM/SAM/SOM figures require a dedicated data-pull and segmentation
  exercise that has not been run; any specific number stated now would be fabricated / Resolution:
  run the bottom-up CNPJ/CNAE segmentation as a Phase-2 spike (same phase as the compliance-data-
  source integration spike below) and publish the resulting TAM/SAM/SOM with its methodology, not as
  a bare number / Decision artifact: a sizing spreadsheet/methodology note (not yet created).

The stronger sizing signal available today is qualitative and directional: the pain (fragmented,
spreadsheet-and-email-based, unauditable vendor review) is described identically by every company in
this band that any team member has direct knowledge of, and it does not require an unusual company
profile to be present — any technology company with a real vendor list running through renewal cycles
has it. That is the basis for prioritizing this segment now, pending the quantitative sizing spike.

## Brazil-specific compliance data sources

This is the concrete, defensible part of the Brazil-first thesis: real, official, publicly accessible
Brazilian government data sources exist today that map directly onto Supplier Intelligence
(`docs/03-domain/domain-model.md`'s `SupplierCheck`/`SupplierProfile`), and using them is not a
speculative integration — it is a known, available data layer:

- **CNPJ registry data (Receita Federal)** — the authoritative source for a Brazilian company's legal
  existence, registration status (ativa/suspensa/inapta/baixada), corporate structure (sócios/
  responsible parties), and CNAE (economic activity code) — exactly the fields modeled in
  `SupplierProfile` (`registry status, corporate structure, responsible parties, CNAE, address`).
  This data is public and has multiple existing access paths, from Receita Federal's own public
  query tools to broader open-data mirrors.
- **CEIS (Cadastro Nacional de Empresas Inidôneas e Suspensas)** — the national registry of companies
  barred or suspended from contracting with public administration, published via Portal da
  Transparência. A hit here is a hard, unambiguous red flag.
- **CNEP (Cadastro Nacional de Empresas Punidas)** — companies sanctioned under the
  Anticorruption Law (Lei 12.846/2013), also via Portal da Transparência — directly relevant to
  contract-approval risk for any company that wants to avoid anticorruption exposure through its
  supply chain.
- **CEPIM (Cadastro de Entidades Privadas Sem Fins Lucrativos Impedidas)** — restrictions specific to
  nonprofit entities, relevant for suppliers structured as associations/institutes, also via Portal
  da Transparência.

**What is established fact vs. what is a Phase-2 spike**: that this data exists, is public, and is
structurally the right verification layer for `BR-SUP-003`/`BR-SUP-004`
(`docs/03-domain/business-rules.md` — a `Supplier` cannot reach `approved` without a completed check,
and a sanctions hit forces the `BLOCK` path) is established and used as given fact in this document.
The exact integration mechanism is not:

- Status: TBD / Current preferred option: direct API/bulk-data integration with Receita Federal's
  CNPJ data and Portal da Transparência's CEIS/CNEP/CEPIM datasets (both have historically offered
  open-data access, including bulk CSV downloads and, for Portal da Transparência, a public API) /
  Why undecided: exact API stability, rate limits, update frequency, and whether a paid data-
  aggregator intermediary (common in the Brazilian compliance-data-vendor market) is a better initial
  path than direct government-source integration has not been technically spiked / Resolution: a
  Phase-2 technical spike (tracked alongside the `ADR-007` blockchain-provider spike) to benchmark
  direct-source integration against at least one commercial aggregator, before committing
  `SupplierCheck`'s adapter implementation / Decision artifact: not yet created — will be an ADR once
  the spike concludes, mirroring how `ADR-007` handled the blockchain-provider decision.

## Procurement culture context

A few structural, non-numeric observations about how procurement and vendor approval actually work
inside the target segment in Brazil, which matter for both product design and sales framing:

- **Relationship-driven, informally documented.** Vendor selection in fast-growing Brazilian tech
  companies is frequently relationship- and referral-driven (a colleague's recommendation, an
  existing relationship from a previous company) more than a formal RFP process — which means the
  compliance check, if it happens at all, happens *after* an informal commitment has already been
  made socially, adding pressure to approve quickly rather than push back. A product that can turn
  around a check fast (versus a multi-week manual Legal review) fits this reality better than one
  that assumes a slow, deliberate procurement process exists to plug into.
- **Legal and Compliance as late-stage gatekeepers, not early-stage partners.** In this segment,
  Legal/Compliance functions are frequently lean (sometimes a single generalist counsel, sometimes
  outsourced) and are looped in near contract-signing rather than at vendor-selection time — meaning
  they are structurally positioned as a bottleneck under time pressure, which is exactly the
  condition where red flags get missed (see `business-case.md`'s delay-cost and risk-cost sections).
  This is an argument for a tool that plugs in early (at vendor intake) rather than only at final
  contract review.
- **CNPJ and formal registration status carry real weight culturally.** Because CNPJ status,
  CEIS/CNEP history, and formal registration are already the reference points Brazilian legal/
  compliance professionals use manually today (checking Receita Federal and Portal da Transparência
  by hand is a known, if tedious, existing practice), automating exactly those checks is intuitive
  to the buyer — it is not asking them to trust an unfamiliar methodology, it is automating a
  methodology they already recognize as legitimate.
- **LGPD awareness is real but compliance maturity is uneven.** Most target-segment companies know
  LGPD exists and carries risk, but few have systematized DPA review into vendor onboarding — this
  gap (awareness without systematization) is precisely the wedge described in `business-case.md`'s
  objection-handling for "we already have a spreadsheet process."

## Implication for go-to-market

The Brazil-specific reasoning above feeds directly into `go-to-market.md`: initial outreach should
lead with the LGPD/audit-trail angle for Legal/Compliance buyers and the vendor-approval-speed angle
for Procurement/COO buyers, use Portuguese-language content and a Brazil-based hackathon presence
(BLI Legal Tech Hackathon 2 / Legal Hack 2026) as credibility signals, and avoid assuming a mature,
formal RFP-driven procurement process exists at the target company — the pitch should work for a
lean, relationship-driven buying motion too.
