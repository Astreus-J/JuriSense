/**
 * All landing-page copy, in three languages. English is the native/primary language (the
 * project-wide rule, CLAUDE.md: "everything is written in English... Portuguese exists only
 * as explicit, supported customer-facing i18n content" — this file is exactly that explicit
 * exception, plus Spanish for the same reason). `en` is served at `/` with no prefix;
 * `pt`/`es` are served at `/pt`/`/es` (see `src/app/[locale]/page.tsx`).
 *
 * Deliberately a plain, locale-keyed object rather than a next-intl/ICU message catalog:
 * the landing page is the ONLY part of the product being translated (the authenticated app,
 * `/login`, `/verify`, etc. stay English-only, per the project's own identifier/UI language
 * rule) and its content is a handful of structured arrays (features, plans, steps, FAQs), not
 * hundreds of independent short strings — a typed object is simpler to keep correct across
 * three languages side by side than a key-per-string catalog would be here.
 */

export type Locale = "en" | "pt" | "es";

export const LOCALES: Locale[] = ["en", "pt", "es"];
export const DEFAULT_LOCALE: Locale = "en";

export const LOCALE_LABELS: Record<Locale, string> = {
  en: "English",
  pt: "Português",
  es: "Español",
};

export interface Feature {
  title: string;
  description: string;
  icon: string; // key into Icons.tsx
  accent: string; // tailwind classes for the icon background
}

export interface Plan {
  name: string;
  audience: string;
  price: string;
  priceNote: string;
  highlighted?: boolean;
  limits: string[];
  cta: string;
}

export interface Step {
  step: number;
  title: string;
  description: string;
}

export interface Faq {
  question: string;
  answer: string;
}

export interface LandingContent {
  meta: { title: string; description: string };
  nav: {
    features: string;
    howItWorks: string;
    pricing: string;
    faq: string;
    login: string;
    talkToUs: string;
  };
  hero: {
    badge: string;
    headlinePrefix: string;
    headlineAccent: string;
    headlineSuffix: string;
    subtext: string;
    ctaPrimary: string;
    ctaSecondary: string;
    trustBadges: { icon: "shield" | "bolt" | "sparkles"; label: string }[];
    mockup: {
      sectionLabel: string;
      title: string;
      monthDelta: string;
      stats: { value: string; label: string }[];
      review: { status: string; name: string; note: string };
      approved: { status: string; name: string; note: string };
      engineRunning: string;
    };
  };
  features: { title: string; subtitle: string; items: Feature[] };
  howItWorks: { title: string; subtitle: string; steps: Step[] };
  plans: {
    title: string;
    subtitle: string;
    highlightedBadge: string;
    items: Plan[];
    includedTitle: string;
    included: string[];
    footnote: string;
  };
  faq: { title: string; subtitle: string; items: Faq[] };
  cta: { headline: string; subtext: string; button: string };
  footer: {
    tagline: string;
    productLabel: string;
    resourcesLabel: string;
    contactLabel: string;
    faqHelp: string;
    privacy: string;
    terms: string;
    rights: string;
  };
}

