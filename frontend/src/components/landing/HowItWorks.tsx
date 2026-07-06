import { steps } from "@/lib/landing-data";
import SectionTitle from "./SectionTitle";

export default function HowItWorks() {
  return (
    <section id="como-funciona" className="py-20 bg-slate-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <SectionTitle
          title="Comece em 5 passos simples"
          subtitle="Da criação da conta à operação completa em minutos"
        />
        <div className="mt-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6">
          {steps.map((item) => (
            <div key={item.step} className="flex flex-col items-center text-center p-6">
              <div className="w-12 h-12 rounded-full bg-blue-600 text-white flex items-center justify-center text-lg font-bold mb-4">
                {item.step}
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">{item.title}</h3>
              <p className="text-sm text-gray-600">{item.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
