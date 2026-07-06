# PLANO DE HOSPEDAGEM GCP - JURISENSE

## Objetivo

Definir como hospedar, na Google Cloud Platform, os componentes centrais do JuriSense:

1. Backend
2. Frontend
3. Domínio e DNS
4. Documentos e arquivos
5. Serviços de apoio para escala, segurança e operação

Este plano busca equilíbrio entre simplicidade inicial, baixo risco operacional e caminho claro de crescimento.

---

## 1) Diretriz Principal

A proposta é usar a GCP como base principal da infraestrutura de produção, com serviços gerenciados sempre que possível.

### Princípios

1. Menos servidor manual, mais serviços gerenciados.
2. Backend stateless e escalável.
3. Frontend distribuído via CDN quando possível.
4. Documentos em object storage, nunca no disco da aplicação.
5. DNS centralizado e controlado pela GCP.
6. Processos pesados e integrações síncronas reduzidas ao mínimo.

---

## 2) Arquitetura Recomendada

### Visão resumida

1. Domínio: Cloud DNS.
2. Backend: Cloud Run.
3. Frontend: Cloud Storage + Cloud CDN, ou Cloud Run se houver SSR.
4. Banco de dados: Cloud SQL PostgreSQL.
5. Documentos: Cloud Storage.
6. Jobs assíncronos: Pub/Sub + Cloud Run Jobs/Workers.
7. Segredos e credenciais: Secret Manager.
8. Logs e métricas: Cloud Logging + Cloud Monitoring.

### Topologia sugerida

```text
Usuário
  ↓
Cloud DNS
  ↓
HTTPS Load Balancer / CDN
  ├── Frontend estático (Cloud Storage + CDN)
  └── Backend API (Cloud Run)
        ├── Cloud SQL (PostgreSQL)
        ├── Cloud Storage (documentos)
        ├── Pub/Sub / Jobs assíncronos
        └── IA / integrações externas
```

---

## 3) Backend

### Serviço recomendado: Cloud Run

#### Por que Cloud Run

1. Escala automática conforme demanda.
2. Custo por uso, sem manter VM ociosa.
3. Deploy simples via container.
4. Bom encaixe para APIs REST/GraphQL e workers leves.
5. Integração nativa com Cloud SQL, Secret Manager, Pub/Sub e Logging.

### Quando usar Cloud Run Jobs ou workers

1. Processamento de documentos.
2. OCR e extração estruturada.
3. Geração de embeddings.
4. Rotinas de IA demoradas.

### Requisitos do backend

1. Stateless.
2. Timeout e retries controlados.
3. Variáveis sensíveis fora do código.
4. Logs estruturados.
5. Rate limiting e autenticação centralizados.

### Alternativa futura

Se o backend crescer muito em complexidade operacional, a migração para GKE pode ser considerada, mas não é a escolha inicial.

---

## 4) Frontend

### Cenário A: Frontend SPA estático

Se o frontend for React/Vite/Next exportado como estático:

1. Hospedar em Cloud Storage.
2. Distribuir via Cloud CDN.
3. Proteger com HTTPS Load Balancer.

### Cenário B: Frontend com SSR/Server Components

Se o frontend precisar de renderização server-side:

1. Hospedar em Cloud Run.
2. Publicar via domínio próprio com HTTPS Load Balancer.
3. Cachear assets estáticos no CDN.

### Recomendação prática

1. Se a primeira versão for institucional + dashboard web simples, usar Cloud Storage + CDN.
2. Se houver SSR, usar Cloud Run desde o início.

### Regra de decisão

1. Frontend simples e previsível: estático.
2. Frontend com autenticação complexa e renderização dinâmica: Cloud Run.

---

## 5) Domínio e DNS

### Serviço recomendado: Cloud DNS

#### Papel do Cloud DNS

1. Gerenciar zona DNS do domínio.
2. Apontar subdomínios para frontend e backend.
3. Centralizar registros A, CNAME, TXT e MX, se necessário.

### Organização sugerida

1. `app.dominio.com` para frontend.
2. `api.dominio.com` para backend.
3. `docs.dominio.com` para área pública de documentos, se existir.
4. `admin.dominio.com` para painel interno, se houver.

### SSL/TLS

1. Certificados gerenciados pelo HTTPS Load Balancer.
2. Forçar HTTPS em todos os subdomínios.
3. Renovação automatizada pela própria GCP.

### Observação importante

Se o domínio estiver registrado fora da GCP, ele pode continuar onde está. O importante é que a zona DNS passe a ser gerenciada no Cloud DNS.

---

## 6) Documentos e Arquivos

### Serviço recomendado: Cloud Storage

#### O que vai para Cloud Storage

1. PDFs enviados por clientes.
2. Documentos OCR processados.
3. Versões de peças e anexos.
4. Arquivos exportados e relatórios.
5. Backups e arquivos de retenção.

### Estrutura de buckets sugerida

1. Bucket para uploads brutos.
2. Bucket para documentos processados.
3. Bucket para exportações e relatórios.
4. Bucket para arquivos de backup e retenção.