const en: LandingContent = {
  meta: {
    title: "JuriSense Gate — Vendor & Contract Compliance, With Evidence",
    description:
      "JuriSense Gate turns contracts, supplier data, and your company's own policy into auditable, explainable compliance decisions — with AI, an executable policy engine, and blockchain-anchored evidence.",
  },
  nav: {
    features: "Features",
    howItWorks: "How it works",
    pricing: "Pricing",
    faq: "FAQ",
    login: "Log in",
    talkToUs: "Talk to us",
  },
  hero: {
    badge: "Compliance engine for suppliers and contracts",
    headlinePrefix: "Know, with ",
    headlineAccent: "evidence",
    headlineSuffix: ", whether you can hire this supplier and sign this contract",
    subtext:
      "JuriSense Gate turns contracts, supplier data, and your company's own policy into auditable compliance decisions — with AI, an executable policy engine, and blockchain-anchored evidence.",
    ctaPrimary: "Schedule a conversation",
    ctaSecondary: "See how it works",
    trustBadges: [
      { icon: "shield", label: "LGPD by default" },
      { icon: "bolt", label: "AI never decides alone" },
      { icon: "sparkles", label: "Evidence verifiable on-chain" },
    ],
    mockup: {
      sectionLabel: "Compliance",
      title: "This week's reviews",
      monthDelta: "+12% this month",
      stats: [
        { value: "34", label: "Suppliers" },
        { value: "19", label: "Contracts" },
        { value: "3", label: "In review" },
      ],
      review: { status: "REVIEW", name: "SaaS Beta Ltd.", note: "Unlimited liability clause" },
      approved: { status: "APPROVE", name: "Delta Consulting", note: "Every policy rule passed" },
      engineRunning: "Policy engine running",
    },
  },
  features: {
    title: "Everything you need to approve suppliers and contracts with confidence",
    subtitle: "From verifying the supplier to blockchain-verifiable evidence — in one flow.",
    items: [
      {
        title: "Supplier Intelligence",
        description:
          "Verify suppliers automatically against official sources — registry status, sanctions/restriction lists — and keep an immutable history of every check.",
        icon: "card",
        accent: "bg-blue-100 text-blue-700",
      },
      {
        title: "Contract Intelligence",
        description:
          "Extract structured data from contracts in PDF, DOCX, or TXT: value, duration, liability, data-processing terms, and IP — with exact citations back to the source clause.",
        icon: "report",
        accent: "bg-indigo-100 text-indigo-700",
      },
      {
        title: "Executable Policy Engine",
        description:
          "Turn your company's own policy into versioned, deterministic rules — when X, then approve, review, or block. The rule is yours, not a model's judgment.",
        icon: "scale",
        accent: "bg-violet-100 text-violet-700",
      },
      {
        title: "Compliance & Risk Engine",
        description:
          "Combine supplier evidence, contract evidence, and policy rules into one explainable outcome: APPROVE, REVIEW, or BLOCK — always with the why.",
        icon: "chart",
        accent: "bg-cyan-100 text-cyan-700",
      },
      {
        title: "Routed Human Approval",
        description:
          "Every decision that needs review is routed automatically to the right role — Legal, Compliance, a director — as an auditable workflow, never a silent resolution.",
        icon: "users",
        accent: "bg-emerald-100 text-emerald-700",
      },
      {
        title: "Full Audit Trail",
        description:
          "Every state-changing action emits an immutable audit event. Nothing happens silently, and nothing gets lost over time.",
        icon: "bell",
        accent: "bg-rose-100 text-rose-700",
      },
      {
        title: "AI That Never Decides Alone",
        description:
          "AI extracts, classifies, and summarizes — always with document/page/clause provenance. It never approves or blocks on its own: that call always belongs to your policy.",
        icon: "sparkles",
        accent: "bg-amber-100 text-amber-700",
      },
      {
        title: "Blockchain-Verifiable Evidence",
        description:
          "Each decision's evidence package is hash-anchored on a public, tamper-evident network — so \"was this altered afterward?\" has an answer that doesn't depend on trusting JuriSense.",
        icon: "shield",
        accent: "bg-green-100 text-green-700",
      },
    ],
  },
  howItWorks: {
    title: "Get started in 5 steps",
    subtitle: "From the first conversation to full operation",
    steps: [
      {
        step: 1,
        title: "Talk to us",
        description: "See how JuriSense Gate fits your compliance process, with no commitment.",
      },
      {
        step: 2,
        title: "Configure your policy",
        description: "We work with you to encode your Legal/Compliance rules as executable policy.",
      },
      {
        step: 3,
        title: "Add suppliers and contracts",
        description: "Bring your real suppliers and contracts into the flow.",
      },
      {
        step: 4,
        title: "Get explainable decisions",
        description: "Every review comes back as APPROVE, REVIEW, or BLOCK — with the full why.",
      },
      {
        step: 5,
        title: "Audit whenever you need to",
        description: "Pull up the Decision Passport and its blockchain verification, even years later.",
      },
    ],
  },
  plans: {
    title: "Priced to your scale, not your feature list",
    subtitle: "Every tier shares the same compliance engine — the limits scale with your volume.",
    highlightedBadge: "Most popular",
    items: [
      {
        name: "Starter",
        audience: "50–150-employee companies starting a structured supplier-compliance process.",
        price: "Talk to us",
        priceNote: "",
        limits: [
          "One core policy",
          "Suppliers and contracts at starter volume",
          "Procurement + Legal/Compliance seats",
          "AI executions included",
          "No API access",
        ],
        cta: "Talk to us",
      },
      {
        name: "Business",
        audience: "Companies with a recurring supplier pipeline and more than one team involved.",
        price: "Talk to us",
        priceNote: "",
        highlighted: true,
        limits: [
          "Multiple concurrent policies",
          "Higher supplier/contract/AI limits",
          "More seats: Procurement, Legal, Compliance, Finance",
          "Basic integrations (Slack, email)",
          "Priority support",
        ],
        cta: "Talk to us",
      },
      {
        name: "Growth",
        audience: "More procurement-mature companies with multiple business units.",
        price: "Talk to us",
        priceNote: "",
        limits: [
          "Unlimited policies",
          "More automation — more decisions auto-approved, safely",
          "Early, rate-limited API access",
          "Expanded storage",
          "Faster support SLA",
        ],
        cta: "Talk to us",
      },
      {
        name: "Enterprise",
        audience: "Large companies and buyers with elevated regulatory and security requirements.",
        price: "Talk to us",
        priceNote: "",
        limits: [
          "Custom or unlimited limits",
          "SSO and advanced security/audit requirements",
          "Multiple jurisdiction/compliance packs",
          "Full API access",
          "Dedicated onboarding and support",
        ],
        cta: "Talk to us",
      },
    ],
    includedTitle: "Included in every plan",
    included: [
      "APPROVE / REVIEW / BLOCK decision engine",
      "A Decision Passport on every decision",
      "Immutable audit trail",
      "Supplier verification against official sources",
      "AI with provenance — never decides alone",
      "Blockchain-anchored evidence",
      "LGPD compliance by default",
      "Per-organization data isolation",
    ],
    footnote:
      "Every plan's exact limits are set in conversation with your team, based on your company's real supplier and contract volume.",
  },
  faq: {
    title: "Frequently asked questions",
    subtitle: "Answers about JuriSense Gate",
    items: [
      {
        question: "Is JuriSense Gate an ERP or a legal-practice-management tool?",
        answer:
          "No. JuriSense Gate doesn't replace your ERP or a CLM tool. It consumes supplier and contract data to produce a compliance decision — it doesn't manage purchase orders, invoicing, or the contract negotiation itself.",
      },
      {
        question: "Can JuriSense Gate's AI approve or block a supplier on its own?",
        answer:
          "No. AI extracts, classifies, and summarizes information — it never decides the compliance outcome. That's always your own policy's rules, configured by your Legal/Compliance team. This is a technical constraint of the product, not just a promise.",
      },
      {
        question: "What exactly gets written to the blockchain?",
        answer:
          "Only the hash of each decision's evidence package — never contract content, supplier data, or personal data. The blockchain only proves the evidence wasn't altered afterward, independent of JuriSense's own database.",
      },
      {
        question: "How does pricing work?",
        answer:
          "Plans scale with your volume of suppliers, contracts, and AI executions, not with feature access. Since the right limits depend on your real compliance volume, we set them in conversation with your team, not off a fixed table.",
      },
      {
        question: "How long does it take to get started?",
        answer:
          "After the first conversation, we configure your policy together with your team and you can start adding real suppliers and contracts right away. The exact timeline depends on how complex your initial policy is.",
      },
      {
        question: "Does JuriSense Gate replace my legal team's judgment?",
        answer:
          "No. JuriSense Gate executes the policy your own Legal/Compliance team defines and approves. It never provides legal advice and never substitutes for your lawyer's judgment.",
      },
      {
        question: "Is my data isolated from other companies using JuriSense Gate?",
        answer:
          "Yes. Every organization's data is isolated by default, and no confidential contract content or personal data is ever exposed publicly — not even on the blockchain, where only the hash is anchored.",
      },
      {
        question: "What happens when a policy or a contract changes after a decision?",
        answer:
          "JuriSense Gate automatically re-evaluates the decision when the policy changes or a new contract version appears, and keeps the full history — the old decision is never deleted, only superseded by a new one.",
      },
    ],
  },
  cta: {
    headline: "Ready for evidence, not guesswork, on every supplier decision?",
    subtext:
      "Talk to our team and see how JuriSense Gate fits your supplier and contract compliance process.",
    button: "Talk to us",
  },
  footer: {
    tagline: "Explainable, verifiable compliance decisions for suppliers and contracts.",
    productLabel: "Product",
    resourcesLabel: "Resources",
    contactLabel: "Contact",
    faqHelp: "FAQ / Help",
    privacy: "Privacy",
    terms: "Terms",
    rights: "All rights reserved.",
  },
};

