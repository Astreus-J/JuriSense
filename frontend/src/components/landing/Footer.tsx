import Image from "next/image";
import { contact } from "@/lib/landing-data";

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="w-full bg-slate-900 text-slate-400 py-12 px-6 border-t border-slate-800">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-12">
          {/* Logo e descrição */}
          <div className="space-y-5">
            <div className="flex items-center gap-2 text-white text-2xl font-bold">
              <Image
                src="/img/logo.jpg"
                alt="Logo JuriSense"
                width={48}
                height={48}
                className="rounded-xl"
              />
              <span>JuriSense</span>
            </div>
            <p>A plataforma completa para gestão jurídica inteligente.</p>
            <div className="flex gap-3">
              <a
                href={contact.social.linkedin}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-2 bg-slate-800 rounded-xl text-white hover:bg-slate-700 text-sm"
              >
                LinkedIn
              </a>
              <a
                href={contact.social.instagram}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-2 bg-slate-800 rounded-xl text-white hover:bg-slate-700 text-sm"
              >
                Instagram
              </a>
              <a
                href={contact.social.twitter}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-2 bg-slate-800 rounded-xl text-white hover:bg-slate-700 text-sm"
              >
                X
              </a>
            </div>
          </div>

          {/* Produto */}
          <div>
            <h3 className="text-white font-semibold mb-5 text-lg">Produto</h3>
            <ul className="space-y-3">
              <li>
                <a href="#funcionalidades" className="hover:text-white transition-colors">
                  Funcionalidades
                </a>
              </li>
              <li>
                <a href="#precos" className="hover:text-white transition-colors">
                  Preços
                </a>
              </li>
              <li>
                <a href="#como-funciona" className="hover:text-white transition-colors">
                  Como funciona
                </a>
              </li>
            </ul>
          </div>

          {/* Recursos */}
          <div>
            <h3 className="text-white font-semibold mb-5 text-lg">Recursos</h3>
            <ul className="space-y-3">
              <li>
                <a href="#faq" className="hover:text-white transition-colors">
                  FAQ / Ajuda
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Privacidade
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Termos
                </a>
              </li>
            </ul>
          </div>

          {/* Contato */}
          <div>
            <h3 className="text-white font-semibold mb-5 text-lg">Contato</h3>
            <ul className="space-y-3">
              <li className="break-all">{contact.email}</li>
              <li>{contact.phone}</li>
              <li>{contact.location}</li>
            </ul>
          </div>
        </div>

        <div className="pt-8 border-t border-slate-800 flex flex-col md:flex-row justify-between gap-4 text-sm">
          <p>© {currentYear} JuriSense. Todos os direitos reservados.</p>
          <div className="flex gap-6">
            <a href="#" className="hover:text-white transition-colors">
              Termos
            </a>
            <a href="#" className="hover:text-white transition-colors">
              Privacidade
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
