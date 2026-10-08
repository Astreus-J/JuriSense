/**
 * Shared section heading: optional small uppercase eyebrow, headline, one-line subtitle.
 * Centralizing this (rather than repeating the type scale in every section) is what keeps the
 * seven content sections reading as one coherent system instead of independently-styled blocks.
 */
export default function SectionTitle({
  eyebrow,
  title,
  subtitle,
  align = "center",
}: {
  eyebrow?: string;
  title: string;
  subtitle: string;
  align?: "center" | "left";
}) {
  const isCenter = align === "center";
  return (
    <div className={isCenter ? "mx-auto max-w-2xl text-center" : "max-w-2xl"}>
      {eyebrow && (
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">
          {eyebrow}
        </p>
      )}
      <h2 className="text-balance text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">
        {title}
      </h2>
      <p className="mt-3 text-lg leading-relaxed text-slate-600">{subtitle}</p>
    </div>
  );
}
