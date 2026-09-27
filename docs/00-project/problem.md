# The Problem

`docs/00-project/overview.md` states the problem in one paragraph. This document expands it: what
companies actually buy, what is supposed to happen before they sign, who is supposed to be involved,
why that coordination breaks down in practice, and — concretely, not abstractly — what goes wrong
when it does.

## What companies actually buy

A technology company in the 50–1,000-employee range JuriSense targets (see
`docs/00-project/overview.md` "Market") is not signing one or two contracts a year. It is
continuously buying:

- **SaaS subscriptions** — the tools every function runs on: CRM, HR/payroll, observability, data
  warehousing, customer support, analytics, design, security tooling. Often dozens of active vendors,
  frequently procured by individual teams (a "shadow IT" SaaS subscription started on a company card
  is one of the most common ways a vendor relationship exists before Procurement ever sees it).
- **Consultancies and professional services** — legal, accounting, HR, strategy, and technical
  consulting engagements, often short-lived and negotiated quickly under time pressure.
- **Outsourcing and staff augmentation** — contracted developers, support staff, or entire outsourced
  teams, which raise a distinct set of labor-law, data-access, and IP-assignment questions beyond a
  typical SaaS contract.
- **Cloud and infrastructure providers** — hyperscalers and specialized infrastructure vendors, where
  the company's own customer data frequently flows through the vendor's systems, making the vendor's
  own security and compliance posture directly inherited risk.
- **Individual developers and freelancers** — contracted directly, often with the least formal
  contracting process of any category, and frequently with direct code or data access.
- **Strategic and channel partners** — resellers, integrators, and co-marketing partners, where the
  contractual relationship is less about service delivery and more about liability, IP, and revenue
  sharing.

Each of these categories carries a different risk profile, but all of them funnel through the same
under-resourced review process before a signature happens.

## What is supposed to happen before signing

Before any of these contracts is signed, a reasonably careful company is supposed to check, at
minimum:

- **Registration and identity data** — does this legal entity actually exist, is it in good standing,
  who are its beneficial owners and legal representatives, does the entity signing match the entity
  being paid.
- **Sanctions and restriction lists** — is the supplier or any of its principals on a sanctions,
  debarment, or restriction list (in Brazil: CEIS, CNEP, CEPIM, and equivalents) that would make
  contracting with them a direct legal or reputational liability.
- **General compliance posture** — does the vendor have the certifications, policies, or track record
  the engagement requires (security certifications for an infrastructure vendor, professional
  licensing for a consultancy, safety compliance for an outsourced labor provider).
- **LGPD / data-processing exposure** — will this vendor process personal data on the company's
  behalf, and if so, is there a valid Data Processing Agreement (DPA) with the required LGPD clauses,
  and does the vendor's own sub-processor chain create further exposure.
- **Security posture** — for any vendor touching systems, code, or data, is there evidence of
  reasonable security practice (this is often the single hardest check to actually perform, because
  it requires technical judgment Procurement and Legal typically do not have).
- **SLA terms** — are the uptime/response-time/support commitments adequate for how the company will
  actually depend on this vendor, and are the remedies for missing them meaningful.
- **Liability caps** — is the vendor's total liability exposure capped at a level appropriate to the
  actual risk of the engagement, or is the company silently accepting unlimited exposure (or granting
  it) in a clause nobody flagged.
- **IP terms** — for anything involving development, content, or data work, who owns the output, and
  are pre-existing IP and third-party IP handled correctly.
- **Renewal and termination terms** — does the contract auto-renew, on what notice period, and does
  the company have a realistic operational process to catch that notice window before it passes.
- **Internal approval requirements** — does this specific contract, given its value, risk category, or
  data exposure, actually require sign-off from Legal, Compliance, Finance, Security, or a director,
  per the company's own internal policy — and can anyone quickly determine which of those apply.

None of this is exotic. It is the ordinary due-diligence checklist any competent Legal or Compliance
function already knows. The problem is not that companies don't know what to check — it's that
performing these checks, consistently, for every vendor, at the volume a growing company generates,
and leaving a record of having done so, is a coordination and process problem, not a knowledge
problem.

## Who is involved, and why coordination is the actual bottleneck

Answering "can we sign this?" correctly touches at least six functions, each of which owns a slice of
the answer and none of which owns the whole thing:

- **Procurement** typically originates the request, tracks the vendor relationship commercially, and
  is the one function with visibility into *volume* — but usually has no tooling or standing to
  independently assess legal or security risk.
- **Legal** reviews contract language — liability, IP, indemnification, dispute resolution,
  termination — but is usually looped in only after commercial terms are already agreed, under time
  pressure to "just get this reviewed by Friday," and rarely has visibility into whether the vendor
  even passed a basic sanctions or registration check.
- **Compliance** owns the sanctions/restriction-list checks and the internal policy the deal is
  supposed to satisfy, but often finds out about a new vendor only when someone remembers to loop them
  in — there is frequently no forcing function that guarantees Compliance sees every vendor before
  signature, only every vendor someone thought to mention.
- **Finance** cares about payment terms, contract value thresholds that should trigger extra approval,
  and budget ownership, but typically only sees the vendor once an invoice or purchase order shows up,
  which is often after the contract is already signed.
