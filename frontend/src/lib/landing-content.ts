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
 *
 * Presentation concerns (Tailwind classes, icon colors) deliberately do NOT live here — only
 * semantic icon *keys* do. Visual styling is centralized once in the consuming components
 * (`Features.tsx`, `HowItWorks.tsx`, etc.), not tripled across `en`/`pt`/`es`.
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
  /** Key into the icon map in `Features.tsx`. Not translated — identical across locales. */
  icon: string;
}

export interface Plan {
  name: string;
  audience: string;
  price: string;
  period: string;
  annual: string;
  highlighted?: boolean;
  limits: string[];
  cta: string;
}

export interface Step {
  step: number;
  title: string;
  description: string;
  /** Key into the icon map in `HowItWorks.tsx`. Not translated — identical across locales. */
  icon: string;
}

export interface Faq {
  question: string;
  answer: string;
}

export interface LandingContent {
  meta: { title: string; description: string };
  nav: {
    skipToContent: string;
    features: string;
    howItWorks: string;
    pricing: string;
    faq: string;
    login: string;
    talkToUs: string;
    primaryNav: string;
    openMenu: string;
    closeMenu: string;
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
      liveLabel: string;
      primary: {
        supplier: string;
        outcome: string;
        riskLabel: string;
        risk: string;
        evidenceLabel: string;
        evidence: string;
        policyLabel: string;
        policy: string;
      };
      secondary: { supplier: string; outcome: string; note: string };
      stats: { value: string; label: string }[];
      monthDelta: string;
    };
  };
  features: {
    eyebrow: string;
    title: string;
    subtitle: string;
    groupPipeline: string;
    groupTrust: string;
    items: Feature[];
  };
  howItWorks: { eyebrow: string; title: string; subtitle: string; stepLabel: string; steps: Step[] };
  plans: {
    title: string;
    subtitle: string;
    pricingNote: string;
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
    contactLabel: string;
    faqHelp: string;
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
    skipToContent: "Skip to content",
    features: "Features",
    howItWorks: "How it works",
    pricing: "Pricing",
    faq: "FAQ",
    login: "Log in",
    talkToUs: "Talk to us",
    primaryNav: "Primary",
    openMenu: "Open navigation",
    closeMenu: "Close navigation",
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
      liveLabel: "Policy engine running",
      primary: {
        supplier: "SaaS Beta Ltd.",
        outcome: "REVIEW",
        riskLabel: "Risk",
        risk: "Medium",
        evidenceLabel: "Evidence",
        evidence: "Clause 14.2 — unlimited liability",
        policyLabel: "Policy",
        policy: "LEGAL-008",
      },
      secondary: {
        supplier: "Delta Consulting",
        outcome: "APPROVE",
        note: "Every policy rule passed",
      },
      stats: [
        { value: "34", label: "Suppliers" },
        { value: "19", label: "Contracts" },
        { value: "3", label: "In review" },
      ],
      monthDelta: "+12% this month",
    },
  },
  features: {
    eyebrow: "Platform",
    title: "Everything you need to approve suppliers and contracts with confidence",
    subtitle: "From verifying the supplier to blockchain-verifiable evidence — in one flow.",
    groupPipeline: "The compliance pipeline",
    groupTrust: "Trust & governance",
    items: [
      {
        title: "Supplier Intelligence",
        description:
          "Verify suppliers automatically against official sources — registry status, sanctions/restriction lists — and keep an immutable history of every check.",
        icon: "truck",
      },
      {
        title: "Contract Intelligence",
        description:
          "Extract structured data from contracts in PDF, DOCX, or TXT: value, duration, liability, data-processing terms, and IP — with exact citations back to the source clause.",
        icon: "file-search",
      },
      {
        title: "Executable Policy Engine",
        description:
          "Turn your company's own policy into versioned, deterministic rules — when X, then approve, review, or block. The rule is yours, not a model's judgment.",
        icon: "gavel",
      },
      {
        title: "Compliance & Risk Engine",
        description:
          "Combine supplier evidence, contract evidence, and policy rules into one explainable outcome: APPROVE, REVIEW, or BLOCK — always with the why.",
        icon: "workflow",
      },
      {
        title: "Routed Human Approval",
        description:
          "Every decision that needs review is routed automatically to the right role — Legal, Compliance, a director — as an auditable workflow, never a silent resolution.",
        icon: "users",
      },
      {
        title: "Full Audit Trail",
        description:
          "Every state-changing action emits an immutable audit event. Nothing happens silently, and nothing gets lost over time.",
        icon: "history",
      },
      {
        title: "AI That Never Decides Alone",
        description:
          "AI extracts, classifies, and summarizes — always with document/page/clause provenance. It never approves or blocks on its own: that call always belongs to your policy.",
        icon: "brain-circuit",
      },
      {
        title: "Blockchain-Verifiable Evidence",
        description:
          "Each decision's evidence package is hash-anchored on a public, tamper-evident network — so \"was this altered afterward?\" has an answer that doesn't depend on trusting JuriSense.",
        icon: "anchor",
      },
    ],
  },
  howItWorks: {
    eyebrow: "Onboarding",
    title: "Get started in 5 steps",
    subtitle: "From the first conversation to full operation",
    stepLabel: "Step",
    steps: [
      {
        step: 1,
        title: "Talk to us",
        description: "See how JuriSense Gate fits your compliance process, with no commitment.",
        icon: "message-circle",
      },
      {
        step: 2,
        title: "Configure your policy",
        description: "We work with you to encode your Legal/Compliance rules as executable policy.",
        icon: "sliders-horizontal",
      },
      {
        step: 3,
        title: "Add suppliers and contracts",
        description: "Bring your real suppliers and contracts into the flow.",
        icon: "upload-cloud",
      },
      {
        step: 4,
        title: "Get explainable decisions",
        description: "Every review comes back as APPROVE, REVIEW, or BLOCK — with the full why.",
        icon: "check-circle-2",
      },
      {
        step: 5,
        title: "Audit whenever you need to",
        description: "Pull up the Decision Passport and its blockchain verification, even years later.",
        icon: "shield-check",
      },
    ],
  },
  plans: {
    title: "All the features. Room to grow.",
    subtitle: "Choose your capacity. Every plan includes the same released features and standard support.",
    pricingNote: "Prices in Brazilian reais (BRL), per organization. Save 10% with annual prepayment. Contact us for a 14-day trial with reduced usage limits.",
    highlightedBadge: "Recommended",
    items: [
      {
        name: "Starter",
        audience: "For small teams organizing supplier compliance.",
        price: "R$149",
        period: "/month",
        annual: "R$1,609.20 billed annually",
        limits: [
          "5 active users",
          "100 active suppliers",
          "100 supplier verifications/month",
          "30 contract analyses/month",
          "60 AI processing units/month",
          "15 GB of storage",
          "10 active policies",
          "10,000 API requests/month, when released"
        ],
        cta: "Choose Starter"
      },
      {
        name: "Business",
        audience: "For recurring reviews across multiple departments.",
        price: "R$349",
        period: "/month",
        annual: "R$3,769.20 billed annually",
        limits: [
          "15 active users",
          "500 active suppliers",
          "300 supplier verifications/month",
          "100 contract analyses/month",
          "200 AI processing units/month",
          "50 GB of storage",
          "40 active policies",
          "50,000 API requests/month, when released"
        ],
        cta: "Choose Business",
        highlighted: true
      },
      {
        name: "Growth",
        audience: "For growing operations and multiple teams.",
        price: "R$799",
        period: "/month",
        annual: "R$8,629.20 billed annually",
        limits: [
          "50 active users",
          "1,500 active suppliers",
          "800 supplier verifications/month",
          "300 contract analyses/month",
          "600 AI processing units/month",
          "150 GB of storage",
          "120 active policies",
          "200,000 API requests/month, when released"
        ],
        cta: "Choose Growth"
      },
      {
        name: "Enterprise",
        audience: "For organizations that need capacity beyond Growth.",
        price: "Custom quote",
        period: "",
        annual: "Capacity and terms agreed with your team",
        limits: [
          "Agreed user and supplier limits",
          "Custom verification and contract quotas",
          "AI and storage sized to your usage",
          "Agreed policy and API quotas",
          "The same features and standard support"
        ],
        cta: "Request a quote"
      }
    ],
    includedTitle: "Included in every plan",
    included: [
      "Supplier verification",
      "AI-assisted contract extraction",
      "Policy authoring and versioning",
      "Compliance decisions and approval workflows",
      "Decision Passports and verifiable evidence",
      "Audit history",
      "Role-based access and data isolation",
      "Standard support"
    ],
    footnote: "Monthly quotas are shared across your organization, including on annual plans. Storage and active-record limits do not reset. API access and integrations are included in every tier when released. Reaching a limit pauses new operations that use that quota; your existing records remain accessible."
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
          "Starter costs R$149/month, Business R$349/month, and Growth R$799/month per organization, in Brazilian reais. Enterprise has a custom quote. All plans include the same released features; usage limits differ. Annual prepayment saves 10%. Contract analyses consume both the contract allowance and AI units: we budget two units per ordinary contract, while longer jobs may require more. Contact our team to subscribe.",
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
    contactLabel: "Contact",
    faqHelp: "FAQ / Help",
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
    skipToContent: "Pular para o conteúdo",
    features: "Funcionalidades",
    howItWorks: "Como funciona",
    pricing: "Preços",
    faq: "FAQ",
    login: "Entrar",
    talkToUs: "Falar com o time",
    primaryNav: "Principal",
    openMenu: "Abrir navegação",
    closeMenu: "Fechar navegação",
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
      liveLabel: "Motor de política em execução",
      primary: {
        supplier: "SaaS Beta Ltda.",
        outcome: "REVISAR",
        riskLabel: "Risco",
        risk: "Médio",
        evidenceLabel: "Evidência",
        evidence: "Cláusula 14.2 — responsabilidade ilimitada",
        policyLabel: "Política",
        policy: "LEGAL-008",
      },
      secondary: {
        supplier: "Consultoria Delta ME",
        outcome: "APROVAR",
        note: "Todas as regras da política foram aprovadas",
      },
      stats: [
        { value: "34", label: "Fornecedores" },
        { value: "19", label: "Contratos" },
        { value: "3", label: "Em revisão" },
      ],
      monthDelta: "+12% este mês",
    },
  },
  features: {
    eyebrow: "Plataforma",
    title: "Tudo que você precisa para aprovar fornecedores e contratos com segurança",
    subtitle: "Da verificação do fornecedor à evidência verificável em blockchain — em um só fluxo.",
    groupPipeline: "O fluxo de compliance",
    groupTrust: "Confiança e governança",
    items: [
      {
        title: "Inteligência de Fornecedores",
        description:
          "Verifique fornecedores automaticamente em fontes oficiais — situação cadastral, listas de sanções/restrições — e mantenha um histórico imutável de cada checagem.",
        icon: "truck",
      },
      {
        title: "Inteligência de Contratos",
        description:
          "Extraia dados estruturados de contratos em PDF, DOCX ou TXT: valor, prazo, responsabilidade, dados pessoais e propriedade intelectual — com citação exata da cláusula de origem.",
        icon: "file-search",
      },
      {
        title: "Motor de Política Executável",
        description:
          "Transforme a política da sua empresa em regras versionadas e determinísticas — quando X, então aprove, revise ou bloqueie. A regra é sua, não de um modelo de IA.",
        icon: "gavel",
      },
      {
        title: "Motor de Decisão e Risco",
        description:
          "Combine evidências de fornecedor, contrato e política em um único resultado explicável: APROVAR, REVISAR ou BLOQUEAR — sempre acompanhado do porquê.",
        icon: "workflow",
      },
      {
        title: "Aprovação Humana Roteada",
        description:
          "Toda decisão que exige revisão é roteada automaticamente para o papel certo — Jurídico, Compliance, Diretoria — como um fluxo auditável, nunca uma resolução silenciosa.",
        icon: "users",
      },
      {
        title: "Trilha de Auditoria Completa",
        description:
          "Toda ação que muda o estado de uma decisão gera um evento de auditoria imutável. Nada acontece em silêncio, nada se perde com o tempo.",
        icon: "history",
      },
      {
        title: "IA que Nunca Decide Sozinha",
        description:
          "A IA extrai, classifica e resume — sempre com proveniência de documento, página e trecho. Ela nunca aprova ou bloqueia por conta própria: essa decisão é sempre da sua política.",
        icon: "brain-circuit",
      },
      {
        title: "Evidência Verificável em Blockchain",
        description:
          "O hash do pacote de evidências de cada decisão é ancorado em uma rede pública e à prova de adulteração — então 'isso foi alterado depois?' tem uma resposta que não depende de confiar no JuriSense.",
        icon: "anchor",
      },
    ],
  },
  howItWorks: {
    eyebrow: "Onboarding",
    title: "Comece em 5 passos",
    subtitle: "Da primeira conversa à operação completa",
    stepLabel: "Passo",
    steps: [
      {
        step: 1,
        title: "Converse com o time",
        description: "Entenda como o JuriSense Gate se encaixa no seu processo de compliance, sem compromisso.",
        icon: "message-circle",
      },
      {
        step: 2,
        title: "Configure sua política",
        description:
          "Codifique junto com o nosso time as regras que já existem no seu Jurídico e Compliance como política executável.",
        icon: "sliders-horizontal",
      },
      {
        step: 3,
        title: "Cadastre fornecedores e contratos",
        description: "Traga seus fornecedores e contratos reais para o fluxo.",
        icon: "upload-cloud",
      },
      {
        step: 4,
        title: "Receba decisões explicáveis",
        description: "Toda análise chega com APROVAR, REVISAR ou BLOQUEAR — e o porquê completo.",
        icon: "check-circle-2",
      },
      {
        step: 5,
        title: "Audite quando precisar",
        description: "Acesse o Decision Passport e a verificação em blockchain a qualquer momento, mesmo anos depois.",
        icon: "shield-check",
      },
    ],
  },
  plans: {
    title: "Todas as funcionalidades. Espaço para crescer.",
    subtitle: "Escolha a capacidade ideal. Todos os planos incluem as mesmas funcionalidades disponíveis e suporte padrão.",
    pricingNote: "Preços em reais (BRL), por organização. Economize 10% no pagamento anual antecipado. Fale com o time para testar por 14 dias com cotas reduzidas.",
    highlightedBadge: "Recomendado",
    items: [
      {
        name: "Starter",
        audience: "Para pequenos times organizando o compliance de fornecedores.",
        price: "R$ 149",
        period: "/mês",
        annual: "R$ 1.609,20 cobrados por ano",
        limits: [
          "5 usuários ativos",
          "100 fornecedores ativos",
          "100 verificações de fornecedores/mês",
          "30 análises de contratos/mês",
          "60 unidades de processamento de IA/mês",
          "15 GB de armazenamento",
          "10 políticas ativas",
          "10.000 requisições de API/mês, quando disponível"
        ],
        cta: "Escolher Starter"
      },
      {
        name: "Business",
        audience: "Para análises recorrentes entre diferentes áreas.",
        price: "R$ 349",
        period: "/mês",
        annual: "R$ 3.769,20 cobrados por ano",
        limits: [
          "15 usuários ativos",
          "500 fornecedores ativos",
          "300 verificações de fornecedores/mês",
          "100 análises de contratos/mês",
          "200 unidades de processamento de IA/mês",
          "50 GB de armazenamento",
          "40 políticas ativas",
          "50.000 requisições de API/mês, quando disponível"
        ],
        cta: "Escolher Business",
        highlighted: true
      },
      {
        name: "Growth",
        audience: "Para operações em expansão e múltiplos times.",
        price: "R$ 799",
        period: "/mês",
        annual: "R$ 8.629,20 cobrados por ano",
        limits: [
          "50 usuários ativos",
          "1.500 fornecedores ativos",
          "800 verificações de fornecedores/mês",
          "300 análises de contratos/mês",
          "600 unidades de processamento de IA/mês",
          "150 GB de armazenamento",
          "120 políticas ativas",
          "200.000 requisições de API/mês, quando disponível"
        ],
        cta: "Escolher Growth"
      },
      {
        name: "Enterprise",
        audience: "Para empresas que precisam de capacidade além do Growth.",
        price: "Sob consulta",
        period: "",
        annual: "Capacidade e condições definidas com seu time",
        limits: [
          "Limites acordados de usuários e fornecedores",
          "Cotas personalizadas de verificações e contratos",
          "IA e armazenamento conforme seu volume",
          "Cotas acordadas de políticas e API",
          "As mesmas funcionalidades e suporte padrão"
        ],
        cta: "Solicitar proposta"
      }
    ],
    includedTitle: "Incluso em todos os planos",
    included: [
      "Verificação de fornecedores",
      "Extração de contratos com IA",
      "Criação e versionamento de políticas",
      "Decisões de compliance e fluxos de aprovação",
      "Decision Passports e evidências verificáveis",
      "Histórico de auditoria",
      "Permissões por perfil e isolamento de dados",
      "Suporte padrão"
    ],
    footnote: "As cotas mensais são compartilhadas pela organização, inclusive no plano anual. Armazenamento e limites de registros ativos não são renovados mensalmente. API e integrações entram em todos os planos quando disponíveis. Ao atingir uma cota, novas operações que a utilizam ficam suspensas; seus registros existentes continuam acessíveis."
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
          "O Starter custa R$149/mês, o Business R$349/mês e o Growth R$799/mês por organização. O Enterprise tem orçamento personalizado. Todos incluem as mesmas funcionalidades disponíveis, com diferentes limites de uso. O pagamento anual antecipado tem 10% de desconto. As análises consomem a cota de contratos e unidades de IA: reservamos duas unidades por contrato comum, enquanto trabalhos mais longos podem exigir mais. A contratação é feita com nosso time.",
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
    contactLabel: "Contato",
    faqHelp: "FAQ / Ajuda",
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
    skipToContent: "Saltar al contenido",
    features: "Funciones",
    howItWorks: "Cómo funciona",
    pricing: "Precios",
    faq: "Preguntas",
    login: "Iniciar sesión",
    talkToUs: "Hablar con nosotros",
    primaryNav: "Principal",
    openMenu: "Abrir navegación",
    closeMenu: "Cerrar navegación",
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
      liveLabel: "Motor de políticas en ejecución",
      primary: {
        supplier: "SaaS Beta Ltd.",
        outcome: "REVISAR",
        riskLabel: "Riesgo",
        risk: "Medio",
        evidenceLabel: "Evidencia",
        evidence: "Cláusula 14.2 — responsabilidad ilimitada",
        policyLabel: "Política",
        policy: "LEGAL-008",
      },
      secondary: {
        supplier: "Consultora Delta",
        outcome: "APROBAR",
        note: "Se aprobaron todas las reglas de la política",
      },
      stats: [
        { value: "34", label: "Proveedores" },
        { value: "19", label: "Contratos" },
        { value: "3", label: "En revisión" },
      ],
      monthDelta: "+12% este mes",
    },
  },
  features: {
    eyebrow: "Plataforma",
    title: "Todo lo que necesitas para aprobar proveedores y contratos con confianza",
    subtitle: "Desde la verificación del proveedor hasta evidencia verificable en blockchain — en un solo flujo.",
    groupPipeline: "El flujo de cumplimiento",
    groupTrust: "Confianza y gobernanza",
    items: [
      {
        title: "Inteligencia de Proveedores",
        description:
          "Verifica proveedores automáticamente contra fuentes oficiales — estado registral, listas de sanciones/restricciones — y mantiene un historial inmutable de cada verificación.",
        icon: "truck",
      },
      {
        title: "Inteligencia de Contratos",
        description:
          "Extrae datos estructurados de contratos en PDF, DOCX o TXT: valor, duración, responsabilidad, tratamiento de datos personales y propiedad intelectual — con citas exactas a la cláusula de origen.",
        icon: "file-search",
      },
      {
        title: "Motor de Políticas Ejecutables",
        description:
          "Convierte la política de tu empresa en reglas versionadas y deterministas — cuando X, entonces aprobar, revisar o bloquear. La regla es tuya, no el juicio de un modelo.",
        icon: "gavel",
      },
      {
        title: "Motor de Cumplimiento y Riesgo",
        description:
          "Combina evidencia de proveedores, evidencia de contratos y reglas de política en un solo resultado explicable: APROBAR, REVISAR o BLOQUEAR — siempre con el porqué.",
        icon: "workflow",
      },
      {
        title: "Aprobación Humana Enrutada",
        description:
          "Toda decisión que requiere revisión se enruta automáticamente al rol correcto — Legal, Cumplimiento, Dirección — como un flujo auditable, nunca una resolución silenciosa.",
        icon: "users",
      },
      {
        title: "Registro de Auditoría Completo",
        description:
          "Cada acción que cambia el estado de una decisión genera un evento de auditoría inmutable. Nada ocurre en silencio ni se pierde con el tiempo.",
        icon: "history",
      },
      {
        title: "IA que Nunca Decide Sola",
        description:
          "La IA extrae, clasifica y resume — siempre con procedencia de documento, página y cláusula. Nunca aprueba ni bloquea por sí misma: esa decisión siempre es de tu política.",
        icon: "brain-circuit",
      },
      {
        title: "Evidencia Verificable en Blockchain",
        description:
          "El hash del paquete de evidencia de cada decisión se ancla en una red pública a prueba de manipulación — así, '¿se alteró esto después?' tiene una respuesta que no depende de confiar en JuriSense.",
        icon: "anchor",
      },
    ],
  },
  howItWorks: {
    eyebrow: "Onboarding",
    title: "Comienza en 5 pasos",
    subtitle: "De la primera conversación a la operación completa",
    stepLabel: "Paso",
    steps: [
      {
        step: 1,
        title: "Habla con nosotros",
        description: "Descubre cómo JuriSense Gate se adapta a tu proceso de cumplimiento, sin compromiso.",
        icon: "message-circle",
      },
      {
        step: 2,
        title: "Configura tu política",
        description:
          "Trabajamos contigo para codificar las reglas de tu equipo Legal/Cumplimiento como política ejecutable.",
        icon: "sliders-horizontal",
      },
      {
        step: 3,
        title: "Agrega proveedores y contratos",
        description: "Incorpora tus proveedores y contratos reales al flujo.",
        icon: "upload-cloud",
      },
      {
        step: 4,
        title: "Recibe decisiones explicables",
        description: "Cada revisión llega como APROBAR, REVISAR o BLOQUEAR — con el porqué completo.",
        icon: "check-circle-2",
      },
      {
        step: 5,
        title: "Audita cuando lo necesites",
        description: "Accede al Decision Passport y su verificación en blockchain en cualquier momento, incluso años después.",
        icon: "shield-check",
      },
    ],
  },
  plans: {
    title: "Todas las funciones. Espacio para crecer.",
    subtitle: "Elige tu capacidad. Todos los planes incluyen las mismas funciones disponibles y soporte estándar.",
    pricingNote: "Precios en reales brasileños (BRL), por organización. Ahorra un 10% con el pago anual anticipado. Contáctanos para una prueba de 14 días con cuotas reducidas.",
    highlightedBadge: "Recomendado",
    items: [
      {
        name: "Starter",
        audience: "Para equipos pequeños que organizan el cumplimiento de proveedores.",
        price: "R$ 149",
        period: "/mes",
        annual: "R$ 1.609,20 facturados al año",
        limits: [
          "5 usuarios activos",
          "100 proveedores activos",
          "100 verificaciones de proveedores/mes",
          "30 análisis de contratos/mes",
          "60 unidades de procesamiento de IA/mes",
          "15 GB de almacenamiento",
          "10 políticas activas",
          "10.000 solicitudes de API/mes, cuando esté disponible"
        ],
        cta: "Elegir Starter"
      },
      {
        name: "Business",
        audience: "Para revisiones recurrentes entre varias áreas.",
        price: "R$ 349",
        period: "/mes",
        annual: "R$ 3.769,20 facturados al año",
        limits: [
          "15 usuarios activos",
          "500 proveedores activos",
          "300 verificaciones de proveedores/mes",
          "100 análisis de contratos/mes",
          "200 unidades de procesamiento de IA/mes",
          "50 GB de almacenamiento",
          "40 políticas activas",
          "50.000 solicitudes de API/mes, cuando esté disponible"
        ],
        cta: "Elegir Business",
        highlighted: true
      },
      {
        name: "Growth",
        audience: "Para operaciones en expansión y múltiples equipos.",
        price: "R$ 799",
        period: "/mes",
        annual: "R$ 8.629,20 facturados al año",
        limits: [
          "50 usuarios activos",
          "1.500 proveedores activos",
          "800 verificaciones de proveedores/mes",
          "300 análisis de contratos/mes",
          "600 unidades de procesamiento de IA/mes",
          "150 GB de almacenamiento",
          "120 políticas activas",
          "200.000 solicitudes de API/mes, cuando esté disponible"
        ],
        cta: "Elegir Growth"
      },
      {
        name: "Enterprise",
        audience: "Para organizaciones que necesitan capacidad superior a Growth.",
        price: "A consultar",
        period: "",
        annual: "Capacidad y condiciones acordadas con tu equipo",
        limits: [
          "Límites acordados de usuarios y proveedores",
          "Cuotas personalizadas de verificaciones y contratos",
          "IA y almacenamiento según tu volumen",
          "Cuotas acordadas de políticas y API",
          "Las mismas funciones y soporte estándar"
        ],
        cta: "Solicitar propuesta"
      }
    ],
    includedTitle: "Incluido en todos los planes",
    included: [
      "Verificación de proveedores",
      "Extracción de contratos con IA",
      "Creación y versionado de políticas",
      "Decisiones de cumplimiento y flujos de aprobación",
      "Decision Passports y evidencia verificable",
      "Historial de auditoría",
      "Permisos por rol y aislamiento de datos",
      "Soporte estándar"
    ],
    footnote: "Las cuotas mensuales se comparten en toda la organización, también en los planes anuales. El almacenamiento y los límites de registros activos no se reinician cada mes. API e integraciones se incluyen en todos los planes cuando estén disponibles. Al alcanzar una cuota, se pausan las nuevas operaciones que la consumen; tus registros existentes siguen accesibles."
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
          "Starter cuesta R$149/mes, Business R$349/mes y Growth R$799/mes por organización, en reales brasileños. Enterprise tiene una cotización personalizada. Todos incluyen las mismas funciones disponibles, con distintos límites de uso. El pago anual anticipado tiene un 10% de descuento. Los análisis consumen la cuota de contratos y unidades de IA: presupuestamos dos unidades por contrato habitual; los trabajos más largos pueden necesitar más. Contacta con nuestro equipo para contratar.",
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
    contactLabel: "Contacto",
    faqHelp: "Preguntas / Ayuda",
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
