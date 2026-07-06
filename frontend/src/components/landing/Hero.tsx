import { contact } from "@/lib/landing-data";
import { ArrowRightIcon, BellIcon, BoltIcon, CardIcon, CheckIcon, ShieldIcon, SparklesIcon } from "./Icons";

const trustBadges = [
  { icon: ShieldIcon, label: "LGPD Compliant" },
  { icon: CheckIcon, label: "Criptografia AES-256" },
  { icon: BoltIcon, label: "99.9% Uptime" },
];

export default function Hero() {
  return (
    <section id="hero" className="py-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
        {/* Conteúdo à esquerda */}
        <div className="space-y-8">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-full text-sm">
            <SparklesIcon className="w-4 h-4 text-blue-600" />
            <span className="font-medium text-blue-700">IA Jurídica treinada para o direito brasileiro</span>
          </div>

          <h1 className="text-5xl lg:text-6xl font-bold text-gray-900 leading-[1.1]">
            Gerencie seu escritório jurídico com{" "}
            <span className="text-blue-600">inteligência</span>, agilidade e segurança
          </h1>

          <p className="text-xl text-gray-600 leading-relaxed max-w-xl">
            Processos, clientes, IA e financeiro em um só lugar. A plataforma completa
            para escritórios de advocacia modernos.
          </p>

          <div className="flex flex-wrap gap-4">
            <a
              href={contact.whatsapp}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3.5 text-base font-semibold text-white hover:bg-blue-700 transition-colors"
            >
              Testar grátis por 14 dias
              <ArrowRightIcon className="w-4 h-4" />
            </a>
            <a
              href="#precos"
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-6 py-3.5 text-base font-semibold text-gray-700 hover:border-blue-600 hover:text-blue-600 transition-colors"
            >
              Ver planos
            </a>
          </div>

          <div className="flex flex-wrap items-center gap-x-6 gap-y-3 pt-4 text-sm">
            {trustBadges.map(({ icon: Icon, label }) => (
              <div key={label} className="flex items-center gap-2">
                <Icon className="w-4 h-4 text-green-700" />
                <span className="text-gray-700">{label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Mockup do dashboard à direita */}
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
                  <p className="text-xs text-gray-500 mb-0.5">Dashboard</p>
                  <h3 className="text-base font-semibold text-gray-900">Bem-vindo, Dr. Carlos</h3>
                </div>
                <span className="text-xs text-green-600 font-semibold">+12% este mês</span>
              </div>

              <div className="grid grid-cols-3 gap-2.5">
                <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                  <div className="text-2xl font-bold text-gray-900 mb-0.5">247</div>
                  <div className="text-xs text-gray-600">Processos</div>
                </div>
                <div className="bg-teal-50 rounded-lg p-3 border border-teal-100">
                  <div className="text-2xl font-bold text-teal-700 mb-0.5">89</div>
                  <div className="text-xs text-gray-600">Clientes</div>
                </div>
                <div className="bg-yellow-50 rounded-lg p-3 border border-yellow-100">
                  <div className="text-2xl font-bold text-yellow-700 mb-0.5">5</div>
                  <div className="text-xs text-gray-600">Prazos hoje</div>
                </div>
              </div>

              <div className="space-y-2.5 pt-1">
                <div className="flex items-start gap-2.5 p-2.5 bg-gray-50 rounded-lg border border-gray-100">
                  <div className="w-6 h-6 rounded bg-blue-100 text-blue-700 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <BellIcon className="w-3.5 h-3.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-900">Audiência amanhã às 14h</p>
                    <p className="text-xs text-gray-500">Processo 0001234-56.2024</p>
                  </div>
                </div>
                <div className="flex items-start gap-2.5 p-2.5 bg-green-50 rounded-lg border border-green-100">
                  <div className="w-6 h-6 rounded bg-green-100 text-green-700 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <CardIcon className="w-3.5 h-3.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-900">Pagamento recebido</p>
                    <p className="text-xs text-gray-500">R$ 5.000,00 - Cliente Silva</p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 pt-1 pl-1">
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                  <span className="text-xs text-gray-600">IA ativa</span>
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
