// Narration for the pitch deck (`JuriSense Gate — Legal Hack 2026 (2).pdf`, 12 slides).
// Text is adapted from docs/08-hackathon/pitch.md (the canonical pitch narrative) into
// one spoken segment per slide, in deck order. Same voice as the demo video narration
// (Gemini TTS, "Kore") -- see gen_pitch_audio.py.

module.exports = [
  {
    id: "01-problem-intro",
    slide: 1,
    narration:
      "Every growing company buys from outside vendors constantly: SaaS tools, consultancies, " +
      "cloud providers, outsourced teams. Before signing, someone is supposed to check: is this " +
      "supplier real and in good standing? Are they on a sanctions list? Does the contract need a " +
      "data processing agreement? Is the liability clause reasonable? Is the value big enough to " +
      "need Legal's sign off? Six months later, someone asks why a vendor was approved, and most " +
      "companies can't answer.",
  },
  {
    id: "02-five-checks",
    slide: 2,
    narration:
      "That's five checks, every time: is the supplier legitimate, are they sanctioned, do we need " +
      "a data processing agreement, is the liability clause reasonable, is the contract value above " +
      "our approval threshold. Each one usually belongs to a different team.",
  },
  {
    id: "03-no-record",
    slide: 3,
    narration:
      "In practice, those checks happen across Procurement, Legal, Compliance, Finance, Security, " +
      "and Privacy, coordinated by email threads and spreadsheets, with no single reproducible " +
      "record of why a vendor was approved. Ask why six months later, and the honest answer is " +
      "usually someone probably looked at it. That's not a process, it's legal liability waiting to " +
      "surface at the worst possible time, and it doesn't scale past a handful of contracts a month.",
  },
  {
    id: "04-one-workflow",
    slide: 4,
    narration:
      "JuriSense Gate turns that fragmented, manual process into one pipeline: supplier " +
      "verification against official sources, A.I. structured contract extraction, evaluation " +
      "against the company's own executable policy rules, a deterministic Approve, Review, or " +
      "Block decision, always with why, evidence, policy, source, risk, required action, and " +
      "approver, never a bare status, routed human approval when a rule requires it, and a " +
      "Decision Passport that packages the entire evidentiary trail.",
  },
  {
    id: "05-ai-vs-rules",
    slide: 5,
    narration:
      "A.I. reads and extracts. It never decides. The policy engine's aggregation is simple enough " +
      "to explain in one sentence: any Block wins. And every decision is reproducible months or " +
      "years later, from its recorded rule evaluations and the exact policy version that was used.",
  },
  {
    id: "06-demo-recap",
    slide: 6,
    narration:
      "Here's what that looks like in the working prototype. Acme reviews CloudDocs' contract: four " +
      "hundred eighty thousand reais a year, unlimited liability, personal data with no D.P.A. " +
      "Blocked. CloudDocs fixes it: D.P.A. added, liability capped. Now it's Review, because the " +
      "value alone still needs Legal's sign off. Legal approves it, with a written rationale, and " +
      "version one stays exactly as it was, in the history.",
  },
  {
    id: "07-three-pieces",
    slide: 7,
    narration:
      "Three pieces make this practical now, and none of them existed together five years ago. A.I. " +
      "finally makes structured extraction from real, messy contracts fast and cheap enough to run " +
      "on every vendor. Policy can be written as code: versioned, executable, and re-run. And " +
      "evidence can be made verifiable, a hash anchored where a third party can check it, without " +
      "trusting our database.",
  },
  {
    id: "08-law-finance-compliance",
    slide: 8,
    narration:
      "Law, Finance, and Compliance all feed into the same decision: D.P.A. and liability terms " +
      "route to Legal, value thresholds trigger Finance approval, supplier checks and the audit " +
      "trail serve Compliance. That's this event's stated theme, and it's exactly the intersection " +
      "JuriSense Gate sits at.",
  },
  {
    id: "09-brazil-first",
    slide: 9,
    narration:
      "We are not building a generic global tool and hoping Brazil is an afterthought. We're " +
      "building Brazil first, on purpose. C.N.P.J. based supplier identity, Brazilian sanctions and " +
      "registry sources, and L.G.P.D. compliance are first class from day one, starting with tech " +
      "companies around fifty to a thousand employees that have real procurement volume and no " +
      "dedicated tooling for this today.",
  },
  {
    id: "10-traceable",
    slide: 10,
    narration:
      "Every decision produces a Decision Passport: the outcome, the exact policy version used, " +
      "every rule's evidence, the documents with their hashes, and the approver with their " +
      "rationale. Then a hash of all of it is anchored on chain. Tamper evident means it proves the " +
      "evidence hasn't changed, not that the decision itself was correct, and no raw data ever goes " +
      "on chain, only the hash.",
  },
  {
    id: "11-the-ask",
    slide: 11,
    narration:
      "So here's our ask. Examine our decision logic and evidence model, they're built to hold up " +
      "under real questioning. Give us your hardest feedback. And if you know a Brazilian tech " +
      "company that feels this pain today, introduce us. This isn't a hackathon project that " +
      "disappears in December. It's milestone one of a real company.",
  },
  {
    id: "12-closing",
    slide: 12,
    narration:
      "Turn contracts, supplier data, and company policies into auditable compliance decisions. " +
      "That's JuriSense Gate.",
  },
];
