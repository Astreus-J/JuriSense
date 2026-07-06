import { faqs } from "@/lib/landing-data";
import SectionTitle from "./SectionTitle";

export default function Faq() {
  return (
    <section id="faq" className="py-20 bg-slate-50">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <SectionTitle title="Perguntas frequentes" subtitle="Tire suas dúvidas sobre o JuriSense" />
        <div className="mt-12 space-y-3">
          {faqs.map((faq) => (
            <details
              key={faq.question}
              className="group rounded-xl border border-gray-200 bg-white p-5 open:shadow-md transition-shadow"
            >
              <summary className="flex items-center justify-between cursor-pointer list-none font-medium text-gray-900">
                {faq.question}
                <span className="ml-4 text-gray-400 transition-transform group-open:rotate-45 text-xl leading-none">
                  +
                </span>
              </summary>
              <p className="mt-3 text-gray-600 leading-relaxed">{faq.answer}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