### Boas práticas

1. Versionamento habilitado.
2. Criptografia padrão da GCP.
3. Regras de lifecycle para arquivamento.
4. Controle de acesso por IAM e signed URLs quando necessário.
5. Separação entre documentos públicos e sigilosos.

### Quando usar Cloud Storage em vez de banco

1. Sempre que o conteúdo for binário ou volumoso.
2. Sempre que houver necessidade de retenção e versionamento.
3. Sempre que o arquivo for tratado como ativo documental, não como registro relacional.

---

## 7) Banco e Dados Operacionais

### Serviço recomendado: Cloud SQL PostgreSQL

#### Uso principal

1. Usuários.
2. Processos.
3. Tarefas.
4. Prazos.
5. Auditoria operacional.
6. Metadados dos documentos.

### Decisão de arquitetura

1. Dados transacionais no PostgreSQL.
2. Arquivos no Cloud Storage.
3. Dados de processamento e eventos em Pub/Sub ou tabelas auxiliares.

---

## 8) Filas e Processamento Assíncrono

### Serviços recomendados

1. Pub/Sub para eventos e desacoplamento.
2. Cloud Run Jobs ou workers para execução de tarefas.
3. Cloud Tasks quando houver agendamento/retry controlado por chamada HTTP.

### Casos de uso

1. OCR de documentos.
2. Geração de embeddings.
3. Resumo de peças longas.
4. Envio de notificações.
5. Rotinas de IA com maior latência.

### Objetivo

1. Não travar a API em tarefas pesadas.
2. Diminuir custo de pico.
3. Melhorar experiência do usuário.

---

## 9) Segurança

### Serviços e controles

1. Secret Manager para segredos.
2. IAM por menor privilégio.
3. Cloud Armor se houver necessidade de proteção adicional.
4. Cloud Logging para auditoria.
5. Criptografia em repouso e em trânsito.

### Controles essenciais

1. Separar ambientes de dev, staging e produção.
2. Proteger bucket de documentos com política restrita.
3. Manter logs de acesso e mutação.
4. Validar acesso a documentos por tenant/cliente.

---

## 10) Observabilidade e Operação

### O que monitorar

1. Latência da API.
2. Taxa de erro.
3. Tempo de processamento de documentos.
4. Uso de storage.
5. Custo mensal por serviço.
6. Volume de requisições por ambiente.

### Ferramentas

1. Cloud Monitoring.
2. Cloud Logging.
3. Alertas por custo, erro e saturação.

---

## 11) Plano de Implantação por Fase

### Fase 1 - MVP funcional

1. Criar projeto GCP e estrutura de billing.
2. Configurar Cloud DNS e HTTPS.
3. Publicar frontend.
4. Publicar backend em Cloud Run.
5. Provisionar Cloud SQL PostgreSQL.
6. Criar buckets de documentos.
7. Configurar Secret Manager.
8. Ativar logs e alertas básicos.

### Fase 2 - Operação estável

1. Adicionar fila assíncrona.
2. Separar workers de processamento.
3. Criar política de lifecycle para documentos.
4. Implantar observabilidade de custo.
5. Adicionar cache e rate limiting.

### Fase 3 - Escala

1. Ajustar autoscaling.
2. Separar workloads críticos.
3. Introduzir CDN mais agressivo.
4. Refinar retenção de documentos.
5. Avaliar otimização de custos por serviço.

---

## 12) Estimativa de Custo Inicial

Sem volume real, a recomendação é começar enxuto e pagar por uso.

### Componentes que mais influenciam custo

1. Cloud SQL.
2. Cloud Run.
3. Cloud Storage.
4. Tráfego de rede e CDN.
5. Processamento de IA.

### Diretriz prática

1. Frontend estático tende a ser barato.
2. Backend em Cloud Run tende a ser eficiente no início.
3. Cloud SQL deve ser dimensionado com cuidado.
4. O maior risco de custo costuma vir de IA e documentos em grande volume.

---

## 13) Decisão Recomendada Para o JuriSense

### Recomendação final de hospedagem

1. Backend em Cloud Run.
2. Frontend em Cloud Storage + Cloud CDN, se for estático; Cloud Run se precisar de SSR.
3. Domínio e DNS em Cloud DNS.
4. Documentos em Cloud Storage com versionamento e lifecycle.
5. Banco em Cloud SQL PostgreSQL.
6. Jobs assíncronos em Pub/Sub + Cloud Run Jobs/workers.

### Motivo

Essa combinação entrega:

1. Menor complexidade operacional.
2. Boa escalabilidade.
3. Baixo custo inicial.
4. Caminho claro para crescer sem refazer a arquitetura.

---

## 14) Próxima Etapa

Após validar este plano, o próximo passo é detalhar:

1. Estrutura de projetos e ambientes na GCP.
2. Domínios e subdomínios oficiais.
3. Pipeline de CI/CD.
4. Dimensionamento inicial dos serviços.
5. Política de backup, retenção e recuperação.

---

Data: 21 de abril de 2026  
Projeto: JuriSense  
Documento: Planejamento de Hospedagem GCP