import { Check, Info } from "lucide-react";
import { contact, type LandingContent, type Plan } from "@/lib/landing-content";
import { primaryButton, secondaryButton } from "./buttonStyles";
import SectionTitle from "./SectionTitle";

/** Approved launch catalog; subscriptions are arranged through the sales contact. */
export default function Plans({ content }: { content: LandingContent }) {
  const { plans } = content;

  return (
    <section id="pricing" className="mx-auto max-w-7xl scroll-mt-20 px-4 py-20 sm:px-6 lg:px-8">
      <SectionTitle eyebrow={content.nav.pricing} title={plans.title} subtitle={plans.subtitle} />

      <div className="mx-auto mt-8 flex max-w-2xl items-start gap-3 rounded-xl border border-blue-100 bg-blue-50/60 p-4 text-sm text-blue-900">
        <Info className="mt-0.5 size-4 shrink-0 text-blue-600" aria-hidden="true" />
        <p>{plans.pricingNote}</p>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        {plans.items.map((plan) => (
          <PlanCard key={plan.name} plan={plan} highlightedBadge={plans.highlightedBadge} />
        ))}
      </div>

      <div className="mt-12 rounded-2xl border border-slate-200 bg-landing-band p-8">
        <h3 className="text-center font-semibold text-slate-900">{plans.includedTitle}</h3>
        <ul className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {plans.included.map((item) => (
            <li key={item} className="flex items-start gap-2 text-sm text-slate-700">
              <Check className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden="true" />
              {item}
            </li>
          ))}
        </ul>
        <p className="mt-6 text-center text-sm text-slate-500">{plans.footnote}</p>
      </div>
    </section>
  );
}

function PlanCard({
  plan,
  highlightedBadge,
}: {
  plan: Plan;
  highlightedBadge: string;
}) {
  return (
    <div
      className={`relative flex flex-col rounded-2xl border bg-white p-6 ${
        plan.highlighted
          ? "border-blue-600 shadow-xl ring-1 ring-blue-600 lg:-translate-y-2"
          : "border-slate-200 shadow-sm"
      }`}
    >
      {plan.highlighted && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-blue-600 px-3 py-1 text-xs font-semibold text-white">
          {highlightedBadge}
        </span>
      )}

      <h3 className="text-lg font-bold text-slate-900">{plan.name}</h3>
      <p className="mt-1 min-h-10 text-sm text-slate-500">{plan.audience}</p>

      <div className="mt-5 min-h-24 border-b border-slate-100 pb-5">
        <p className="flex flex-wrap items-baseline gap-x-1">
          <span className="text-3xl font-bold tracking-tight text-slate-900">{plan.price}</span>
          {plan.period && <span className="text-sm text-slate-500">{plan.period}</span>}
        </p>
        <p className="mt-2 text-xs leading-relaxed text-slate-500">{plan.annual}</p>
      </div>

      <ul className="mt-6 flex-1 space-y-3">
        {plan.limits.map((limit) => (
          <li key={limit} className="flex items-start gap-2 text-sm text-slate-700">
            <Check className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden="true" />
            {limit}
          </li>
        ))}
      </ul>

      <a
        href={contact.whatsapp}
        target="_blank"
        rel="noopener noreferrer"
        className={plan.highlighted ? primaryButton("md", "mt-6 w-full") : secondaryButton("md", "mt-6 w-full")}
      >
        {plan.cta}
      </a>
    </div>
  );
}
