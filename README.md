# 📘 SCHEMAJUD - DOCUMENTAÇÃO COMPLETA DO PROJETO

## Sistema de Automação e Inteligência Jurídica

**Versão:** 1.0.2 
**Data:** 04/04/2026  
**Status:** Desenvolvimento 

**Tecnologia:** Backend (Python | FastAPI) + Frontend (Next.js + TypeScript)


---

## 📑 ÍNDICE COMPLETO

1. [Introdução](#introdução)
2. [Visão Geral do Sistema](#visão-geral-do-sistema)
3. [Análise de Mercado](#análise-de-mercado)
4. [Atores do Sistema](#atores-do-sistema)
5. [Requisitos Funcionais](#requisitos-funcionais)
6. [Requisitos Não Funcionais](#requisitos-não-funcionais)
7. [Regras de Negócio](#regras-de-negócio)
8. [Regras de Acesso e Permissões](#regras-de-acesso-e-permissões)
9. [Casos de Uso](#casos-de-uso)
10. [Sistemas Externos](#sistemas-externos)
11. [Arquitetura do Sistema](#arquitetura-do-sistema)
12. [Tecnologias Utilizadas](#tecnologias-utilizadas)
13. [Modelo de Dados](#modelo-de-dados)
14. [Segurança e Compliance](#segurança-e-compliance)
15. [Modelo de Negócio](#modelo-de-negócio)

---

## Introdução

### Contexto

O setor jurídico brasileiro enfrenta desafios significativos relacionados à gestão de processos, controle de prazos e produção de documentos. Advogados gastam aproximadamente 60-70% do tempo em atividades administrativas e burocráticas, reduzindo o tempo disponível para atividades estratégicas e consultivas.

### Problema

- **Sobrecarga Administrativa:** Tarefas repetitivas consomem tempo valioso dos profissionais.
- **Perda de Prazos:** Sistemas inadequados causam prejuízos financeiros e processos éticos.
- **Decisões sem Dados:** Falta de análise preditiva para avaliar viabilidade de ações judiciais.
- **Produção Manual:** Documentos jurídicos são elaborados do zero, sem automação.
- **Sistemas Fragmentados:** Múltiplas ferramentas desconectadas aumentam a complexidade.
- **Alto Custo:** Softwares existentes têm custo elevado e baixa acessibilidade.

### Solução Proposta

O **JuriSense** é uma plataforma SaaS que combina automação de processos, inteligência artificial e business intelligence para transformar a gestão jurídica. O sistema oferece:

- Automação completa do fluxo de trabalho jurídico.
- Inteligência artificial para geração de documentos e análise preditiva.
- Jurimetria avançada com análise comportamental de magistrados.
- Business intelligence com dashboards e KPIs em tempo real.
- Integração nativa com tribunais e sistemas externos.

### Objetivos do Projeto

#### Objetivos de Negócio

- Capturar 5% do mercado brasileiro em 3 anos (25.000 usuários).
- Atingir R$ 10 milhões em receita recorrente anual (ARR) em 24 meses.
- Manter taxa de cancelamento (churn) abaixo de 5% ao ano.
- Alcançar Net Promoter Score (NPS) superior a 70.

#### Objetivos de Produto

- Reduzir em 50% o tempo gasto em tarefas administrativas.
- Aumentar em 30% a taxa de êxito dos processos por meio de análise preditiva.
- Automatizar 80% da produção de documentos jurídicos.
- Integrar com 95% dos tribunais brasileiros.

### Público-Alvo

**Primário:**

- Advogados autônomos (1-2 processos).
- Pequenos escritórios (2-5 advogados).
- Escritórios médios (6-20 advogados).

**Secundário:**

- Departamentos jurídicos empresariais.
- Grandes escritórios (20+ advogados).
- Consultorias jurídicas.

### Diferenciais Competitivos

1. **IA de Última Geração:** Utilização de GPT-4 e Claude 3.5 fine-tuned para o direito brasileiro.
2. **Jurimetria Avançada:** Análise comportamental individual de magistrados.
3. **Performance Superior:** Backend assíncrono em Python (FastAPI) oferece velocidade superior aos concorrentes.
4. **Mobile-First:** Aplicativo com 100% das funcionalidades.

---

## Visão Geral do Sistema

### Descrição Geral


O JuriSense é uma plataforma web e mobile que centraliza todas as operações jurídicas de um escritório ou departamento. O sistema opera em modelo SaaS (Software as a Service), oferecendo alta disponibilidade, escalabilidade e segurança.


### Principais Funcionalidades

#### Gestão de Processos

- Cadastro e acompanhamento de processos judiciais.
- Sincronização automática com tribunais.
- Timeline visual de movimentações.
- Classificação automática de relevância.
- Notificações inteligentes.

#### Inteligência Artificial

- Geração automática de petições, contratos e pareceres.
- Redação assistida em tempo real.
- Análise preditiva de resultados.
- Chatbot jurídico especializado.
- Resumos automáticos de processos e decisões.

#### Jurimetria e Analytics

- Análise estatística de decisões judiciais.
- Perfil decisório de magistrados.
- Probabilidade de êxito por tipo de ação.
- Tempo médio de tramitação.
- Benchmarking com mercado.

#### Gestão Documental

- Armazenamento seguro e criptografado.
- Controle de versões.
- Assinatura digital ICP-Brasil.
- OCR (reconhecimento de texto).
- Templates inteligentes.

#### Controle de Prazos

- Calculadora inteligente de prazos processuais.
- Consideração automática de feriados.
- Alertas escalonados multi-canal.
- Sincronização com Google Calendar/Outlook.
- Agenda compartilhada de equipe.

#### Business Intelligence

- Dashboards personalizáveis.
- KPIs em tempo real.
- Relatórios automatizados.
- Análise de carteira de processos.
- Provisionamento de passivos.

#### Financeiro

- Controle de honorários e custos.
- Gestão de contratos de honorários.
- Emissão de boletos e notas fiscais.
- Análise de ROI por processo.
- Fluxo de caixa projetado.

### Arquitetura de Alto Nível

#### Camada de Apresentação

- **Web App:** Next.js + React + TypeScript.
- **Mobile Apps:** React Native (iOS e Android).
- **Portal do Cliente:** Interface simplificada para clientes.

#### Camada de API

- **Reverse Proxy:** Nginx (na VPS).
- **Backend:** Python, FastAPI.
- **WebSocket:** Para notificações em tempo real.

#### Camada de Negócio

- **Auth Service:** Autenticação e autorização.
- **Process Service:** Gestão de processos.
- **AI Service:** Inteligência artificial.
- **Document Service:** Gestão documental.
- **Analytics Service:** Business intelligence.
- **Integration Service:** Integrações externas.
- **Notification Service:** Notificações multi-canal.
- **Calendar Service:** Prazos e agenda.
- **Financial Service:** Controle financeiro.

#### Camada de Dados

- **PostgreSQL 15 (externo):** Dados estruturados em banco gerenciado fora da VPS.
- **Redis 7 (na VPS):** Cache e filas.
- **Sistema de Arquivos da VPS:** Documentos organizados em diretórios por empresa (organização).

#### Infraestrutura

- **Hospedagem:** VPS única com Docker Compose (frontend, backend, workers, Redis, Nginx).
- **Externos:** Banco de dados gerenciado (PostgreSQL) e APIs de IA (OpenAI/Anthropic).
- **Armazenamento de Documentos:** Diretórios por empresa no filesystem da VPS.
- **CI/CD:** GitHub Actions.
- **Monitoring:** Prometheus + Grafana.
- **Logs:** Logs estruturados centralizados na VPS.

---

## Análise de Mercado

### Tamanho do Mercado

#### TAM (Total Addressable Market)

- **1,3 milhão** de advogados registrados na OAB.
- **500 mil** advogados ativos em escritórios e empresas.
- **150 mil** escritórios de advocacia no Brasil.
- **Ticket médio:** R$ 200-500/mês por usuário.
- **Valor Total:** R$ 1,2 bilhão/ano.

#### SAM (Serviceable Available Market)

- **200 mil** advogados digitalizados (40% do mercado ativo).
- **Valor:** R$ 480 milhões/ano.

#### SOM (Serviceable Obtainable Market - 3 anos)

- **25 mil** usuários (5% do SAM).
- **Valor:** R$ 75 milhões/ano.

### Concorrentes Principais

#### CPJ-3C (Preâmbulo)

- **Posição:** Líder de mercado.
- **Pontos Fortes:** 11M+ processos gerenciados, marca consolidada, 3x eleito mais usado.
- **Pontos Fracos:** Interface desatualizada, pouca IA, tecnologia legada (.NET).
- **Preço:** ~R$ 300/mês por usuário.

#### EasyJur

- **Posição:** Líder em inovação.
- **Pontos Fortes:** JurisAI avançado (1TB dados treinados), Internet Banking nativo.
- **Pontos Fracos:** Preço elevado, complexidade.
- **Preço:** ~R$ 400/mês por usuário.

#### ADVBOX

- **Posição:** Maior base de usuários.
- **Pontos Fortes:** 140k+ advogados, TaskScore único, gestão de equipes.
- **Pontos Fracos:** Performance limitada, interface complexa.
- **Preço:** ~R$ 250/mês por usuário.

#### Projuris (ADV/Empresas)

- **Posição:** Líder corporativo.
- **Pontos Fortes:** Jurimetria robusta, foco empresarial.
- **Pontos Fracos:** Preço premium, não atende pequenos escritórios.
- **Preço:** R$ 500+/mês por usuário.

#### Astrea (Aurum)

- **Posição:** Challenger.
- **Pontos Fortes:** Interface moderna, gratuito por 1 ano.
- **Pontos Fracos:** Funcionalidades limitadas, base pequena.
- **Preço:** ~R$ 150/mês após trial.

### Análise SWOT

#### Forças (Strengths)

- IA de última geração (GPT-4, Claude 3.5).
- Backend assíncrono em Python/FastAPI (performance superior).
- Jurimetria com análise individual de juízes.
- Pricing agressivo (todas as funcionalidades em todos os planos + pay-per-use para excedentes).
- Interface moderna e intuitiva (React).
- Mobile-first com 100% das funcionalidades.

#### Fraquezas (Weaknesses)

- Marca nova sem reconhecimento de mercado.
- Base inicial limitada para jurimetria.
- Equipe pequena vs. concorrentes estabelecidos.
- Capital limitado para marketing massivo.
- Sem histórico de cases de sucesso.

#### Oportunidades (Opportunities)

- Mercado em crescimento (10% ao ano).
- Transformação digital acelerada pós-pandemia.
- Insatisfação com softwares legados.
- IA revolucionando o setor.
- Demanda por soluções mobile.
- Regulamentações favorecem segurança de dados (LGPD).

#### Ameaças (Threats)

- Concorrentes com recursos massivos.
- Possível resistência da OAB à IA.
- Mudanças regulatórias.
- Dependência de APIs de tribunais.
- Custos elevados de infraestrutura de IA.
- Entrada de players internacionais (LegalTech global).

---

## Atores do Sistema

### Atores Primários (Usuários Diretos)

#### A01 - Administrador

**Descrição:** Gerencia toda a organização, usuários, configurações e permissões.

**Responsabilidades:**

- Configurar organização e planos.
- Gerenciar usuários e suas permissões.
- Configurar integrações (tribunais, APIs).
- Acessar logs de auditoria.
- Definir políticas de segurança.
- Gerenciar assinaturas e pagamentos.

**Permissões:** Acesso total ao sistema.

#### A02 - Advogado Sênior

**Descrição:** Profissional com OAB ativa, gerencia processos, equipes e clientes.

**Responsabilidades:**

- Gerenciar processos judiciais.
- Criar e editar documentos.
- Usar IA para geração de petições.
- Acessar jurimetria e análises.
- Gerenciar clientes e honorários.
- Supervisionar estagiários.
- Aprovar documentos críticos.

**Permissões:** Acesso completo, exceto configurações administrativas.

#### A03 - Advogado Júnior

**Descrição:** Profissional em início de carreira, executa tarefas delegadas.

**Responsabilidades:**

- Acompanhar processos designados.
- Criar documentos básicos.
- Usar IA com supervisão.
- Registrar prazos e compromissos.
- Fazer pesquisas jurídicas.
- Registrar timesheet.

**Permissões:** Acesso limitado, sem gestão financeira ou configurações.

#### A04 - Estagiário

**Descrição:** Estudante de direito, auxilia nas atividades administrativas.

**Responsabilidades:**

- Visualizar processos designados.
- Fazer pesquisas jurídicas.
- Organizar documentos.
- Registrar informações básicas.
- Acompanhar audiências.

**Permissões:** Somente leitura na maioria dos módulos, acesso limitado.

#### A05 - Cliente

**Descrição:** Pessoa física ou jurídica que contrata serviços jurídicos.

**Responsabilidades:**

- Visualizar seus processos.
- Acessar documentos autorizados.
- Acompanhar movimentações.
- Pagar honorários.
- Solicitar serviços.
- Chat com advogado.

**Permissões:** Acesso apenas aos seus próprios dados via portal específico.

### Atores Secundários (Sistemas)

#### A06 - Sistema de IA

**Descrição:** Serviços de inteligência artificial (OpenAI, Anthropic).

**Interações:**

- Recebe prompts para geração de conteúdo.
- Retorna petições, contratos, análises.
- Processa resumos e traduções.
- Responde chatbot.

#### A07 - Tribunais (APIs)

**Descrição:** Sistemas judiciais que fornecem dados de processos.

**Interações:**

- PJe, e-SAJ, PROJUDI, DataJud.
- Consulta de processos.
- Download de documentos.
- Peticionamento eletrônico.

#### A08 - Sistema de Pagamento

**Descrição:** Gateways de pagamento (Stripe, PagSeguro, Mercado Pago).

**Interações:**

- Processar cobranças.
- Emitir boletos.
- Gerar links de pagamento PIX.
- Confirmar recebimentos.

#### A09 - Serviços de Comunicação

**Descrição:** WhatsApp, E-mail, SMS.

**Interações:**

- Enviar notificações.
- Alertas de prazos.
- Confirmações de agendamento.

#### A10 - Serviços de Armazenamento

**Descrição:** Sistema de arquivos da VPS (diretórios por empresa), com backup externo.

**Interações:**

- Armazenar documentos em diretórios isolados por empresa.
- Backups automáticos para destino externo.
- Sincronização de arquivos.

---

## Requisitos Funcionais

### RF - MÓDULO 1: AUTENTICAÇÃO E GESTÃO DE USUÁRIOS (RF01-RF07)

**RF01 - Login com Autenticação Multifator**

- Sistema deve permitir login com e-mail e senha.
- Suporte a 2FA (autenticação de dois fatores) via TOTP ou SMS.
- Login com certificado digital ICP-Brasil (opcional).
- Bloqueio após 5 tentativas falhas.
- Histórico de acessos por usuário.

**RF02 - Recuperação de Senha**

- Envio de link de recuperação por e-mail.
- Token expira em 1 hora.
- Validação de força da nova senha.
- Notificação ao usuário após alteração.

**RF03 - Perfis de Acesso**

- Sistema deve suportar 5 perfis: Administrador, Advogado Sênior, Advogado Júnior, Estagiário, Cliente.
- Cada perfil tem permissões específicas pré-definidas.
- Administrador pode customizar permissões.

**RF04 - CRUD de Usuários**

- Criar, visualizar, editar e desativar usuários.
- Campos obrigatórios: nome completo, e-mail, OAB (para advogados).
- Validação de número OAB na API da OAB.
- Não permitir exclusão física (apenas desativação).

**RF05 - Controle de Permissões Granular**

- Sistema deve permitir controle por módulo e ação (criar, ler, atualizar, deletar).
- Permissões por processo individual (compartilhamento seletivo).

**RF06 - Logs de Auditoria**

- Registrar todas as ações: login, logout, criação, edição, exclusão.
- Armazenar: usuário, IP, timestamp, ação, dados antes/depois.
- Logs imutáveis e criptografados.
- Retenção mínima de 5 anos (compliance LGPD).

**RF07 - Single Sign-On (SSO)**

- Suporte a SAML 2.0 para integração corporativa.
- Compatível com Azure AD, Okta, Google Workspace.
- Provisionamento automático de usuários (SCIM).

### RF - MÓDULO 2: JURIMETRIA E ANÁLISE PREDITIVA (RF08-RF15)

**RF08 - Análise Estatística de Tribunais**

- Dados agregados por tribunal, vara e instância.
- Taxa de procedência/improcedência por tipo de ação.
- Distribuição de tempos de tramitação.
- Comparação entre tribunais.

**RF09 - Cálculo de Probabilidade de Êxito**

- Algoritmo considera: tipo de ação, tribunal, vara, magistrado, teses utilizadas, histórico similar.
- Retorna probabilidade percentual (0-100%).
- Intervalo de confiança estatístico.
- Fatores que influenciam o resultado.

**RF10 - Tempo Médio de Tramitação**

- Por tribunal, vara e tipo de ação.
- Separado por instância (1º grau, 2º grau, STJ, STF).
- Identificação de gargalos.
- Previsão de duração do processo.

**RF11 - Identificação de Teses Vencedoras**

- Análise de jurisprudência favorável por tema.
- Correlação entre teses e resultados positivos.
- Sugestão de argumentos baseados em dados.

**RF12 - Perfil Decisório de Magistrados**

- Análise individual por juiz/desembargador.
- Taxa de procedência por tipo de ação.
- Tempo médio de decisão.
- Jurisprudências frequentemente citadas.
- Preferências argumentativas.

**RF13 - Comparativo de Performance**

- Escritório vs. média do mercado.
- Taxa de êxito por advogado.
- Tempo médio de resolução.
- Benchmarking regional.

**RF14 - Previsão com Intervalo de Confiança**

- Modelo probabilístico com machine learning.
- Intervalo de confiança (ex: 70-85%).
- Cenários: otimista, realista, pessimista.

**RF15 - Exportação de Relatórios de Jurimetria**

- Formato PDF e Excel.
- Gráficos visuais incluídos.
- Dados anonimizados quando necessário.

### RF - MÓDULO 3: INTELIGÊNCIA ARTIFICIAL (RF16-RF22)

**RF16 - Geração Automática de Petições**

- Usuário fornece: tipo de ação, fatos, pedidos, partes.
- IA gera petição completa com: endereçamento, qualificação, narrativa, fundamentação legal, jurisprudência, pedidos.
- Adaptação ao estilo de escrita do advogado (personalização).
- Citação automática de artigos de lei aplicáveis.

**RF17 - Redação Assistida em Tempo Real**

- Sugestões enquanto usuário escreve.
- Correção gramatical e jurídica.
- Alertas de inconsistências (ex: prazo errado, foro inadequado).
- Sugestão de teses e argumentos.

**RF18 - Geração de Contratos Personalizados**

- Templates dinâmicos por tipo (trabalho, prestação de serviços, locação).
- Preenchimento automático de dados das partes.
- Cláusulas inteligentes baseadas no contexto.
- Identificação de riscos e sugestões de melhorias.

**RF19 - Resumo Automático**

- Processos: resumo em 1 parágrafo do histórico completo.
- Decisões: extração dos pontos principais.
- Contratos: cláusulas relevantes destacadas.
- Ajuste de nível de detalhe (resumido, médio, detalhado).

**RF20 - Análise de Documentos**

- Upload de contratos para revisão.
- Identificação de cláusulas abusivas ou problemáticas.
- Comparação de versões (track changes).
- Extração de dados estruturados (valor, prazo, partes).

**RF21 - Chatbot Jurídico (JurisBot)**

- Responde consultas jurídicas complexas.
- Analisa casos e sugere estratégias.
- Pesquisa jurisprudencial conversacional.
- Integração com base de conhecimento do escritório.

**RF22 - Tradução e Simplificação**

- Juridiquês → Linguagem simples (para clientes).
- Adaptação de peças para diferentes públicos.
- Geração de versão "cliente" de documentos técnicos.

### RF - MÓDULO 4: GESTÃO DE PROCESSOS (RF23-RF31)

**RF23 - Cadastro de Processos**

- Manual: formulário com validação de número CNJ.
- Automático: busca por número em tribunais integrados.
- Campos: número, tribunal, vara, tipo de ação, assunto, partes, valor da causa.

**RF24 - Busca em Tribunais**

- Consulta automática via API ou scraping.
- Suporte: PJe, e-SAJ, PROJUDI, DataJud.
- Atualização sob demanda ou agendada.

**RF25 - Atualização Automática de Movimentações**

- Sincronização diária (ou configurável).
- Parsing inteligente de movimentações.
- Classificação automática por relevância.
- Detecção de intimações e prazos.

**RF26 - Timeline Visual**

- Linha do tempo interativa de movimentações.
- Filtros por tipo e relevância.
- Anexo de documentos por movimentação.
- Anotações por movimento.

**RF27 - Filtros Avançados**

- Status: ativo, suspenso, arquivado, sentenciado.
- Tribunal, vara, tipo de ação.
- Cliente, parte contrária.
- Advogado responsável.
- Data de distribuição/última movimentação.
- Tags customizadas.
- Valor da causa (faixas).

**RF28 - Processos Relacionados**

- Vinculação de processos conexos.
- Identificação automática por partes ou assunto.
- Visualização em grafo.

**RF29 - Anotações Internas**

- Notas por processo ou movimentação.
- Marcação como privada ou compartilhada.
- @menções para notificar colegas.
- Fixar anotações importantes.

**RF30 - Anexação de Documentos**

- Upload de documentos ao processo.
- Categorização automática.
- Versionamento.
- Visualizador integrado.

**RF31 - Portal do Cliente**

- Cliente visualiza apenas seus processos.
- Movimentações em linguagem simplificada.
- Comentários e perguntas ao advogado.
- Download de documentos autorizados.

### RF - MÓDULO 5: GESTÃO DOCUMENTAL (RF32-RF42)

**RF32 - Armazenamento Criptografado**

- Criptografia AES-256 em repouso.
- TLS 1.3 em trânsito.
- Armazenamento no filesystem da VPS, em diretórios isolados por empresa (ex.: `/dados/empresas/{organizacao_id}/`).
- Backup externo criptografado.

**RF33 - Organização Hierárquica**

- Por cliente → processo → tipo → data.
- Pastas customizáveis.
- Tags e etiquetas coloridas.
- Busca por metadata.

**RF34 - Controle de Versões**

- Histórico completo de alterações.
- Restauração de versões anteriores.
- Comparação visual (diff).
- Quem alterou e quando.

**RF35 - Assinatura Digital ICP-Brasil**

- Integração com certificados A1/A3.
- Suporte a múltiplos signatários.
- Validação de certificado.
- Armazenamento do certificado assinado.

**RF36 - OCR (Reconhecimento de Texto)**

- Digitalização de documentos físicos.
- Extração de texto de PDFs escaneados.
- Suporte a português jurídico.
- Indexação para busca.

**RF37 - Busca Full-Text**

- Busca em todo conteúdo dos documentos.
- Filtros por data, tipo, autor.
- Preview de resultado com destaque.
- Busca semântica (não apenas palavras exatas).

**RF38 - Templates Personalizáveis**

- Biblioteca de templates por tipo.
- Editor visual (WYSIWYG).
- Placeholders dinâmicos (ex: {{cliente_nome}}).
- Compartilhamento entre equipe.

**RF39 - Merge de Dados**

- Preenchimento automático de templates.
- Dados do processo, cliente, adversário.
- Geração em PDF, DOCX.
- Assinatura digital automatizada.

**RF40 - Envio por E-mail/WhatsApp**

- Envio direto do sistema.
- Rastreamento de leitura.
- Confirmação de recebimento.
- Histórico de envios.

**RF41 - Links Temporários**

- Compartilhamento seguro sem login.
- Expiração configurável (1h, 24h, 7 dias).
- Proteção por senha opcional.
- Limite de downloads.

**RF42 - Biblioteca de Cláusulas**

- Repositório de cláusulas contratuais.
- Categorização por tipo de contrato.
- Favoritar cláusulas frequentes.
- Busca por palavra-chave.

### RF - MÓDULO 6: PRAZOS E AGENDA (RF43-RF50)

**RF43 - Calculadora Inteligente de Prazos**

- Cálculo automático considerando:
  - Feriados nacionais, estaduais e municipais.
  - Recesso forense e plantões.
  - Prazo em dobro (litisconsortes).
  - Prazo diferenciado (Defensoria, MP).
  - Prazos sucessivos.
- Atualização diária do calendário oficial.
- Alertas se prazo cai em feriado (prorroga).

**RF44 - CRUD de Compromissos**

- Audiências, reuniões, prazos, tarefas.
- Vinculação com processo e cliente.
- Definir participantes.
- Local ou link de videochamada.
- Recorrência (semanal, mensal).

**RF45 - Calendário Visual**

- Visões: dia, semana, mês, agenda.
- Cores por tipo de evento.
- Filtro por advogado, cliente, status.
- Arrastar e soltar para reagendar.

**RF46 - Sincronização Google/Outlook**

- Integração bidirecional.
- Atualização em tempo real.
- Mapeamento de categorias.
- Conflito de horários.

**RF47 - Alertas Escalonados**

- Configuráveis por evento:
  - 7 dias antes.
  - 3 dias antes.
  - 1 dia antes.
  - No dia (horário configurável).
  - 3 horas antes (prazos críticos).
- Múltiplos canais: e-mail, WhatsApp, push, SMS.

**RF48 - Agenda de Equipe**

- Visualização consolidada do escritório.
- Identificar disponibilidade.
- Agendar reuniões em horários livres.
- Exportar agenda do mês.

**RF49 - Bloqueio de Horários**

- Reservar tempo para atividades não processuais.
- Estudo, viagens, férias.
- Bloquear de agendamentos externos.

**RF50 - Exportação em PDF**

- Agenda mensal/semanal em PDF.
- Inclui detalhes dos compromissos.
- Útil para impressão e compartilhamento.

### RF - MÓDULO 7: NOTIFICAÇÕES (RF51-RF59)

**RF51 - Central de Notificações**

- Inbox dentro do sistema.
- Marcar como lida/não lida.
- Arquivar notificações antigas.
- Filtro por tipo e prioridade.

**RF52 - Notificações por E-mail**

- Templates HTML responsivos.
- Opção de unsubscribe.
- Agrupamento (digest).
- Tracking de abertura.

**RF53 - Notificações por WhatsApp**

- Via WhatsApp Business API.
- Mensagens transacionais.
- Limitado a eventos críticos (prazos).
- Opt-in obrigatório.

**RF54 - Push Notifications**

- App mobile (iOS e Android).
- Web push (navegador).
- Agrupamento inteligente.
- Badge count.

**RF55 - Preferências Granulares**

- Configurar por tipo de evento.
- Escolher canais preferidos (email, WhatsApp, push, SMS).
- Horário de silêncio (não perturbe).
- Frequência (imediato, agregado diário).
- Prioridade mínima para notificar.

**RF56 - Priorização Inteligente**

- Crítica: prazos fatais, intimações urgentes (vermelho).
- Média: movimentações relevantes, compromissos próximos (amarelo).
- Baixa: atualizações gerais, lembretes (azul).
- Algoritmo aprende com interações do usuário.

**RF57 - Resumo Diário (Digest)**

- E-mail enviado uma vez ao dia (horário configurável).
- Resume: prazos próximos, movimentações do dia, tarefas pendentes.
- Opção de desativar.

**RF58 - Alertas de Aniversários**

- Clientes, colegas, magistrados.
- Sugestão de envio de mensagem.
- Histórico de relacionamento.

**RF59 - Notificações de Tarefas Atrasadas**

- Alerta diário de tarefas não concluídas.
- Escalonamento para supervisor se não tratado em 3 dias.
- Dashboard de pendências.

### RF - MÓDULO 8: BUSINESS INTELLIGENCE (RF60-RF68)

**RF60 - Dashboard Principal com KPIs**

- Número total de processos ativos.
- Taxa de êxito geral e por tipo de ação.
- Processos ganhos/perdidos no período.
- Valor total de causas em andamento.
- Produtividade da equipe (tarefas concluídas).
- Prazos próximos (próximos 7 dias).
- Honorários a receber.
- Atualização em tempo real.

**RF61 - Dashboards Personalizáveis**

- Arrastar e soltar widgets.
- Escolher métricas relevantes.
- Salvar layouts personalizados.
- Compartilhar dashboards com equipe.

**RF62 - Relatórios Pré-configurados**

- Movimentações do período.
- Produtividade por advogado.
- Processos por status.
- Análise financeira (receitas, custos, ROI).
- Tempo médio de resolução.
- Distribuição geográfica de processos.
- Performance por tipo de ação.

**RF63 - Query Builder Visual**

- Interface drag-and-drop para criar relatórios customizados.
- Seleção de campos, filtros, agrupamentos.
- Salvar queries para reutilização.
- Compartilhar com equipe.

**RF64 - Gráficos Interativos**

- Barras, linhas, funil, heat map, radar.
- Zoom, pan, drill-down.
- Exportar gráfico como imagem.
- Tooltips informativos.

**RF65 - Exportação em Múltiplos Formatos**

- PDF (alta qualidade para apresentações).
- Excel (dados brutos para análise).
- CSV (integração com outras ferramentas).
- DOCX
- Manter formatação e gráficos.

**RF66 - Agendamento de Relatórios**

- Envio automático por email.
- Periodicidade: diária, semanal, mensal.
- Destinatários configuráveis.
- Formato e conteúdo personalizáveis.

**RF67 - Análise de Carteira de Processos**

- Provisionamento de passivos (valor em risco).
- Classificação de risco: alto, médio, baixo.
- Distribuição geográfica (mapa de calor).
- Concentração por cliente (análise de dependência).
- Valor provável de ganho/perda.

**RF68 - Benchmarking com Mercado**

- Comparação com dados agregados e anonimizados.
- Posicionamento percentual (top 10%, 25%, etc.).
- Métricas: taxa de êxito, tempo de resolução, produtividade.
- Insights e recomendações.

### RF - MÓDULO 9: TIMESHEET E PRODUTIVIDADE (RF69-RF77)

**RF69 - Timer Integrado**

- Start/stop de cronômetro.
- Vinculação automática ao processo/cliente atual.
- Pausa para intervalos.
- Registro automático ao finalizar.

**RF70 - Registro Manual de Horas**

- Adicionar horas retroativamente.
- Data, horário, duração.
- Descrição da atividade.
- Aprovação do supervisor.

**RF71 - Vinculação Processo/Cliente**

- Toda entrada de tempo vinculada a processo ou cliente.
- Categorizável como billable/non-billable.
- Geração automática de faturas baseada em horas.

**RF72 - Categorização de Atividades**

- Pesquisa jurídica.
- Redação de peças.
- Audiências/reuniões.
- Atendimento ao cliente.
- Administrativo.
- Customizável por escritório.

**RF73 - Relatórios de Horas**

- Por período (dia, semana, mês).
- Por advogado, cliente ou processo.
- Total de horas billable vs non-billable.
- Valor total a ser cobrado.

**RF74 - Cálculo Automático de Honorários**

- Taxa horária configurável por advogado.
- Cálculo automático baseado em horas trabalhadas.
- Aplicação de descontos/bônus.
- Geração de pré-fatura.

**RF75 - Gamificação (TaskScore)**

- Sistema de pontos por tarefas concluídas:
  - Criar processo: 10 pontos.
  - Gerar petição: 15 pontos.
  - Cumprir prazo: 20 pontos.
  - Ganhar processo: 50 pontos.
- Badges e conquistas (ex: "100 petições geradas").
- Ranking da equipe (diário, semanal, mensal).
- Recompensas configuráveis.

**RF76 - Metas de Produtividade**

- Definir metas individuais e coletivas.
- Processos a gerenciar, horas a trabalhar, receita a gerar.
- Acompanhamento visual (% atingido).
- Alertas quando abaixo da meta.

**RF77 - Análise de Ociosidade**

- Identificar advogados com capacidade ociosa.
- Sugerir redistribuição de casos.
- Balanceamento de carga de trabalho.
- Relatório de utilização por membro da equipe.

### RF - MÓDULO 10: FINANCEIRO (RF78-RF85)

**RF78 - Controle de Custos Processuais**

- Custas judiciais, honorários periciais, despesas com cópias, deslocamento, outros custos operacionais.
- Vinculação ao processo.
- Comprovante (upload de recibo).
- Marcação como reembolsável ou não.

**RF79 - Controle de Honorários**

- Cadastro de contratos de honorários:
  - Fixo: valor determinado.
  - Por hora: taxa x horas trabalhadas.
  - Êxito: percentual sobre resultado.
  - Misto: fixo + êxito.
- Gestão de parcelas/prestações.
- Emissão de notas fiscais.
- Controle de recebimentos e inadimplência.

**RF80 - Análise de ROI por Processo**

- Custos totais (honorários pagos, custas, despesas).
- Valor da causa ou ganho esperado.
- Cálculo de viabilidade econômica.
- Simulação de cenários:
  - Ganho total: receita - custos.
  - Ganho parcial (50%): receita/2 - custos.
  - Perda: apenas custos.
- Recomendação: litigar ou acordar.

**RF81 - Fluxo de Caixa Projetado**

- Previsão de receitas (honorários contratados).
- Previsão de despesas (custos estimados).
- Visão mensal dos próximos 12 meses.
- Identificação de déficits e superávits.

**RF82 - Provisionamento de Passivos**

- Para departamentos jurídicos empresariais.
- Cálculo do valor em risco por processo.
- Classificação por probabilidade de perda.
- Total provisionado vs patrimônio líquido.

**RF83 - Integração com Gateways de Pagamento**

- Boleto bancário (geração e registro).
- PIX (QR Code e copia-e-cola).
- Cartão de crédito (parcelamento).
- Confirmação automática de pagamento.
- Baixa automática de faturas.

**RF84 - Emissão de Recibos e Notas Fiscais**

- Geração automática em PDF.
- Envio por email ao cliente.
- Integração com prefeitura (NF-e).
- Histórico de emissões.

**RF85 - Relatórios Financeiros**

- DRE (Demonstração de Resultado do Exercício).
- Fluxo de caixa realizado.
- Inadimplência (aging report).
- Honorários por cliente/advogado.
- Lucratividade por tipo de caso.

### RF - MÓDULO 11: INTEGRAÇÕES (RF86-RF97)

**RF86 - Integração com PJe**

- Consulta de processos via API oficial.
- Download de documentos processuais.
- Peticionamento eletrônico (protocolo de petições).
- Autenticação via certificado digital ICP-Brasil.
- Tribunais: TRF-1, TRF-2, TRF-3, TRF-4, TRF-5, TRTs.

**RF87 - Integração com e-SAJ**

- Web scraping (não possui API pública).
- Consulta de processos de 1º e 2º grau.
- Quebra de CAPTCHA automatizada.
- Tribunais: TJ-SP, TJ-SC, TJ-PR, TJ-BA, outros.

**RF88 - Integração com PROJUDI**

- API REST (quando disponível) ou scraping.
- Tribunais menores e regionais.

**RF89 - Scraping Inteligente**

- Sistema resiliente a mudanças de layout.
- Detecção automática de alterações.
- Retry com backoff exponencial.
- Rotação de IPs e user agents.
- Rate limiting para evitar bloqueios.
- Fallback para entrada manual se bloqueado.

**RF90 - Jusbrasil API (Opcional)**

- Acesso mediante contrato comercial.
- Busca em 90+ tribunais.
- Dados estruturados e padronizados.
- Custo: R$ 5.000 - R$ 50.000/mês.

**RF91 - Escavador API (Opcional)**

- Busca de processos e diários oficiais.
- Dados de pessoas e empresas.
- Custo: R$ 1.500 - R$ 10.000/mês.

**RF92 - API RESTful Própria**

- Documentação OpenAPI/Swagger.
- Autenticação via API Key.
- Rate limiting: 1000 req/hour.
- Webhooks para eventos.
- Permitir integrações de terceiros.

**RF93 - Webhooks**

- Notificação de eventos para sistemas externos:
  - Processo criado/atualizado.
  - Prazo próximo.
  - Movimentação relevante.
  - Pagamento recebido.
- Configurável por organização.
- Retry automático em caso de falha.
- Logs de entregas.

**RF94 - WhatsApp Business API**

- Envio de notificações transacionais.
- Não é marketing (precisa opt-in).
- Provedores: Twilio, MessageBird, WATI.
- Custo: ~R$ 0,10 por mensagem.

**RF95 - E-mail SMTP/IMAP**

- SMTP para envio (SendGrid, AWS SES, Postmark).
- IMAP para recebimento (integração com inbox).
- Templates personalizáveis.
- Tracking de abertura e cliques.

**RF96 - Google Drive / Dropbox**

- Backup automático de documentos.
- Sincronização bidirecional.
- Estrutura de pastas espelhada.

**RF97 - Open Banking**

- Conciliação bancária automática.
- Identificação de pagamentos recebidos.
- Baixa automática de faturas.
- APIs do Banco Central.

### RF - MÓDULO 12: PORTAL DO CLIENTE (RF98-RF105)

**RF98 - Acesso Web Exclusivo**

- URL única e branding do escritório.
- Login com credenciais separadas.
- Interface simplificada e amigável.

**RF99 - Visualização de Processos**

- Somente processos vinculados ao cliente.
- Informações essenciais: número, status, fase.
- Sem informações técnicas complexas.

**RF100 - Movimentações Simplificadas**

- Linguagem não jurídica.
- Tradução automática de juridiquês.
- Destaque para eventos importantes.

**RF101 - Download de Documentos Autorizados**

- Apenas documentos liberados pelo advogado.
- Contratos, petições principais, sentenças.
- Histórico de downloads.

**RF102 - Chat com Advogado**

- Mensageiro interno.
- Notificação ao advogado responsável.
- Histórico de conversas.
- Anexar arquivos.

**RF103 - Pagamento de Honorários Online**

- Visualizar faturas pendentes.
- Gerar boleto ou PIX.
- Pagar com cartão de crédito.
- Histórico de pagamentos.

**RF104 - Solicitação de Serviços**

- Formulário para novos serviços.
- Agendamento de reuniões.
- Upload de documentos.
- Acompanhamento do status da solicitação.

**RF105 - Notificações Automáticas**

- Email quando há atualização no processo.
- Novos documentos disponíveis.
- Faturas vencendo.
- Compromissos agendados.

### RF - MÓDULO 13: PESQUISA JURÍDICA (RF106-RF112)

**RF106 - Busca em Bases de Jurisprudência**

- Integração com sites dos tribunais:
  - STF, STJ, TST, TSE, STM.
  - TJs estaduais (todos os 27).
  - TRFs (1 a 5).
- Busca unificada em todas as bases.

**RF107 - Pesquisa Semântica**

- Não apenas palavras-chave exatas.
- Compreensão de sinônimos e contexto.
- Busca por conceitos jurídicos.
- Algoritmo de relevância.

**RF108 - Filtros Avançados**

- Data da decisão (intervalo).
- Relator/Ministro.
- Órgão julgador.
- Tipo de decisão (monocrática, colegiada).
- Resultado (provido, negado, parcial).

**RF109 - Histórico de Pesquisas**

- Salvar queries realizadas.
- Reaplicar pesquisas rapidamente.
- Compartilhar com equipe.

**RF110 - Favoritos**

- Salvar jurisprudências importantes.
- Organizar por pastas/tags.
- Adicionar anotações.

**RF111 - Exportação para Petições**

- Botão "Adicionar à petição".
- Formatação automática da citação.
- Inserção no documento em edição.

**RF112 - Alertas de Jurisprudência**

- Monitorar temas de interesse.
- Notificação quando nova decisão relevante.
- Configurável por assunto ou palavra-chave.

### RF - MÓDULO 14: MOBILE (RF113-RF119)

**RF113 - Apps Nativos iOS e Android**

- Desenvolvimento em React Native.
- Publicados nas stores oficiais.
- Atualizações OTA (over-the-air).

**RF114 - 100% das Funcionalidades**

- Paridade com versão web.
- Adaptado para mobile (UI/UX).
- Performance otimizada.

**RF115 - Modo Offline**

- Sincronização quando voltar online.
- Cache de processos recentes.
- Visualização de documentos baixados.
- Fila de ações pendentes.

**RF116 - Ditado por Voz**

- Redação de documentos por voz.
- Reconhecimento de termos jurídicos.
- Correção e edição posterior.

**RF117 - Digitalização com Câmera + OCR**

- Captura de documentos físicos.
- Recorte automático e ajuste de contraste.
- Extração de texto.
- Salvar como PDF pesquisável.

**RF118 - Push Notifications Inteligentes**

- Notificações em tempo real.
- Agrupamento por categoria.
- Ações rápidas (responder, adiar, concluir).

**RF119 - Assinatura Digital Biométrica**

- Uso de biometria do dispositivo (Face ID, Touch ID).
- Assinatura simples (não ICP-Brasil).
- Logs de autenticação.

### RF - MÓDULO 15: COMPLIANCE E LGPD (RF120-RF125)

**RF120 - Termo de Consentimento Digital**

- Aceite obrigatório no cadastro.
- Versões históricas dos termos.
- Log de aceite (IP, timestamp, versão aceita).
- Possibilidade de revogar consentimento.

**RF121 - Portal de Privacidade**

- Cliente pode solicitar:
  - Cópia de todos os seus dados (portabilidade).
  - Correção de dados incorretos.
  - Exclusão de dados (direito ao esquecimento).
- Prazo de resposta: 15 dias úteis.
- Verificação de identidade obrigatória.

**RF122 - Anonimização Automática**

- Dados sensíveis mascarados em relatórios.
- CPF: XXX.XXX.XXX-XX.
- E-mail: x\*\*\*\*@dominio.com.
- Exportação para análise sem identificação.

**RF123 - Criptografia End-to-End**

- Comunicações sensíveis criptografadas.
- Chat advogado-cliente.
- Compartilhamento de documentos confidenciais.
- Chaves gerenciadas localmente.

**RF124 - Backup Automático**

- Backup diário incremental.
- Backup semanal completo.
- Retenção configurável (mínimo 90 dias).
- Criptografia dos backups.
- Armazenamento em região diferente.

**RF125 - Disaster Recovery**

- RTO (Recovery Time Objective): < 4 horas.
- RPO (Recovery Point Objective): < 1 hora.
- Plano de contingência documentado.
- Testes trimestrais de recuperação.

---

## Requisitos Não Funcionais

### RNF - PERFORMANCE

**RNF01 - Tempo de Carregamento da Home**

- Primeira carga: < 2 segundos.
- Navegação subsequente: < 500ms.
- Medido em conexão 3G.
- Lighthouse score > 90.

**RNF02 - Busca de Processos**

- Retorno de resultados: < 3 segundos.
- Até 10.000 processos na base.
- Com até 5 filtros aplicados.

**RNF03 - Geração de Petições por IA**

- Petição básica (2-3 páginas): < 30 segundos.
- Petição complexa (10+ páginas): < 2 minutos.
- Sem degradação com múltiplas requisições simultâneas.

**RNF04 - Usuários Simultâneos**

- Suportar 10.000 usuários ativos simultaneamente.
- Sem degradação de performance.
- Auto-scaling configurado.

**RNF05 - Uptime**

- Disponibilidade: 99.9% (SLA).
- Downtime máximo: 43 minutos/mês.
- Janela de manutenção: domingos 2h-6h.
- Comunicação prévia de manutenções.

### RNF - SEGURANÇA

**RNF06 - Protocolo de Criptografia**

- TLS 1.3 obrigatório.
- Certificado SSL de autoridade confiável.
- HSTS habilitado.
- Desabilitar TLS 1.0 e 1.1.

**RNF07 - Criptografia de Dados**

- AES-256 para dados em repouso.
- Chaves gerenciadas em cofre de segredos na VPS (ex.: Vault ou variáveis protegidas).
- Rotação de chaves anual.
- Backup de chaves em local seguro.

**RNF08 - Autenticação**

- JWT com tempo de expiração: 1 hora (access token).
- Refresh token válido por 7 dias.
- Renovação automática transparente.
- Invalidação em logout.

**RNF09 - Rate Limiting**

- 100 requisições/minuto por usuário.
- 1000 requisições/hora por IP.
- Bloqueio temporário após limite.
- Whitelist para integrações.

**RNF10 - Proteção contra Ataques**

- SQL Injection: prepared statements.
- XSS: sanitização de inputs e CSP headers.
- CSRF: tokens em formulários.
- Auditoria regular com ferramentas automatizadas.

**RNF11 - Web Application Firewall**

- CloudFlare WAF (proxy) + regras no Nginx e fail2ban na VPS.
- Bloqueio de IPs suspeitos.
- Proteção contra bots maliciosos.
- Logs de tentativas de ataque.

**RNF12 - Testes de Penetração**

- Pentest semestral por empresa especializada.
- Correção de vulnerabilidades críticas em 7 dias.
- Vulnerabilidades médias em 30 dias.
- Relatório documentado.

### RNF - ESCALABILIDADE


**RNF13 - Arquitetura de DDDl**

- Serviços independentes e desacoplados.
- Comunicação via API REST e message queue.
- Deployment independente por serviço.
- Falha isolada (não cascata).

**RNF14 - Escalabilidade na VPS**

- Escala vertical da VPS (CPU/RAM) conforme demanda.
- Escala horizontal de containers (réplicas via Docker Compose) dentro da VPS.
- Monitoramento de CPU (> 70%) e requisições como gatilho de upgrade.
- Migração futura para múltiplas VPS quando necessário.

**RNF15 - Load Balancing**

- Nginx como reverse proxy e balanceador entre réplicas de containers.
- Algoritmo: least connections.
- Health checks a cada 30 segundos.
- Failover automático entre réplicas.

**RNF16 - CDN para Assets Estáticos**

- CloudFlare (proxy/CDN) na frente da VPS.
- Cache de imagens, CSS, JS.
- TTL configurável (1 dia padrão).
- Invalidação sob demanda.

### RNF - USABILIDADE

**RNF17 - Design Responsivo**

- Mobile-first approach.
- Breakpoints: 320px, 768px, 1024px, 1440px.
- Testado em iOS (Safari) e Android (Chrome).
- Touch-friendly (botões > 44px).

**RNF18 - Acessibilidade**

- WCAG 2.1 nível AA.
- Navegação por teclado.
- Screen reader compatível.
- Contraste mínimo 4.5:1.
- Alt text em imagens.

**RNF19 - Internacionalização (i18n)**

- Suporte inicial: Português (BR).
- Preparado para: Espanhol, Inglês.
- Textos externalizados.
- Formatação de datas/números por locale.

**RNF20 - Onboarding Interativo**

- Tour guiado no primeiro acesso.
- Tooltips contextuais.
- Vídeos tutoriais.
- Base de conhecimento integrada.

### RNF - MANUTENIBILIDADE

**RNF21 - Cobertura de Testes**

- Testes unitários: > 80%.
- Testes de integração: > 60%.
- Testes E2E: cenários críticos.
- CI/CD com testes automatizados.

**RNF22 - Documentação de API**

- OpenAPI 3.0 (Swagger).
- Gerada automaticamente do código.
- Exemplos de requisição/resposta.
- Ambiente de testes (sandbox).

**RNF23 - Logging Centralizado**

- ELK Stack ou CloudWatch.
- Níveis: DEBUG, INFO, WARN, ERROR.
- Correlation ID por requisição.
- Retenção: 90 dias.

**RNF24 - Monitoramento e Alertas**

- Prometheus + Grafana ou Datadog.
- Métricas: CPU, memória, latência, erros.
- Alertas via PagerDuty ou Slack.
- Dashboards em tempo real.

### RNF - COMPATIBILIDADE

**RNF25 - Navegadores Suportados**

- Chrome 100+.
- Firefox 100+.
- Safari 15+.
- Edge 100+.
- Não suportar Internet Explorer.

**RNF26 - Dispositivos Móveis**

- iOS 14+.
- Android 10+.
- Tablets e smartphones.
- Orientação portrait e landscape.

**RNF27 - Integrações**

- APIs REST seguindo padrão OpenAPI.
- Webhooks com retry automático.
- Compatibilidade retroativa (versionamento).

### RNF - BACKUP E RECUPERAÇÃO

**RNF28 - Backup Automatizado**

- Diário incremental (1h da madrugada).
- Semanal completo (domingo 3h).
- Mensal arquivado (1 ano).
- Teste de restauração mensal.

**RNF29 - Recuperação de Desastres**

- RTO: 4 horas.
- RPO: 1 hora.
- Backup em região diferente (georredundância).
- Runbook documentado e atualizado.

---

## Regras de Negócio

### RN - PROCESSOS

**RN01 - Validação de Número de Processo**

- Seguir padrão CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO.
- Validar dígito verificador.
- Rejeitar números inválidos no cadastro.

**RN02 - Unicidade de Processo**

- Não permitir cadastro duplicado do mesmo número.
- Dentro da mesma organização.
- Sugerir processo existente se tentativa de duplicação.

**RN03 - Status de Processo**

- Ativo: em tramitação normal.
- Suspenso: aguardando evento externo.
- Arquivado: finalizado administrativamente.
- Sentenciado: com decisão definitiva.
- Transições válidas devem ser controladas.

**RN04 - Sincronização com Tribunais**

- Automática: diária às 6h.
- Manual: sob demanda pelo usuário.
- Limitada a 10 sincronizações manuais/dia por usuário.
- Cooldown de 1 hora entre sincronizações do mesmo processo.

**RN05 - Classificação de Movimentações**

- Relevância calculada por algoritmo:
  - Palavras-chave (intimação, prazo, sentença): alta.
  - Juntada de documento, certidão: média.
  - Movimentações internas: baixa.
- Usuário pode recategorizar manualmente.

**RN06 - Arquivamento de Processos**

- Somente se status = sentenciado ou finalizado.
- Não pode ter prazos pendentes.
- Mantém histórico completo.
- Pode ser desarquivado.

**RN07 - Valor da Causa**

- Opcional no cadastro.
- Se informado, usado para cálculos de ROI.
- Atualizado automaticamente se alterado no tribunal.
- Moeda: BRL (Real brasileiro).

### RN - PRAZOS

**RN08 - Cálculo de Prazos Processuais**

- Seguir CPC (Código de Processo Civil).
- Início: dia útil seguinte à intimação.
- Fim: último dia útil.
- Prorrogar se cair em feriado/fim de semana.

**RN09 - Prazo em Dobro**

- Aplicar para litisconsortes com procuradores diferentes.
- Defensoria Pública e Ministério Público.
- Indicação manual obrigatória.

**RN10 - Recesso Forense**

- 20 dez a 20 jan: suspensão de prazos.
- Configurável por tribunal.
- Plantões judiciais não suspendem urgências.

**RN11 - Feriados Municipais**

- Considerar feriado do foro do processo.
- Atualização anual do calendário.
- Fonte: sites oficiais das prefeituras.

**RN12 - Prazo Fatal**

- Prazo marcado como crítico.
- Alertas mais frequentes.
- Não pode ser postergado.
- Destaque visual no calendário.

### RN - DOCUMENTOS

**RN13 - Tamanho Máximo de Upload**

- Por arquivo: 100 MB.
- Por organização, conforme plano:
  - Plano 1 (Autônomo): 15 GB total.
  - Plano 2 (Escritório): 75 GB.
  - Plano 3 (Escritório Plus): 300 GB.
  - Plano 4 (Enterprise): sob consulta.

**RN14 - Formatos Aceitos**

- Documentos: PDF, DOC, DOCX, ODT, RTF.
- Imagens: JPG, PNG, GIF, TIFF.
- Planilhas: XLS, XLSX, ODS.
- Outros: ZIP, RAR (até 50 MB).

**RN15 - Versionamento**

- Nova versão gerada a cada edição.
- Máximo 50 versões por documento.
- Versões antigas podem ser purgadas após 2 anos.

**RN16 - Assinatura Digital**

- ICP-Brasil obrigatória para peticionamento.
- Certificado A1 ou A3.
- Validar cadeia de certificação.
- Armazenar hash do documento assinado.

**RN17 - Compartilhamento Externo**

- Link expira após período definido (1h a 30 dias).
- Rastrear acessos (IP, data/hora).
- Revogar link a qualquer momento.
- Proteger com senha opcional.

### RN - FINANCEIRO

**RN18 - Contratos de Honorários**

- Tipos permitidos: fixo, por hora, êxito, misto.
- Honorários de êxito: percentual entre 10-50%.
- Parcelamento: até 12x.
- Vincular a processo específico ou cliente.

**RN19 - Emissão de Nota Fiscal**

- Obrigatória para recebimentos > R$ 1.000.
- Integração com prefeitura (NF-e).
- Alíquota de ISS conforme município.
- Retenção de IR se aplicável.

**RN20 - Inadimplência**

- Fatura vencida > 30 dias: inadimplente.
- Cobrança automática: 7, 15 e 30 dias após vencimento.
- Juros: 1% ao mês.

---

## Regras de Acesso e Permissões

### RA01 - Hierarquia de Permissões

- **Administrador:** Acesso total a todos os módulos e configurações.
- **Advogado Sênior:** Acesso completo, exceto configurações administrativas.
- **Advogado Júnior:** Acesso a módulos de processos, documentos e pesquisa, com edição limitada.
- **Estagiário:** Acesso de leitura na maioria dos módulos, edição restrita a documentos e tarefas.
- **Cliente:** Acesso apenas ao portal do cliente, com dados restritos aos seus processos.

### RA02 - Controle Granular

- Permissões configuráveis por módulo (ex: processos, documentos, financeiro).
- Ações específicas: criar, ler, atualizar, deletar.
- Permissões por processo individual (ex: apenas processos atribuídos).

### RA03 - Auditoria de Acessos

- Todas as ações registradas com: usuário, IP, timestamp, ação realizada.
- Logs acessíveis apenas por administradores.
- Retenção mínima de 5 anos (LGPD).

### RA04 - Autenticação Multifator

- Obrigatória para administradores e advogados sêniores.
- Opcional para outros perfis.
- Suporte a TOTP (Google Authenticator) e SMS.

### RA05 - Certificado Digital

- Login com certificado ICP-Brasil opcional para advogados.
- Obrigatório para peticionamento em tribunais.

---

## Casos de Uso

### UC01 - Cadastro de Processo

**Ator:** Advogado Sênior, Advogado Júnior.

- **Pré-condição:** Usuário autenticado com permissão.
- **Fluxo Principal:**
  1. Usuário acessa módulo de processos.
  2. Seleciona "Cadastrar Processo".
  3. Insere número CNJ ou busca automaticamente.
  4. Preenche campos: tribunal, vara, partes, valor da causa.
  5. Sistema valida número CNJ e unicidade.
  6. Processo é salvo e sincronizado com tribunal.
- **Pós-condição:** Processo cadastrado e visível na lista.

### UC02 - Geração de Petição

**Ator:** Advogado Sênior, Advogado Júnior (com supervisão).

- **Pré-condição:** Processo cadastrado.
- **Fluxo Principal:**
  1. Usuário seleciona processo.
  2. Escolhe "Gerar Petição".
  3. Informa tipo de ação, fatos, pedidos.
  4. IA gera petição com base nos inputs.
  5. Usuário revisa e edita.
  6. Petição é salva e anexada ao processo.
- **Pós-condição:** Petição gerada e pronta para protocolo.

### UC03 - Acompanhamento de Prazo

**Ator:** Advogado Sênior, Advogado Júnior, Estagiário.

- **Pré-condição:** Processo com movimentação recente.
- **Fluxo Principal:**
  1. Sistema detecta nova movimentação com prazo.
  2. Calcula prazo automaticamente (CPC, feriados).
  3. Notifica usuário via canais configurados.
  4. Usuário visualiza prazo no calendário.
  5. Marca como concluído após cumprimento.
- **Pós-condição:** Prazo registrado como cumprido.

### UC04 - Visualização de Processos pelo Cliente

**Ator:** Cliente.

- **Pré-condição:** Cliente autenticado no portal.
- **Fluxo Principal:**
  1. Cliente acessa portal do cliente.
  2. Visualiza lista de seus processos.
  3. Seleciona processo para ver movimentações.
  4. Faz download de documentos autorizados.
  5. Envia mensagem ao advogado via chat.
- **Pós-condição:** Cliente informado sobre seu processo.

---

## Sistemas Externos

### SE01 - Tribunais

- **Sistemas:** PJe, e-SAJ, PROJUDI, DataJud.
- **Interação:** Consulta de processos, download de documentos, peticionamento.
- **Método:** APIs REST (quando disponível) ou web scraping.
- **Autenticação:** Certificado digital ICP-Brasil.

### SE02 - Inteligência Artificial

- **Sistemas:** OpenAI (GPT-4), Anthropic (Claude 3.5).
- **Interação:** Geração de documentos, análise preditiva, chatbot.
- **Método:** APIs REST com autenticação via API Key.

### SE03 - Pagamentos

- **Sistemas:** Stripe, PagSeguro, Mercado Pago.
- **Interação:** Geração de boletos, PIX, pagamento com cartão.
- **Método:** APIs REST com autenticação segura.

### SE04 - Comunicação

- **Sistemas:** WhatsApp Business API, SendGrid, Twilio.
- **Interação:** Envio de notificações e alertas.
- **Método:** APIs REST e SMTP.

### SE05 - Armazenamento

- **Sistemas:** Filesystem da VPS (diretórios por empresa); destino externo apenas para backup.
- **Interação:** Armazenamento local de documentos e backup criptografado externo.
- **Método:** Acesso direto ao filesystem pelo backend; rotinas de backup agendadas.

---

## Arquitetura do Sistema

### Visão Geral

- **Modelo:** Arquitetura Hexagonal.

- **Hospedagem:** VPS única com Docker Compose (frontend, backend, workers, Redis, Nginx); banco de dados e IA externos.
- **Escalabilidade:** Escala vertical da VPS + réplicas de containers.
- **Segurança:** Criptografia end-to-end, WAF (CloudFlare/Nginx), autenticação robusta.

### Componentes

- **Frontend:** Next.js + React + TypeScript (web), React Native (mobile) — hospedado na VPS.
- **Backend:** Python/FastAPI (auth, process, AI, document, etc.) — hospedado na VPS.
- **Reverse Proxy:** Nginx na VPS (TLS, roteamento, load balancing).
- **Banco de Dados:** PostgreSQL gerenciado externo (estruturado), Redis na VPS (cache e filas).
- **Armazenamento de Documentos:** Filesystem da VPS com diretórios isolados por empresa.
- **Serviços Externos:** Banco PostgreSQL gerenciado e APIs de IA (OpenAI/Anthropic).
- **Monitoramento:** Prometheus + Grafana na VPS.

---

## Tecnologias Utilizadas

### Frontend

- **Next.js:** Framework React para interfaces web (SSR/SSG).
- **React 18:** Biblioteca de componentes.
- **TypeScript:** Tipagem estática para maior robustez.
- **React Native:** Apps iOS e Android.
- **Tailwind CSS:** Estilização responsiva.

### Backend


- **Python, FastAPI:** API assíncrona, performance e escalabilidade.
- **JWT:** Autenticação de APIs.

### Banco de Dados

- **PostgreSQL 15 (externo):** Dados estruturados em banco gerenciado fora da VPS.
- **Redis 7 (na VPS):** Cache e filas.

### Infraestrutura

- **VPS:** Hospedagem de frontend, backend, workers, Redis e Nginx (Docker Compose).
- **PostgreSQL gerenciado externo:** Banco de dados fora da VPS.
- **Filesystem da VPS:** Armazenamento de documentos em diretórios por empresa.
- **CloudFlare:** CDN/proxy e WAF na frente da VPS.
- **GitHub Actions:** CI/CD com deploy na VPS.
- **Prometheus + Grafana:** Monitoramento.
- **Logs estruturados:** Centralizados na VPS.

---

## Modelo de Dados

### Entidades Principais

- **Organização:** Dados do escritório (CNPJ, nome, plano).
- **Usuário:** Nome, e-mail, OAB, perfil, permissões.
- **Processo:** Número CNJ, tribunal, vara, partes, status, valor da causa.
- **Documento:** Nome, tipo, versão, hash, processo vinculado.
- **Prazo:** Data inicial, data final, tipo, processo, responsável.
- **Honorário:** Tipo, valor, parcelas, cliente, processo.
- **Notificação:** Tipo, canal, destinatário, conteúdo, status.
- **Evento:** Tipo (audiência, reunião), data, participantes, processo.

### Relacionamentos

- Organização 1:N Usuários.
- Processo 1:N Documentos, Prazos, Eventos.
- Usuário 1:N Processos (responsável).
- Cliente 1:N Processos, Honorários.
- Notificação N:1 Processo, Usuário.

---

## Segurança e Compliance

### Segurança

- **Criptografia:** AES-256 (repouso), TLS 1.3 (trânsito).
- **Autenticação:** JWT, 2FA, SSO (SAML 2.0).
- **WAF:** CloudFlare WAF + regras Nginx/fail2ban na VPS.
- **Logs:** Imutáveis, retidos por 5 anos.

### LGPD

- Termo de consentimento no cadastro.
- Portal de privacidade para portabilidade/exclusão de dados.
- Anonimização de dados sensíveis.
- Backup criptografado e georredundante.
- Resposta a solicitações em 15 dias úteis.

---

## Modelo de Negócio

### Modelo de Receita

Todos os planos incluem **100% das funcionalidades** da plataforma. A diferença entre eles está apenas nos **limites de quantidade e uso** (usuários, processos ativos, armazenamento e gerações de IA). Limites definidos com base na média de mercado de ~250 processos por advogado e nos planos praticados por concorrentes (Astrea, ADVBOX).

| Plano | Público | Usuários | Processos ativos | Armazenamento | Gerações de IA/mês | Preço |
|---|---|---|---|---|---|---|
| **Plano 1 - Autônomo** | Advogados autônomos | 1 | 250 | 15 GB | 50 | R$ 189/mês |
| **Plano 2 - Escritório** | Pequenos escritórios (2-5 advogados) | até 5 | 1.250 | 75 GB | 250 | R$ 499/mês |
| **Plano 3 - Escritório Plus** | Médios escritórios (6-20 advogados) | até 20 | 5.000 | 300 GB | 1.000 | R$ 1.490/mês |
| **Plano 4 - Enterprise** | Grandes escritórios e departamentos jurídicos | 20+ | ilimitado | sob consulta | sob consulta | Preço sob consulta |

- **Excedentes (pay-per-use):** uso acima dos limites cobrado por consumo, ex.: pacote adicional de processos ativos e geração de petição avulsa.
- **Upgrade:** mudança de plano a qualquer momento, com cobrança proporcional.
- **Contratação anual:** desconto sobre o valor mensal (a definir, mercado pratica ~15-17%).

### Estratégia de Crescimento

- Marketing digital focado em advogados autônomos.
- Parcerias com OABs estaduais.
- Webinars e trials gratuitos.
- Expansão para América Latina (2027).

---

## Estrutura do Repositório

- **`frontend/`** — Aplicação web em Next.js 16 + React 19 + TypeScript + Tailwind CSS v4, contendo a **landing page** do JuriSense (hero, funcionalidades, planos, FAQ e contato). Inclui `Dockerfile` multi-stage otimizado (build standalone + runtime distroless, sem shell e não-root).
- **`backend/`** — API em Python/FastAPI (a implementar).
- **`docs/`** — Documentação de arquitetura (`IMPLEMENTACAO_ARQUITETURA/`) e diagramas PlantUML (`diagramas/`).
- **`JuriSense_frontend/`** — Protótipo legado em Vite + React (substituído pelo `frontend/` em Next.js; mantido como referência de componentes e assets).

### Comandos do Frontend

```bash
cd frontend

# Desenvolvimento (http://localhost:3000)
npm run dev

# Build de producao (output standalone)
npm run build

# Lint
npm run lint

# Build da imagem Docker otimizada
docker build -t jurisense-frontend .
docker run -p 3000:3000 jurisense-frontend
```

---

## Instrucoes de Operacao

### Arquitetura de Fila (Celery + RabbitMQ)

O sistema utiliza Celery com RabbitMQ para operacoes assincronas:

- **emails**: Envio de emails transacionais (verificacao, convites, recuperacao de senha)
- **ocr**: Processamento OCR de documentos
- **uploads**: Processamento de uploads pesados
- **maintenance**: Limpeza de dados expirados (convites, logs antigos)
- **default**: Tarefas gerais

### Comandos de Operacao

```bash
# Iniciar todos os servicos (dev)
docker-compose up -d

# Ver status do RabbitMQ (management UI)
# http://localhost:15672 (schemajud / schemajud_secret)

# Ver status dos workers Celery
docker-compose logs -f celery_worker

# Iniciar flower (monitoramento Celery)
celery -A config.celery flower --port=5555

# Executar tarefas periodicas manualmente
celery -A config.celery call apps.accounts.tasks.cleanup_expired_invites_task

# Escala de workers (producao)
docker-compose up -d --scale celery_worker=3
```

### Feature Flags

| Variavel | Default |Descricao |
|---|---|---|
| `USE_CELERY_EMAILS` | `true` | Envia emails via fila Celery |
| `USE_ASYNC_DB` | `false` | Usa pool async de banco de dados |

### Monitoramento

- **RabbitMQ Management**: `http://localhost:15672`
- **Health check**: `GET /api/health` (endpoint de health check do FastAPI)
- **Sentry**: Configurado via `SENTRY_DSN` em producao

### Testes

```bash
# Testes unitarios
pytest apps/accounts/tests/test_tasks.py -v
pytest apps/accounts/tests/test_audit_logs_endpoint.py -v

# Testes com coverage
pytest --cov=apps --cov-report=html

# Tests async
pytest --asyncio-mode=auto
```

---

