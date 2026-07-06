export default function SectionTitle({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="text-center space-y-3">
      <h2 className="text-3xl md:text-4xl font-bold text-gray-900">{title}</h2>
      <p className="text-lg text-gray-600 max-w-2xl mx-auto">{subtitle}</p>
    </div>
  );
}
