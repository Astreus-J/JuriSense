# BRIEFING TÉCNICO - IA JURISENSE (PARA ESPECIALISTA)

## Objetivo Deste Documento

Consolidar, de forma objetiva, o que o JuriSense quer implementar em IA, quais decisões técnicas precisam ser tomadas, e qual estratégia de custo/escala é mais viável para o momento do produto.

Este briefing deve servir como base para uma reunião técnica e para definição da arquitetura final de IA.

---

## 1) Contexto do Produto

O JuriSense é uma plataforma jurídica com foco em automação operacional para advogados e escritórios. A IA é um componente central para reduzir trabalho manual, aumentar qualidade técnica e escalar atendimento.

### Principais dores que queremos resolver

1. Tempo excessivo com tarefas repetitivas (triagem, leitura, organização e resumo de documentos).
2. Baixa padronização de peças e análises entre profissionais.
3. Dificuldade em transformar grande volume documental em informação acionável.
4. Crescimento de custo operacional conforme aumento de clientes.

---

## 2) O Que Queremos Que a IA Faça

### 2.1 Casos de uso prioritários (MVP)

1. Classificação automática de documentos jurídicos.
2. Extração estruturada de dados relevantes (partes, prazos, valores, números processuais, pedidos).
3. Resumo técnico de documentos e andamentos processuais.
4. Apoio à geração de minutas de petições com base em dados do caso.
5. Busca semântica em base jurídica interna (RAG com jurisprudência/documentos).

### 2.2 Casos de uso de segunda fase

1. Jurimetria (probabilidade de êxito e sinalização de risco).
2. Sugestões de estratégia processual com explicações.
3. Auditoria automática de coerência de peças geradas.

### 2.3 Limites de atuação da IA

1. A IA não substitui decisão técnica do advogado.
2. Todo output jurídico sensível deve passar por revisão humana.
3. O sistema deve preservar rastreabilidade (prompt, contexto e resposta).

---

## 3) Cenário Técnico Atual Desejado

## 3.1 Infraestrutura e plataforma (visão inicial)

1. Frontend e domínio público: Hostinger.
2. Banco relacional e autenticação: Supabase (ou alternativa equivalente em PostgreSQL gerenciado).
3. Armazenamento de documentos: provedor de object storage com baixo custo (Supabase Storage, Cloudflare R2, GCS ou S3).
4. Backend API e orquestração de IA: serviço dedicado com deploy contínuo.

## 3.2 Dúvida central

Definir a melhor estratégia de IA entre:

1. Uso predominante de APIs de terceiros (OpenAI/Anthropic/Google/Hugging Face Inference).
2. Self-host de modelos open source (Hugging Face) em cloud (ex.: GCP).
3. Modelo híbrido (API para tarefas complexas + self-host para tarefas repetitivas/alto volume).

---

## 4) Critérios de Decisão Para Arquitetura de IA

A decisão deve priorizar viabilidade econômica e operacional para startup em crescimento.

### Critérios obrigatórios

1. Custo por requisição e custo por cliente ativo.
2. Escalabilidade sem explosão de custo em picos.
3. Latência aceitável por tipo de tarefa.
4. Facilidade de operação (MLOps, monitoramento, fallback).
5. Segurança e conformidade com LGPD (dados sensíveis jurídicos).
6. Possibilidade de migração progressiva sem reescrever todo o backend.

---

## 5) Hipótese de Arquitetura Preferida (Para Validação)

## 5.1 Estratégia recomendada inicialmente

Modelo híbrido progressivo:

1. API externa para geração textual jurídica complexa (maior qualidade).
2. Modelos menores e mais baratos para classificação/extração quando possível.
3. Camada interna "AI Gateway" para abstrair provedores e evitar lock-in.

## 5.2 AI Gateway (requisito chave)

Criar um serviço interno que:

1. Recebe todas as chamadas de IA do produto.
2. Roteia para modelos/provedores por tipo de tarefa.
3. Registra custo por feature, cliente e operação.
4. Implementa fallback automático entre provedores.
5. Permite troca de provedor sem alterar frontend/domínio.

## 5.3 Processamento assíncrono

Tarefas pesadas devem rodar em fila:

1. OCR e parsing documental.
2. Indexação e embeddings.
3. Geração longa de peças.

Objetivo: evitar timeouts, melhorar experiência e controlar picos de custo.

---

## 6) Custos: Diretriz de Avaliação

Não buscamos o menor custo unitário isolado, e sim o melhor custo total com confiabilidade.

### 6.1 O que queremos medir mensalmente

1. Custo total de IA (por provedor e por tarefa).
2. Custo por 1.000 requisições por tipo de operação.
3. Custo médio por cliente ativo.
4. Margem por plano comercial.

### 6.2 Regra de migração para self-host

Uma tarefa só migra para self-host quando:

1. Representa parcela relevante do custo total de IA.
2. Tem alto volume previsível.
3. Mantém qualidade adequada com modelo open source.
4. O custo operacional de manter GPU/infra é justificado.

---

## 7) Requisitos Não Funcionais

1. Observabilidade completa (latência, erro, custo, token usage, throughput).
2. Versionamento de prompts e rastreabilidade de respostas.
3. Controles por tenant (rate limit, quota, budget).
4. Criptografia em trânsito e em repouso.
5. Auditoria para compliance jurídico e LGPD.
6. Estratégia de cache para reduzir chamadas repetidas.

---

## 8) Riscos Mapeados

1. Explosão de custo variável com crescimento de base.
2. Dependência excessiva de um único provedor.
3. Queda de qualidade em tarefas críticas se roteamento estiver inadequado.
4. Complexidade operacional precoce ao tentar self-host cedo demais.
5. Risco regulatório por tratamento de dados sensíveis sem governança robusta.

---

## 9) O Que Precisamos do Especialista

Esperamos uma proposta objetiva com:

1. Arquitetura alvo de IA para 12 meses (fases: curto, médio e escala).
2. Recomendação clara entre API, self-host e híbrido para cada caso de uso.
3. Estimativa de custo em 3 cenários de crescimento (baixo, médio, alto).
4. Plano de implementação do AI Gateway e do roteamento de modelos.
5. Estratégia de observabilidade financeira e técnica.
6. Estratégia de segurança/LGPD para pipeline de IA.
7. Critérios de "go/no-go" para migrar workloads específicos para self-host.

---


Data: 21 de abril de 2026  
Projeto: JuriSense  
Documento: Briefing para Especialista de IA