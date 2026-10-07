import { contact, type LandingContent } from "@/lib/landing-content";
import { ArrowRightIcon, BoltIcon, ShieldIcon, SparklesIcon } from "./Icons";

const trustIcons = { shield: ShieldIcon, bolt: BoltIcon, sparkles: SparklesIcon };

export default function Hero({ content }: { content: LandingContent }) {
  const { hero } = content;

  return (
    <section id="hero" className="py-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
        <div className="space-y-8">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-full text-sm">
            <SparklesIcon className="w-4 h-4 text-blue-600" />
            <span className="font-medium text-blue-700">{hero.badge}</span>
          </div>

          <h1 className="text-5xl lg:text-6xl font-bold text-gray-900 leading-[1.1]">
            {hero.headlinePrefix}
            <span className="text-blue-600">{hero.headlineAccent}</span>
            {hero.headlineSuffix}
          </h1>

          <p className="text-xl text-gray-600 leading-relaxed max-w-xl">{hero.subtext}</p>

          <div className="flex flex-wrap gap-4">
            <a
              href={contact.whatsapp}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3.5 text-base font-semibold text-white hover:bg-blue-700 transition-colors"
            >
              {hero.ctaPrimary}
              <ArrowRightIcon className="w-4 h-4" />
            </a>
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-6 py-3.5 text-base font-semibold text-gray-700 hover:border-blue-600 hover:text-blue-600 transition-colors"
            >
              {hero.ctaSecondary}
            </a>
          </div>

          <div className="flex flex-wrap items-center gap-x-6 gap-y-3 pt-4 text-sm">
            {hero.trustBadges.map((badge) => {
              const Icon = trustIcons[badge.icon];
              return (
                <div key={badge.label} className="flex items-center gap-2">
                  <Icon className="w-4 h-4 text-green-700" />
                  <span className="text-gray-700">{badge.label}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Illustrative mockup of a compliance decision */}
        <div className="relative lg:ml-8">
          <div className="bg-white rounded-xl shadow-2xl overflow-hidden border border-gray-200">
            <div className="bg-gray-50 px-4 py-2.5 flex items-center gap-3 border-b border-gray-200">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                <div className="w-3 h-3 rounded-full bg-green-500" />
              </div>
              <div className="flex-1 text-center text-xs text-gray-500 font-medium">
                app.jurisense.com
              </div>
              <div className="w-8" />
            </div>

            <div className="p-5 bg-white space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-gray-500 mb-0.5">{hero.mockup.sectionLabel}</p>
                  <h3 className="text-base font-semibold text-gray-900">{hero.mockup.title}</h3>
                </div>
                <span className="text-xs text-green-600 font-semibold">
                  {hero.mockup.monthDelta}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2.5">
                <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                  <div className="text-2xl font-bold text-gray-900 mb-0.5">
                    {hero.mockup.stats[0].value}
                  </div>
                  <div className="text-xs text-gray-600">{hero.mockup.stats[0].label}</div>
                </div>
                <div className="bg-teal-50 rounded-lg p-3 border border-teal-100">
                  <div className="text-2xl font-bold text-teal-700 mb-0.5">
                    {hero.mockup.stats[1].value}
                  </div>
                  <div className="text-xs text-gray-600">{hero.mockup.stats[1].label}</div>
                </div>
                <div className="bg-yellow-50 rounded-lg p-3 border border-yellow-100">
                  <div className="text-2xl font-bold text-yellow-700 mb-0.5">
                    {hero.mockup.stats[2].value}
                  </div>
                  <div className="text-xs text-gray-600">{hero.mockup.stats[2].label}</div>
                </div>
              </div>

              <div className="space-y-2.5 pt-1">
                <div className="flex items-start gap-2.5 p-2.5 bg-amber-50 rounded-lg border border-amber-100">
                  <span className="shrink-0 rounded-full bg-amber-500 px-2 py-0.5 text-[10px] font-bold text-white mt-0.5">
                    {hero.mockup.review.status}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-900">{hero.mockup.review.name}</p>
                    <p className="text-xs text-gray-500">{hero.mockup.review.note}</p>
                  </div>
                </div>
                <div className="flex items-start gap-2.5 p-2.5 bg-green-50 rounded-lg border border-green-100">
                  <span className="shrink-0 rounded-full bg-green-600 px-2 py-0.5 text-[10px] font-bold text-white mt-0.5">
                    {hero.mockup.approved.status}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-900">
                      {hero.mockup.approved.name}
                    </p>
                    <p className="text-xs text-gray-500">{hero.mockup.approved.note}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 pt-1 pl-1">
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                  <span className="text-xs text-gray-600">{hero.mockup.engineRunning}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="absolute -top-3 -right-3 bg-white rounded-lg shadow-lg p-2 border border-gray-200 text-blue-600">
            <SparklesIcon className="w-5 h-5" />
          </div>
        </div>
      </div>
    </section>
  );
}