const pt: LandingContent = {
  meta: {
    title: "JuriSense Gate — Compliance de Fornecedores e Contratos, com Evidência",
    description:
      "O JuriSense Gate transforma contratos, dados de fornecedores e a política da sua empresa em decisões de compliance auditáveis e explicáveis — com IA, motor de política executável e evidência ancorada em blockchain.",
  },
  nav: {
    features: "Funcionalidades",
    howItWorks: "Como funciona",
    pricing: "Preços",
    faq: "FAQ",
    login: "Entrar",
    talkToUs: "Falar com o time",
  },
  hero: {
    badge: "Motor de compliance para fornecedores e contratos",
    headlinePrefix: "Saiba, com ",
    headlineAccent: "evidência",
    headlineSuffix: ", se pode contratar este fornecedor e assinar este contrato",
    subtext:
      "O JuriSense Gate transforma contratos, dados de fornecedores e a política da sua empresa em decisões de compliance auditáveis — com IA, motor de política executável e evidência ancorada em blockchain.",
    ctaPrimary: "Agendar uma conversa",
    ctaSecondary: "Ver como funciona",
    trustBadges: [
      { icon: "shield", label: "LGPD por padrão" },
      { icon: "bolt", label: "IA nunca decide sozinha" },
      { icon: "sparkles", label: "Evidência verificável em blockchain" },
    ],
    mockup: {
      sectionLabel: "Compliance",
      title: "Revisões desta semana",
      monthDelta: "+12% este mês",
      stats: [
        { value: "34", label: "Fornecedores" },
        { value: "19", label: "Contratos" },
        { value: "3", label: "Em revisão" },
      ],
      review: { status: "REVISAR", name: "SaaS Beta Ltda.", note: "Cláusula de responsabilidade ilimitada" },
      approved: { status: "APROVAR", name: "Consultoria Delta ME", note: "Todas as regras da política aprovadas" },
      engineRunning: "Motor de política em execução",
    },
  },
  features: {
    title: "Tudo que você precisa para aprovar fornecedores e contratos com segurança",
    subtitle: "Da verificação do fornecedor à evidência verificável em blockchain — em um só fluxo.",
    items: [
      {
        title: "Inteligência de Fornecedores",
        description:
          "Verifique fornecedores automaticamente em fontes oficiais — situação cadastral, listas de sanções/restrições — e mantenha um histórico imutável de cada checagem.",
        icon: "card",
        accent: "bg-blue-100 text-blue-700",
      },
      {
        title: "Inteligência de Contratos",
        description:
          "Extraia dados estruturados de contratos em PDF, DOCX ou TXT: valor, prazo, responsabilidade, dados pessoais e propriedade intelectual — com citação exata da cláusula de origem.",
        icon: "report",
        accent: "bg-indigo-100 text-indigo-700",
      },
      {
        title: "Motor de Política Executável",
        description:
          "Transforme a política da sua empresa em regras versionadas e determinísticas — quando X, então aprove, revise ou bloqueie. A regra é sua, não de um modelo de IA.",
        icon: "scale",
        accent: "bg-violet-100 text-violet-700",
      },
      {
        title: "Motor de Decisão e Risco",
        description:
          "Combine evidências de fornecedor, contrato e política em um único resultado explicável: APROVAR, REVISAR ou BLOQUEAR — sempre acompanhado do porquê.",
        icon: "chart",
        accent: "bg-cyan-100 text-cyan-700",
      },
      {
        title: "Aprovação Humana Roteada",
        description:
          "Toda decisão que exige revisão é roteada automaticamente para o papel certo — Jurídico, Compliance, Diretoria — como um fluxo auditável, nunca uma resolução silenciosa.",
        icon: "users",
        accent: "bg-emerald-100 text-emerald-700",
      },
      {
        title: "Trilha de Auditoria Completa",
        description:
          "Toda ação que muda o estado de uma decisão gera um evento de auditoria imutável. Nada acontece em silêncio, nada se perde com o tempo.",
        icon: "bell",
        accent: "bg-rose-100 text-rose-700",
      },
      {
        title: "IA que Nunca Decide Sozinha",
        description:
          "A IA extrai, classifica e resume — sempre com proveniência de documento, página e trecho. Ela nunca aprova ou bloqueia por conta própria: essa decisão é sempre da sua política.",
        icon: "sparkles",
        accent: "bg-amber-100 text-amber-700",
      },
      {
        title: "Evidência Verificável em Blockchain",
        description:
          "O hash do pacote de evidências de cada decisão é ancorado em uma rede pública e à prova de adulteração — então 'isso foi alterado depois?' tem uma resposta que não depende de confiar no JuriSense.",
        icon: "shield",
        accent: "bg-green-100 text-green-700",
      },
    ],
  },
  howItWorks: {
    title: "Comece em 5 passos",
    subtitle: "Da primeira conversa à operação completa",
    steps: [
      {
        step: 1,
        title: "Converse com o time",
        description: "Entenda como o JuriSense Gate se encaixa no seu processo de compliance, sem compromisso.",
      },
      {
        step: 2,
        title: "Configure sua política",
        description:
          "Codifique junto com o nosso time as regras que já existem no seu Jurídico e Compliance como política executável.",
      },
      {
        step: 3,
        title: "Cadastre fornecedores e contratos",
        description: "Traga seus fornecedores e contratos reais para o fluxo.",
      },
      {
        step: 4,
        title: "Receba decisões explicáveis",
        description: "Toda análise chega com APROVAR, REVISAR ou BLOQUEAR — e o porquê completo.",
      },
      {
        step: 5,
        title: "Audite quando precisar",
        description: "Acesse o Decision Passport e a verificação em blockchain a qualquer momento, mesmo anos depois.",
      },
    ],
  },
  plans: {
    title: "Preço pelo seu tamanho, não pela sua lista de funcionalidades",
    subtitle: "Todos os planos compartilham o mesmo motor de compliance — os limites acompanham seu volume.",
    highlightedBadge: "Mais popular",
    items: [
      {
        name: "Starter",
        audience: "Empresas de 50 a 150 colaboradores iniciando um processo estruturado de compliance de fornecedores.",
        price: "Falar com o time",
        priceNote: "",
        limits: [
          "1 política principal",
          "Fornecedores e contratos em volume inicial",
          "Times de Procurement e Jurídico/Compliance",
          "Execuções de IA incluídas no plano",
          "Sem acesso à API",
        ],
        cta: "Falar com o time",
      },
      {
        name: "Business",
        audience: "Empresas com um pipeline de fornecedores recorrente e mais de uma área envolvida na decisão.",
        price: "Falar com o time",
        priceNote: "",
        highlighted: true,
        limits: [
          "Múltiplas políticas simultâneas",
          "Limites de fornecedores, contratos e IA ampliados",
          "Mais usuários: Procurement, Jurídico, Compliance e Finanças",
          "Integrações básicas (Slack, e-mail)",
          "Suporte prioritário",
        ],
        cta: "Falar com o time",
      },
      {
        name: "Growth",
        audience: "Empresas em estágio avançado de maturidade de procurement, com múltiplas unidades de negócio.",
        price: "Falar com o time",
        priceNote: "",
        limits: [
          "Políticas ilimitadas",
          "Mais automação — mais decisões aprovadas automaticamente, com segurança",
          "Acesso antecipado à API (com limite de uso)",
          "Armazenamento ampliado",
          "SLA de suporte mais rápido",
        ],
        cta: "Falar com o time",
      },
      {
        name: "Enterprise",
        audience: "Grandes empresas e compradores com exigências regulatórias e de segurança elevadas.",
        price: "Falar com o time",
        priceNote: "",
        limits: [
          "Limites customizados ou ilimitados",
          "SSO e requisitos avançados de segurança e auditoria",
          "Múltiplos pacotes de jurisdição/compliance",
          "Acesso completo à API",
          "Onboarding e suporte dedicados",
        ],
        cta: "Falar com o time",
      },
    ],
    includedTitle: "Incluso em todos os planos",
    included: [
      "Motor de decisão APROVAR / REVISAR / BLOQUEAR",
      "Decision Passport em cada decisão",
      "Trilha de auditoria imutável",
      "Verificação de fornecedores em fontes oficiais",
      "IA com proveniência — nunca decide sozinha",
      "Evidência ancorada em blockchain",
      "Conformidade LGPD por padrão",
      "Isolamento de dados por organização",
    ],
    footnote:
      "Os limites exatos de cada plano são definidos em conversa com o seu time, de acordo com o volume real de fornecedores e contratos da sua empresa.",
  },
  faq: {
    title: "Perguntas frequentes",
    subtitle: "Tire suas dúvidas sobre o JuriSense Gate",
    items: [
      {
        question: "O JuriSense Gate é um ERP ou um sistema de gestão jurídica?",
        answer:
          "Não. O JuriSense Gate não substitui seu ERP nem uma ferramenta de CLM. Ele consome dados de fornecedores e contratos para produzir uma decisão de compliance — não gerencia pedidos de compra, faturamento ou a negociação do contrato em si.",
      },
      {
        question: "A IA do JuriSense Gate pode aprovar ou bloquear um fornecedor sozinha?",
        answer:
          "Não. A IA extrai, classifica e resume informações — nunca decide o resultado de compliance. Quem decide são as regras da sua própria política, configuradas pelo seu time de Jurídico/Compliance. Esse é um limite técnico do produto, não apenas uma promessa de marketing.",
      },
      {
        question: "O que exatamente fica registrado no blockchain?",
        answer:
          "Apenas o hash do pacote de evidências de cada decisão — nunca o conteúdo do contrato, dados de fornecedores ou dados pessoais. O blockchain serve só para provar que a evidência não foi alterada depois, de forma independente do banco de dados do JuriSense.",
      },
      {
        question: "Como funciona o preço?",
        answer:
          "Os planos variam por volume de fornecedores, contratos e execuções de IA, não por funcionalidade. Como os limites certos dependem do seu volume real de compliance, definimos isso em conversa com o seu time, não em uma tabela fixa.",
      },
      {
        question: "Quanto tempo leva para começar a usar?",
        answer:
          "Depois da primeira conversa, configuramos sua política junto com o seu time e você já pode cadastrar fornecedores e contratos reais. O tempo exato depende da complexidade da sua política inicial.",
      },
      {
        question: "O JuriSense Gate substitui o parecer do meu time jurídico?",
        answer:
          "Não. O JuriSense Gate executa a política que o seu próprio Jurídico/Compliance define e aprova. Ele nunca fornece aconselhamento jurídico nem substitui o julgamento do seu advogado.",
      },
      {
        question: "Meus dados ficam isolados de outras empresas que usam o JuriSense Gate?",
        answer:
          "Sim. Cada organização tem seus dados isolados por padrão, e nenhum conteúdo confidencial de contrato ou dado pessoal é exposto publicamente — nem mesmo no blockchain, onde só o hash é ancorado.",
      },
      {
        question: "O que acontece quando uma política ou um contrato muda depois da decisão?",
        answer:
          "O JuriSense Gate reavalia a decisão automaticamente quando a política muda ou surge uma nova versão do contrato, e mantém o histórico completo — a decisão antiga nunca é apagada, só superada por uma nova.",
      },
    ],
  },
  cta: {
    headline: "Pronto para ter evidência, não achismo, em cada decisão de fornecedor?",
    subtext: "Fale com o nosso time e veja como o JuriSense Gate se encaixa no seu processo de compliance.",
    button: "Falar com o time",
  },
  footer: {
    tagline: "Decisões de compliance de fornecedores e contratos, explicáveis e verificáveis.",
    productLabel: "Produto",
    resourcesLabel: "Recursos",
    contactLabel: "Contato",
    faqHelp: "FAQ / Ajuda",
    privacy: "Privacidade",
    terms: "Termos",
    rights: "Todos os direitos reservados.",
  },
};

