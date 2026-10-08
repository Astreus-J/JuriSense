import type { LucideIcon } from "lucide-react";
import { Anchor, BrainCircuit, FileSearch, Gavel, History, Truck, Users, Workflow } from "lucide-react";
import type { LandingContent } from "@/lib/landing-content";
import SectionTitle from "./SectionTitle";

const ICONS: Record<string, LucideIcon> = {
  truck: Truck,
  "file-search": FileSearch,
  gavel: Gavel,
  workflow: Workflow,
  users: Users,
  history: History,
  "brain-circuit": BrainCircuit,
  anchor: Anchor,
};

/**
 * The first four cards follow the actual product pipeline, in order, from
 * `docs/00-project/overview.md` (Supplier → Contract → Policy → Decision); the last four cover
 * trust/governance (Approval, Audit, the AI boundary, Blockchain evidence). The "01–04" index
 * and the group labels make that narrative explicit instead of presenting all eight as an
 * unordered feature dump.
 */
export default function Features({ content }: { content: LandingContent }) {
  const pipeline = content.features.items.slice(0, 4);
  const trust = content.features.items.slice(4);

  return (
    <section id="features" className="mx-auto max-w-7xl scroll-mt-20 px-4 py-20 sm:px-6 lg:px-8">
      <SectionTitle
        eyebrow={content.features.eyebrow}
        title={content.features.title}
        subtitle={content.features.subtitle}
      />

      <div className="mt-14 space-y-12">
        <FeatureGroup label={content.features.groupPipeline} items={pipeline} startIndex={0} />
        <FeatureGroup label={content.features.groupTrust} items={trust} startIndex={4} />
      </div>
    </section>
  );
}

function FeatureGroup({
  label,
  items,
  startIndex,
}: {
  label: string;
  items: LandingContent["features"]["items"];
  startIndex: number;
}) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">{label}</h3>
      <div className="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((feature, i) => {
          const Icon = ICONS[feature.icon] ?? Gavel;
          const index = startIndex + i + 1;
          return (
            <div
              key={feature.title}
              className="group relative rounded-xl border border-slate-200 bg-white p-6 transition-all hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-lg"
            >
              <div className="flex items-center justify-between">
                <div className="flex size-11 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-blue-600 group-hover:border-blue-200 group-hover:bg-blue-50">
                  <Icon className="size-5" aria-hidden="true" />
                </div>
                <span className="font-mono text-xs text-slate-300">{String(index).padStart(2, "0")}</span>
              </div>
              <h4 className="mt-4 font-semibold text-slate-900">{feature.title}</h4>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{feature.description}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
