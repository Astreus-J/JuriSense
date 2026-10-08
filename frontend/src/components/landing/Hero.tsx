import { ArrowRight, FileSearch, Gavel, Scale, ShieldCheck, Sparkles, Zap } from "lucide-react";
import { contact, type LandingContent } from "@/lib/landing-content";
import { primaryButton, secondaryButton } from "./buttonStyles";

const TRUST_ICONS = { shield: ShieldCheck, bolt: Zap, sparkles: Sparkles };

const OUTCOME_STYLES: Record<"review" | "approve", string> = {
  review: "bg-amber-500 text-white",
  approve: "bg-emerald-600 text-white",
};

export default function Hero({ content }: { content: LandingContent }) {
  const { hero } = content;
  const { mockup } = hero;

  return (
    <section id="hero" className="relative overflow-hidden">
      {/* Faint brand texture: a soft radial wash plus a few hairline strokes, echoing the
          logo's node-and-line motif without becoming decorative clutter. Pure CSS, no asset. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(60%_50%_at_80%_-10%,rgba(37,99,235,0.08),transparent),radial-gradient(40%_35%_at_0%_10%,rgba(8,145,178,0.07),transparent)]"
      />

      <div className="mx-auto grid max-w-7xl grid-cols-1 items-center gap-16 px-4 py-16 sm:px-6 lg:px-8 lg:py-24 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm">
            <Sparkles className="size-4 text-blue-600" aria-hidden="true" />
            <span className="font-medium text-blue-700">{hero.badge}</span>
          </div>

          <h1 className="mt-6 text-balance text-5xl font-bold leading-[1.08] tracking-tight text-slate-900 lg:text-6xl">
            {hero.headlinePrefix}
            <span className="text-cyan-600">{hero.headlineAccent}</span>
            {hero.headlineSuffix}
          </h1>

          <p className="mt-6 max-w-xl text-xl leading-relaxed text-slate-600">{hero.subtext}</p>

          <div className="mt-8 flex flex-wrap gap-4">
            <a
              href={contact.whatsapp}
              target="_blank"
              rel="noopener noreferrer"
              className={primaryButton("lg")}
            >
              {hero.ctaPrimary}
              <ArrowRight className="size-4" aria-hidden="true" />
            </a>
            <a href="#how-it-works" className={secondaryButton("lg")}>
              {hero.ctaSecondary}
            </a>
          </div>

          <ul className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3 text-sm text-slate-600">
            {hero.trustBadges.map((badge) => {
              const Icon = TRUST_ICONS[badge.icon];
              return (
                <li key={badge.label} className="flex items-center gap-2">
                  <Icon className="size-4 text-emerald-600" aria-hidden="true" />
                  {badge.label}
                </li>
              );
            })}
          </ul>
        </div>

        {/* Product preview: a single, specific compliance decision shown with the full
            Risk / Evidence / Policy / Outcome chain (not generic dashboard stats) — the
            product's own "Evidence UX" principle applied to its first impression. */}
        <div className="relative">
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_24px_60px_-20px_rgba(15,23,42,0.25)]">
            <div className="flex items-center gap-3 border-b border-slate-200 bg-slate-50 px-4 py-2.5">
              <div className="flex gap-1.5">
                <div className="size-2.5 rounded-full bg-red-400" />
                <div className="size-2.5 rounded-full bg-amber-400" />
                <div className="size-2.5 rounded-full bg-emerald-400" />
              </div>
              <div className="flex-1 text-center text-xs font-medium text-slate-500">app.jurisense.com</div>
              <div className="w-8" />
            </div>

            <div className="space-y-4 p-5">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {mockup.sectionLabel}
                </p>
                <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-700">
                  <span className="relative flex size-2">
                    <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75 motion-reduce:hidden" />
                    <span className="relative inline-flex size-2 rounded-full bg-emerald-500" />
                  </span>
                  {mockup.liveLabel}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 p-4">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-semibold text-slate-900">{mockup.primary.supplier}</p>
                  <span
                    className={`shrink-0 rounded-md px-2 py-1 text-[11px] font-bold tracking-wide ${OUTCOME_STYLES.review}`}
                  >
                    {mockup.primary.outcome}
                  </span>
                </div>

                <dl className="mt-3 space-y-2 text-xs">
                  <div className="flex items-start gap-2">
                    <Scale className="mt-0.5 size-3.5 shrink-0 text-amber-600" aria-hidden="true" />
                    <dt className="font-medium text-slate-500">{mockup.primary.riskLabel}</dt>
                    <dd className="text-slate-700">{mockup.primary.risk}</dd>
                  </div>
                  <div className="flex items-start gap-2">
                    <FileSearch className="mt-0.5 size-3.5 shrink-0 text-slate-400" aria-hidden="true" />
                    <dt className="font-medium text-slate-500">{mockup.primary.evidenceLabel}</dt>
                    <dd className="text-slate-700">{mockup.primary.evidence}</dd>
                  </div>
                  <div className="flex items-start gap-2">
                    <Gavel className="mt-0.5 size-3.5 shrink-0 text-slate-400" aria-hidden="true" />
                    <dt className="font-medium text-slate-500">{mockup.primary.policyLabel}</dt>
                    <dd className="font-mono text-slate-700">{mockup.primary.policy}</dd>
                  </div>
                </dl>
              </div>

              <div className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900">{mockup.secondary.supplier}</p>
                  <p className="truncate text-xs text-slate-500">{mockup.secondary.note}</p>
                </div>
                <span
                  className={`ml-3 shrink-0 rounded-md px-2 py-1 text-[11px] font-bold tracking-wide ${OUTCOME_STYLES.approve}`}
                >
                  {mockup.secondary.outcome}
                </span>
              </div>

              <div className="flex items-center justify-between border-t border-slate-100 pt-3">
                <div className="flex gap-4">
                  {mockup.stats.map((stat) => (
                    <div key={stat.label} className="text-left">
                      <p className="text-sm font-bold tabular-nums text-slate-900">{stat.value}</p>
                      <p className="text-[11px] text-slate-500">{stat.label}</p>
                    </div>
                  ))}
                </div>
                <span className="text-xs font-semibold text-emerald-600">{mockup.monthDelta}</span>
              </div>
            </div>
          </div>

          <div className="absolute -right-3 -top-3 rounded-xl border border-slate-200 bg-white p-2.5 text-cyan-600 shadow-lg">
            <Sparkles className="size-5" aria-hidden="true" />
          </div>
        </div>
      </div>
    </section>
  );
}
