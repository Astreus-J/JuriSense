export type Feature = {
  title: string;
  description: string;
  icon: string; // chave do ícone em Icons.tsx
  accent: string; // classes tailwind do fundo do ícone
};

export const features: Feature[] = [
  {
    title: "Gestão de Processos",
    description:
      "Acompanhe todos os processos do escritório em um só lugar, com timeline, sincronização automática com tribunais e alertas.",
    icon: "scale",
    accent: "bg-blue-100 text-blue-700",
  },
  {
    title: "Gestão de Clientes",
    description:
      "Cadastro completo, histórico de atendimentos, documentos e comunicação centralizada.",
    icon: "users",
    accent: "bg-emerald-100 text-emerald-700",
  },
  {
    title: "IA para Petições",
    description:
      "Gere petições, contratos e pareceres com inteligência artificial treinada para o direito brasileiro.",
    icon: "sparkles",
    accent: "bg-amber-100 text-amber-700",
  },
  {
    title: "Jurimetria Avançada",
    description:
      "Perfil decisório de magistrados, probabilidade de êxito e análise preditiva de resultados.",
    icon: "chart",
    accent: "bg-violet-100 text-violet-700",
  },
  {
    title: "Alertas de Prazos",
    description:
      "Calculadora inteligente de prazos processuais e alertas escalonados por e-mail, push e WhatsApp.",
    icon: "bell",
    accent: "bg-rose-100 text-rose-700",
  },
  {
    title: "Financeiro Automatizado",
    description:
      "Honorários, faturas, boletos, timesheet e relatórios financeiros completos.",
    icon: "card",
    accent: "bg-cyan-100 text-cyan-700",
  },
  {
    title: "Relatórios Inteligentes",
    description:
      "Dashboards personalizáveis, KPIs em tempo real e business intelligence da carteira de processos.",
    icon: "report",
    accent: "bg-indigo-100 text-indigo-700",
  },
  {
    title: "Segurança LGPD",
    description:
      "Criptografia AES-256, autenticação 2FA, logs de auditoria e conformidade total com a LGPD.",
    icon: "shield",
    accent: "bg-green-100 text-green-700",
  },
];

export type Plan = {
  name: string;
  audience: string;
  price: string;
  priceNote: string;
  highlighted?: boolean;
  limits: string[];
  cta: string;
};

export const plans: Plan[] = [
  {
    name: "Autônomo",
    audience: "Advogados autônomos",
    price: "R$ 189",
    priceNote: "/mês",
    limits: [
      "1 usuário",
      "250 processos ativos",
      "15 GB de armazenamento",
      "50 gerações de IA/mês",
    ],
    cta: "Começar 14 dias grátis",
  },
  {
    name: "Escritório",
    audience: "Pequenos escritórios (2-5 advogados)",
    price: "R$ 499",
    priceNote: "/mês",
    highlighted: true,
    limits: [
      "Até 5 usuários",
      "1.250 processos ativos",
      "75 GB de armazenamento",
      "250 gerações de IA/mês",
    ],
    cta: "Começar 14 dias grátis",
  },
  {
    name: "Escritório Plus",
    audience: "Médios escritórios (6-20 advogados)",
    price: "R$ 1.490",
    priceNote: "/mês",
    limits: [
      "Até 20 usuários",
      "5.000 processos ativos",
      "300 GB de armazenamento",
      "1.000 gerações de IA/mês",
    ],
    cta: "Começar 14 dias grátis",
  },
  {
    name: "Enterprise",
    audience: "Grandes escritórios e departamentos jurídicos",
    price: "Sob consulta",
    priceNote: "",
    limits: [
      "Usuários ilimitados",
      "Processos ilimitados",
      "Armazenamento sob demanda",
      "IA sob demanda",
    ],
    cta: "Falar com especialista",
  },
];

export const allPlansInclude = [
  "Gestão de processos com sincronização automática",
  "IA Jurídica: petições, resumos e análises",
  "Jurimetria e análise preditiva",
  "Portal do cliente",
  "Agenda, prazos e financeiro integrados",
  "Assinatura digital e OCR",
  "Notificações por e-mail, push e WhatsApp",
  "Suporte por e-mail, chat e WhatsApp",
];

export type Step = { step: number; title: string; description: string };

export const steps: Step[] = [
  { step: 1, title: "Crie sua conta", description: "Cadastro rápido em menos de 2 minutos" },
  { step: 2, title: "Configure seu escritório", description: "Personalize as configurações do seu escritório" },
  { step: 3, title: "Adicione seus clientes", description: "Gerencie seus clientes de forma eficiente" },
  { step: 4, title: "Configure seus casos", description: "Organize seus casos jurídicos facilmente" },
  { step: 5, title: "Comece a usar", description: "Explore todas as funcionalidades da plataforma" },
];

export type Faq = { question: string; answer: string };

export const faqs: Faq[] = [
  {
    question: "Existe período de teste gratuito?",
    answer:
      "Sim! Você tem 14 dias para testar o JuriSense sem pagar nada e sem precisar cadastrar cartão de crédito. Após o período de teste, basta escolher o plano que melhor se encaixa no tamanho do seu escritório.",
  },
  {
    question: "Qual a diferença entre os planos?",
    answer:
      "Todos os planos incluem 100% das funcionalidades da plataforma. A diferença está apenas nos limites de uso: número de usuários, processos ativos, armazenamento e gerações de IA por mês. Você escolhe pelo tamanho do seu escritório, não pelas funcionalidades.",
  },
  {
    question: "O que acontece se eu ultrapassar os limites do meu plano?",
    answer:
      "Você pode contratar excedentes por consumo (pay-per-use), como pacotes adicionais de processos ativos e gerações de petição avulsas, ou fazer upgrade de plano a qualquer momento com cobrança proporcional.",
  },
  {
    question: "Como funciona a IA Jurídica?",
    answer:
      "Nossa IA analisa documentos jurídicos usando processamento de linguagem natural avançado, identificando cláusulas, riscos e oportunidades. Ela também auxilia na redação de petições, gera resumos de processos e responde perguntas jurídicas via chatbot integrado.",
  },
  {
    question: "Os dados do escritório estão seguros?",
    answer:
      "Sim. Utilizamos criptografia de ponta a ponta, autenticação em dois fatores (2FA), backup automático diário e logs de auditoria completos. Cada escritório tem seus documentos armazenados de forma isolada e em conformidade com a LGPD.",
  },
  {
    question: "Posso cancelar a qualquer momento?",
    answer:
      "Sim, sem multas ou fidelidade. Você pode cancelar a assinatura a qualquer momento diretamente pelo painel de configurações. Seus dados ficam disponíveis para exportação por 30 dias após o cancelamento.",
  },
  {
    question: "O sistema sincroniza com os tribunais automaticamente?",
    answer:
      "Sim. O JuriSense realiza a sincronização automática de movimentações processuais diariamente e envia notificações em tempo real via WhatsApp e e-mail para prazos e novas publicações.",
  },
  {
    question: "Preciso instalar algum programa?",
    answer:
      "Não. O JuriSense é 100% online, funciona em qualquer navegador moderno em computadores, tablets e smartphones. Não há instalação necessária.",
  },
];

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
