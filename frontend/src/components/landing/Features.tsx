import type { LandingContent } from "@/lib/landing-content";
import SectionTitle from "./SectionTitle";
import { FeatureIcon } from "./Icons";

export default function Features({ content }: { content: LandingContent }) {
  return (
    <section id="features" className="py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <SectionTitle title={content.features.title} subtitle={content.features.subtitle} />
      <div className="mt-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {content.features.items.map((feature) => (
          <div
            key={feature.title}
            className="p-6 rounded-xl border border-gray-200 bg-white hover:shadow-lg hover:border-blue-200 transition-all"
          >
            <div
              className={`w-11 h-11 rounded-lg flex items-center justify-center mb-4 ${feature.accent}`}
            >
              <FeatureIcon name={feature.icon} className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">{feature.title}</h3>
            <p className="text-sm text-gray-600 leading-relaxed">{feature.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