const es: LandingContent = {
  meta: {
    title: "JuriSense Gate — Cumplimiento de Proveedores y Contratos, con Evidencia",
    description:
      "JuriSense Gate convierte contratos, datos de proveedores y la política de tu empresa en decisiones de cumplimiento auditables y explicables — con IA, un motor de políticas ejecutables y evidencia anclada en blockchain.",
  },
  nav: {
    features: "Funciones",
    howItWorks: "Cómo funciona",
    pricing: "Precios",
    faq: "Preguntas",
    login: "Iniciar sesión",
    talkToUs: "Hablar con nosotros",
  },
  hero: {
    badge: "Motor de cumplimiento para proveedores y contratos",
    headlinePrefix: "Sepa, con ",
    headlineAccent: "evidencia",
    headlineSuffix: ", si puede contratar a este proveedor y firmar este contrato",
    subtext:
      "JuriSense Gate convierte contratos, datos de proveedores y la política de tu empresa en decisiones de cumplimiento auditables — con IA, un motor de políticas ejecutables y evidencia anclada en blockchain.",
    ctaPrimary: "Agendar una conversación",
    ctaSecondary: "Ver cómo funciona",
    trustBadges: [
      { icon: "shield", label: "LGPD por defecto" },
      { icon: "bolt", label: "La IA nunca decide sola" },
      { icon: "sparkles", label: "Evidencia verificable en blockchain" },
    ],
    mockup: {
      sectionLabel: "Cumplimiento",
      title: "Revisiones de esta semana",
      monthDelta: "+12% este mes",
      stats: [
        { value: "34", label: "Proveedores" },
        { value: "19", label: "Contratos" },
        { value: "3", label: "En revisión" },
      ],
      review: { status: "REVISAR", name: "SaaS Beta Ltd.", note: "Cláusula de responsabilidad ilimitada" },
      approved: { status: "APROBAR", name: "Consultora Delta", note: "Todas las reglas de la política aprobadas" },
      engineRunning: "Motor de políticas en ejecución",
    },
  },
  features: {
    title: "Todo lo que necesitas para aprobar proveedores y contratos con confianza",
    subtitle: "Desde la verificación del proveedor hasta evidencia verificable en blockchain — en un solo flujo.",
    items: [
      {
        title: "Inteligencia de Proveedores",
        description:
          "Verifica proveedores automáticamente contra fuentes oficiales — estado registral, listas de sanciones/restricciones — y mantiene un historial inmutable de cada verificación.",
        icon: "card",
        accent: "bg-blue-100 text-blue-700",
      },
      {
        title: "Inteligencia de Contratos",
        description:
          "Extrae datos estructurados de contratos en PDF, DOCX o TXT: valor, duración, responsabilidad, tratamiento de datos personales y propiedad intelectual — con citas exactas a la cláusula de origen.",
        icon: "report",
        accent: "bg-indigo-100 text-indigo-700",
      },
      {
        title: "Motor de Políticas Ejecutables",
        description:
          "Convierte la política de tu empresa en reglas versionadas y deterministas — cuando X, entonces aprobar, revisar o bloquear. La regla es tuya, no el juicio de un modelo.",
        icon: "scale",
        accent: "bg-violet-100 text-violet-700",
      },
      {
        title: "Motor de Cumplimiento y Riesgo",
        description:
          "Combina evidencia de proveedores, evidencia de contratos y reglas de política en un solo resultado explicable: APROBAR, REVISAR o BLOQUEAR — siempre con el porqué.",
        icon: "chart",
        accent: "bg-cyan-100 text-cyan-700",
      },
      {
        title: "Aprobación Humana Enrutada",
        description:
          "Toda decisión que requiere revisión se enruta automáticamente al rol correcto — Legal, Cumplimiento, Dirección — como un flujo auditable, nunca una resolución silenciosa.",
        icon: "users",
        accent: "bg-emerald-100 text-emerald-700",
      },
      {
        title: "Registro de Auditoría Completo",
        description:
          "Cada acción que cambia el estado de una decisión genera un evento de auditoría inmutable. Nada ocurre en silencio ni se pierde con el tiempo.",
        icon: "bell",
        accent: "bg-rose-100 text-rose-700",
      },
      {
        title: "IA que Nunca Decide Sola",
        description:
          "La IA extrae, clasifica y resume — siempre con procedencia de documento, página y cláusula. Nunca aprueba ni bloquea por sí misma: esa decisión siempre es de tu política.",
        icon: "sparkles",
        accent: "bg-amber-100 text-amber-700",
      },
      {
        title: "Evidencia Verificable en Blockchain",
        description:
          "El hash del paquete de evidencia de cada decisión se ancla en una red pública a prueba de manipulación — así, '¿se alteró esto después?' tiene una respuesta que no depende de confiar en JuriSense.",
        icon: "shield",
        accent: "bg-green-100 text-green-700",
      },
    ],
  },
  howItWorks: {
    title: "Comienza en 5 pasos",
    subtitle: "De la primera conversación a la operación completa",
    steps: [
      {
        step: 1,
        title: "Habla con nosotros",
        description: "Descubre cómo JuriSense Gate se adapta a tu proceso de cumplimiento, sin compromiso.",
      },
      {
        step: 2,
        title: "Configura tu política",
        description:
          "Trabajamos contigo para codificar las reglas de tu equipo Legal/Cumplimiento como política ejecutable.",
      },
      {
        step: 3,
        title: "Agrega proveedores y contratos",
        description: "Incorpora tus proveedores y contratos reales al flujo.",
      },
      {
        step: 4,
        title: "Recibe decisiones explicables",
        description: "Cada revisión llega como APROBAR, REVISAR o BLOQUEAR — con el porqué completo.",
      },
      {
        step: 5,
        title: "Audita cuando lo necesites",
        description: "Accede al Decision Passport y su verificación en blockchain en cualquier momento, incluso años después.",
      },
    ],
  },
  plans: {
    title: "Precio según tu tamaño, no según tu lista de funciones",
    subtitle: "Todos los planes comparten el mismo motor de cumplimiento — los límites escalan con tu volumen.",
    highlightedBadge: "Más popular",
    items: [
      {
        name: "Starter",
        audience: "Empresas de 50 a 150 empleados que inician un proceso estructurado de cumplimiento de proveedores.",
        price: "Hablar con nosotros",
        priceNote: "",
        limits: [
          "1 política principal",
          "Proveedores y contratos en volumen inicial",
          "Asientos para Compras y Legal/Cumplimiento",
          "Ejecuciones de IA incluidas",
          "Sin acceso a la API",
        ],
        cta: "Hablar con nosotros",
      },
      {
        name: "Business",
        audience: "Empresas con un flujo recurrente de proveedores y más de un equipo involucrado.",
        price: "Hablar con nosotros",
        priceNote: "",
        highlighted: true,
        limits: [
          "Múltiples políticas simultáneas",
          "Límites ampliados de proveedores, contratos e IA",
          "Más usuarios: Compras, Legal, Cumplimiento y Finanzas",
          "Integraciones básicas (Slack, correo)",
          "Soporte prioritario",
        ],
        cta: "Hablar con nosotros",
      },
      {
        name: "Growth",
        audience: "Empresas con mayor madurez de compras y múltiples unidades de negocio.",
        price: "Hablar con nosotros",
        priceNote: "",
        limits: [
          "Políticas ilimitadas",
          "Más automatización — más decisiones aprobadas automáticamente, con seguridad",
          "Acceso anticipado a la API (con límite de uso)",
          "Almacenamiento ampliado",
          "SLA de soporte más rápido",
        ],
        cta: "Hablar con nosotros",
      },
      {
        name: "Enterprise",
        audience: "Grandes empresas y compradores con requisitos regulatorios y de seguridad elevados.",
        price: "Hablar con nosotros",
        priceNote: "",
        limits: [
          "Límites personalizados o ilimitados",
          "SSO y requisitos avanzados de seguridad y auditoría",
          "Múltiples paquetes de jurisdicción/cumplimiento",
          "Acceso completo a la API",
          "Onboarding y soporte dedicados",
        ],
        cta: "Hablar con nosotros",
      },
    ],
    includedTitle: "Incluido en todos los planes",
    included: [
      "Motor de decisión APROBAR / REVISAR / BLOQUEAR",
      "Un Decision Passport por cada decisión",
      "Registro de auditoría inmutable",
      "Verificación de proveedores contra fuentes oficiales",
      "IA con procedencia — nunca decide sola",
      "Evidencia anclada en blockchain",
      "Cumplimiento de LGPD por defecto",
      "Aislamiento de datos por organización",
    ],
    footnote:
      "Los límites exactos de cada plan se definen en conversación con tu equipo, según el volumen real de proveedores y contratos de tu empresa.",
  },
  faq: {
    title: "Preguntas frecuentes",
    subtitle: "Respuestas sobre JuriSense Gate",
    items: [
      {
        question: "¿JuriSense Gate es un ERP o una herramienta de gestión legal?",
        answer:
          "No. JuriSense Gate no reemplaza tu ERP ni una herramienta de CLM. Consume datos de proveedores y contratos para producir una decisión de cumplimiento — no gestiona órdenes de compra, facturación ni la negociación del contrato en sí.",
      },
      {
        question: "¿La IA de JuriSense Gate puede aprobar o bloquear a un proveedor por sí sola?",
        answer:
          "No. La IA extrae, clasifica y resume información — nunca decide el resultado de cumplimiento. Eso siempre lo deciden las reglas de tu propia política, configuradas por tu equipo Legal/Cumplimiento. Es una restricción técnica del producto, no solo una promesa de marketing.",
      },
      {
        question: "¿Qué se registra exactamente en el blockchain?",
        answer:
          "Solo el hash del paquete de evidencia de cada decisión — nunca el contenido del contrato, datos de proveedores ni datos personales. El blockchain solo prueba que la evidencia no fue alterada después, de forma independiente de la base de datos de JuriSense.",
      },
      {
        question: "¿Cómo funciona el precio?",
        answer:
          "Los planes escalan según tu volumen de proveedores, contratos y ejecuciones de IA, no según el acceso a funciones. Como los límites correctos dependen de tu volumen real de cumplimiento, los definimos en conversación con tu equipo, no en una tabla fija.",
      },
      {
        question: "¿Cuánto tiempo toma empezar a usarlo?",
        answer:
          "Después de la primera conversación, configuramos tu política junto con tu equipo y ya puedes agregar proveedores y contratos reales. El tiempo exacto depende de la complejidad de tu política inicial.",
      },
      {
        question: "¿JuriSense Gate reemplaza el criterio de mi equipo legal?",
        answer:
          "No. JuriSense Gate ejecuta la política que tu propio equipo Legal/Cumplimiento define y aprueba. Nunca brinda asesoría legal ni sustituye el juicio de tu abogado.",
      },
      {
        question: "¿Mis datos están aislados de otras empresas que usan JuriSense Gate?",
        answer:
          "Sí. Los datos de cada organización están aislados por defecto, y ningún contenido confidencial de contrato ni dato personal se expone públicamente — ni siquiera en el blockchain, donde solo se ancla el hash.",
      },
      {
        question: "¿Qué pasa cuando una política o un contrato cambia después de una decisión?",
        answer:
          "JuriSense Gate reevalúa la decisión automáticamente cuando la política cambia o aparece una nueva versión del contrato, y conserva el historial completo — la decisión anterior nunca se elimina, solo es reemplazada por una nueva.",
      },
    ],
  },
  cta: {
    headline: "¿Listo para tener evidencia, no suposiciones, en cada decisión de proveedores?",
    subtext: "Habla con nuestro equipo y descubre cómo JuriSense Gate se adapta a tu proceso de cumplimiento.",
    button: "Hablar con nosotros",
  },
  footer: {
    tagline: "Decisiones de cumplimiento de proveedores y contratos, explicables y verificables.",
    productLabel: "Producto",
    resourcesLabel: "Recursos",
    contactLabel: "Contacto",
    faqHelp: "Preguntas / Ayuda",
    privacy: "Privacidad",
    terms: "Términos",
    rights: "Todos los derechos reservados.",
  },
};

const CONTENT: Record<Locale, LandingContent> = { en, pt, es };

export function getLandingContent(locale: Locale): LandingContent {
  return CONTENT[locale];
}

export function isLocale(value: string): value is Locale {
  return (LOCALES as string[]).includes(value);
}

export function localeHref(locale: Locale): string {
  return locale === DEFAULT_LOCALE ? "/" : `/${locale}`;
}

export const contact = {
  email: "astreusdev.tech@gmail.com",
  phone: "(86) 99436-9763",
  location: "Parnaíba, PI",
  whatsapp: "https://wa.link/i07wi7",
  social: {
    linkedin: "https://www.linkedin.com/company/astreus-j/about/",
    instagram: "https://www.instagram.com/astreus_dev/",
    twitter: "https://x.com/Astreus_Dev",
  },
};
