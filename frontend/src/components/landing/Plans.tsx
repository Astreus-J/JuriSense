import { contact, type LandingContent } from "@/lib/landing-content";
import SectionTitle from "./SectionTitle";
import { CheckIcon } from "./Icons";

export default function Plans({ content }: { content: LandingContent }) {
  return (
    <section id="pricing" className="py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <SectionTitle title={content.plans.title} subtitle={content.plans.subtitle} />

      <div className="mt-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {content.plans.items.map((plan) => (
          <div
            key={plan.name}
            className={`relative flex flex-col p-6 rounded-2xl border bg-white ${
              plan.highlighted
                ? "border-blue-600 shadow-xl ring-1 ring-blue-600"
                : "border-gray-200 shadow-sm"
            }`}
          >
            {plan.highlighted && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
                {content.plans.highlightedBadge}
              </span>
            )}

            <h3 className="text-lg font-bold text-gray-900">{plan.name}</h3>
            <p className="text-sm text-gray-500 mt-1 min-h-10">{plan.audience}</p>

            <div className="mt-4 flex items-baseline gap-1">
              <span className="text-3xl font-bold text-gray-900">{plan.price}</span>
              <span className="text-gray-500 text-sm">{plan.priceNote}</span>
            </div>

            <ul className="mt-6 space-y-3 flex-1">
              {plan.limits.map((limit) => (
                <li key={limit} className="flex items-start gap-2 text-sm text-gray-700">
                  <CheckIcon className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                  {limit}
                </li>
              ))}
            </ul>

            <a
              href={contact.whatsapp}
              target="_blank"
              rel="noopener noreferrer"
              className={`mt-6 inline-flex justify-center rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors ${
                plan.highlighted
                  ? "bg-blue-600 text-white hover:bg-blue-700"
                  : "border border-gray-300 text-gray-700 hover:border-blue-600 hover:text-blue-600"
              }`}
            >
              {plan.cta}
            </a>
          </div>
        ))}
      </div>

      <div className="mt-12 p-8 rounded-2xl bg-slate-50 border border-gray-200">
        <h3 className="font-semibold text-gray-900 mb-4 text-center">
          {content.plans.includedTitle}
        </h3>
        <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {content.plans.included.map((item) => (
            <li key={item} className="flex items-start gap-2 text-sm text-gray-700">
              <CheckIcon className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
              {item}
            </li>
          ))}
        </ul>
        <p className="text-center text-sm text-gray-500 mt-6">{content.plans.footnote}</p>
      </div>
    </section>
  );
}