- **Security** is supposed to assess any vendor with system, code, or data access, but security review
  is frequently the first thing skipped under deadline pressure, precisely because it is the slowest
  and most specialized check to perform.
- **Privacy** (often a hat Legal or Compliance wears, not a dedicated team, at this company size) is
  responsible for catching LGPD/data-processing exposure and DPA requirements, which requires someone
  to correctly recognize "this vendor will touch personal data" in the first place — a classification
  step that is easy to get wrong or skip entirely when nobody is explicitly asked the question.

Today, coordinating these six functions happens over **email threads and spreadsheets**: a
Procurement analyst emails a contract PDF to Legal, CCs Compliance "just in case," someone manually
checks a sanctions list website and pastes a screenshot into a Slack thread, Finance approves a
purchase order in a completely separate system with no link back to the contract review, and the only
record that any of this happened is scattered across inboxes, chat history, and, if the company is
unusually disciplined, a shared spreadsheet row that says "Approved — see thread." There is no single
system of record for the *decision*, only for its scattered inputs. Nobody owns making sure all six
functions actually weighed in before signature — it depends on individual diligence and institutional
memory, which does not scale past a handful of contracts per month and does not survive turnover.

## What concretely goes wrong

These are not hypothetical edge cases — they are the predictable, recurring failure modes of a
manual, email-and-spreadsheet coordination process at this volume. They are illustrative composites,
not claims about any specific real company, but every Legal, Compliance, or Procurement professional
who has worked at a fast-growing company will recognize the shape of each one:

- **A bad liability clause slips through.** A SaaS vendor's standard contract caps *their* liability
  at one month of fees but leaves the customer's liability uncapped — a common, easy-to-miss asymmetry
  buried in section 14 of an attachment nobody read past the pricing table. Legal reviewed the
  commercial terms in a rush before a deal deadline, focused on price and term length, and the
  liability asymmetry was never specifically checked because there was no standing rule forcing that
  check — it depended on whichever reviewer happened to think to look. Eighteen months later, an
  outage caused by that vendor causes real damage, and the company discovers it has no recourse and no
  cap protecting it, because nobody was ever specifically responsible for confirming liability terms
  before signature.
- **A vendor processing personal data has no DPA, and nobody catches it until an audit.** A customer
  support tooling vendor is onboarded by a support team lead directly, with Procurement looped in only
  to process payment. The tool ingests customer names, emails, and support conversation content — squarely
  personal data under LGPD — but nobody classified the engagement as "processes personal data" at
  intake, so the standing rule requiring a DPA before such a vendor goes live never fires, because
  nobody asked the triggering question. The gap surfaces a year later during a customer's own vendor
  security questionnaire, or worse, during a regulator's inquiry after an unrelated incident — at
  which point the company must scramble to backfill a DPA for a vendor that has already been
  processing data for a year, and cannot represent to the regulator that it had a process catching this
  before the fact.
- **Nobody can reconstruct, eight months later, why a vendor was approved.** A mid-size outsourcing
  vendor is approved after "Legal looked at it and it seemed fine" — a decision that lived entirely in
  a Slack thread and one reviewer's memory. Eight months later, that vendor is involved in a data
  incident, and the company's own leadership, its cyber insurer, and eventually outside counsel all
  ask the same question: what exactly was reviewed, what red flags (if any) were identified and
  accepted, and who signed off on accepting them? The honest answer is "someone probably looked at it,"
  which is not a defensible answer to an insurer investigating a claim, a regulator investigating a
  breach, or a board investigating why due diligence failed — and by this point the original reviewer
  may have left the company, and the Slack thread may have rolled off retention.
- **Auto-renewal traps fire silently.** A contract with a 90-day advance-notice auto-renewal clause is
  filed away after signature with no tracked reminder anywhere except, in the best case, a calendar
  invite on the original negotiator's calendar — who has since changed roles. The renewal window
  passes unnoticed, the company is locked into another 12-month term on terms it no longer wants, and
  the failure is invisible until the next invoice arrives.
- **Duplicate and inconsistent vendor risk decisions.** Two different teams, unaware of each other,
  independently onboard the same vendor (or two subsidiaries of the same vendor) under different
  terms and with different levels of scrutiny, because there is no shared, queryable record of "have
  we already evaluated this supplier, and what did we decide."

## Why this does not scale, and why it is not merely an inconvenience

At one or two contracts a month, a diligent Legal and Compliance team can absorb this manually — every
company survives its first few years this way. The problem is structural, not a matter of individual
competence: manual, memory-dependent coordination across six functions has a throughput ceiling, and
a growing company's procurement volume crosses that ceiling long before it has the headcount to hire
a dedicated cross-functional review team for every vendor. Past that point, the company faces an
unpleasant choice it usually doesn't realize it's making: either slow down procurement to match the
manual review capacity (a real competitive cost), or let review quality silently degrade as volume
rises (the far more common outcome, and the one that produces the failures above). Both outcomes are
avoidable — not by hiring more reviewers, but by making the review process itself systematic,
consistent, and evidenced, which is what JuriSense Gate is built to do (see
`docs/00-project/solution.md`).
