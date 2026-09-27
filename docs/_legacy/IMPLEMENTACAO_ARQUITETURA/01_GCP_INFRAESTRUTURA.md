# ☁️ GCP INFRAESTRUTURA: DESIGN CLOUD-NATIVE

## Introdução: A Nuvem como Plataforma

A escolha da Google Cloud Platform para hospedar o JuriSense não é apenas uma decisão técnica, mas estratégica. A GCP oferece primitivos de computação, armazenamento e IA que permitem construir sistemas altamente escaláveis, resilientes e economicamente eficientes. Este documento descreve a filosofia, arquitetura e decisões de design que guiam nossa implementação na GCP.

## Filosofia: 12-Factor App e Cloud-Native

### Os Doze Fatores Aplicados ao JuriSense

Fundamentamos nossa arquitetura nos doze fatores descritos por Heroku, adaptados para a GCP:

1. **Codebase:** Um único repositório Git com versionamento semântico
2. **Dependências:** Explícitas em `requirements.txt` e `package.json`
3. **Configuração:** Via variáveis de ambiente (não hardcoded)
4. **Backing Services:** Serviços externos tratados como recursos anexados (BD, Filas, APIs)
5. **Build, Release, Run:** Separação clara com CI/CD pipeline
6. **Processos:** Stateless, sem dependência de sessão local
7. **Port Binding:** Serviço expõe-se via porta (não depende de servidor web externo)
8. **Concorrência:** Múltiplos processos independentes
9. **Descartabilidade:** Inicia rápido, encerra gracefully
10. **Paridade Dev/Prod:** Ambiente local emula produção
11. **Logs:** Enviados para stdout, agregados por GCP
12. **Admin Tasks:** Scripts uma vez executáveis, não permanentes

### Implicações Práticas no JuriSense

- **Backend Django** é stateless; sessões em Redis (GCP Memorystore)
- **Celery workers** são efêmeros; enfileiramento via Google Cloud Tasks ou Pub/Sub
- **Banco de dados** é serviço gerenciado (Cloud SQL); schema versionado
- **Configuração** vem de Secret Manager (não de arquivos)
- **Logs** estruturados em JSON e enviados a Cloud Logging
- **Deployments** automáticos via Cloud Build + Cloud Deploy

---

## Arquitetura de Serviços na GCP

### Topologia de Componentes

```
┌──────────────────────────────────────────────────────────┐
│               INTERNET / LOAD BALANCER                     │
└──────────────────┬───────────────────────────────────────┘
                   │
      ┌────────────┼────────────┐
      │            │            │
      │            │            │
  ┌───▼───┐   ┌───▼────┐   ┌──▼────┐
  │ Cloud │   │ Cloud  │   │ Cloud │
  │ Run   │   │ Run    │   │ SQL   │
  │(API)  │   │(Worker)│   │(BD)   │
  └───┬───┘   └───┬────┘   └───────┘
      │           │
      │    ┌──────┼──────┐
      │    │      │      │
  ┌───▼────▼──┐ ┌▼─────┐ ┌─────────┐
  │Pub/Sub    │ │Cloud │ │Cloud    │
  │(Messaging)│ │Tasks │ │Storage  │
  └───────────┘ └──────┘ │(Docs)   │
                         └─────────┘
                              │
                         ┌────▼────┐
                         │Firestore│
                         │(NoSQL)  │
                         └─────────┘
```

### Seleção de Serviços

#### **Cloud Run (Backend e Workers)**
- **Por que:** Serverless, escala automaticamente, paga por execução
- **Uso:** Hospedagem da API Django, background jobs
- **Decisão:** Cloud Run sobre App Engine por maior controle e containers

#### **Cloud SQL (Banco Relacional)**
- **Por que:** PostgreSQL gerenciado, backups automáticos, replicação
- **Uso:** Dados estruturados (Usuários, Processos, Documentos, Prazos)
- **Decisão:** Replicação alta disponibilidade (HA) em produção

#### **Firestore (NoSQL)**
- **Por que:** Escalabilidade horizontal, queries em tempo real, síncrono
- **Uso:** Cache de análises, documentos jurídicos estruturados em alta concorrência
- **Decisão:** Usado seletivamente para dados que não precisam de transações ACID

#### **Cloud Storage (Object Storage)**
- **Por que:** Escalabilidade ilimitada, custo baixo, integração com IA
- **Uso:** Armazenamento de PDFs, documentos OCR-processados, versões
- **Decisão:** Bucket com versionamento habilitado

#### **Pub/Sub (Message Queue)**
- **Por que:** Pub/Sub desacoplado, escalável, garantia at-least-once
- **Uso:** Fila de processamento (OCR, IA), eventos de negócio
- **Decisão:** Alternativa a RabbitMQ; integra-se melhor com GCP

#### **Cloud Tasks (Scheduler de Tarefas)**
- **Por que:** Retry automático, rate limiting, agendamento
- **Uso:** Lembretes de prazos, processamento em batch
- **Decisão:** Para tarefas agendadas, não críticas

#### **Vertex AI (ML Managed)**
- **Por que:** Modelos pré-treinados, fine-tuning, deployment automático
- **Uso:** Modelos preditivos de jurimetria, OCR custom
- **Decisão:** Complementa OpenAI GPT-4 para tarefas específicas

---

## Estratégia de Dados

### Modelo de Dados Multi-Camadas

```
┌────────────────────────────────────────┐
│     Aplicação (Lógica de Negócio)      │
└────────────────────────────────────────┘
           │         │          │
      ┌────▼─┐   ┌───▼──┐   ┌──▼────┐
      │Cache │   │ Hot  │   │Archive│
      │(Redis)   │Data  │   │(GCS)  │
      │      │   │(SQL) │   │       │
      └──────┘   └──────┘   └───────┘
```

#### **Camada 1: Cache (Redis / Memorystore)**
- Sessões de usuário (JWT tokens, permissões)
- Resultados de cálculos custosos (jurimetria)
- Rate limiting e throttling
- **TTL:** 1h a 24h dependendo do tipo

#### **Camada 2: Hot Data (Cloud SQL)**
- Modelos centrais do domínio
- Transações ACID críticas
- Queries frequentes
- **Replicação:** HA com failover automático

#### **Camada 3: Warm Data (Firestore)**
- Documentos jurídicos processados
- Análises de casos históricos
- Dados de alta concorrência
- **Índices:** Criados automaticamente

#### **Camada 4: Cold Data (Cloud Storage)**
- PDFs originais (archive)
- Backups de dados antigos
- Logs históricos
- **Classe:** Nearline (acesso raro)

### Estratégia de Backup e Recovery

1. **Backups Automáticos**
   - Cloud SQL: 30 dias retenção
   - Cloud Storage: Versionamento habilitado
   - Firestore: Snapshots diários

2. **Disaster Recovery**
   - RTO (Recovery Time Objective): < 4 horas
   - RPO (Recovery Point Objective): < 1 hora
   - Teste trimestral de restauração

---

## Resilência, Escalabilidade e Disaster Recovery

### Padrões de Resilência

#### **Circuit Breaker (para APIs Externas)**
```
Sucesso > Limite
         ↓
      CLOSED → chamadas fluem
         ↓
Falhas > Limite
         ↓
      OPEN → chamadas retornam erro
         ↓
Timeout
         ↓
   HALF-OPEN → teste chamada
         ↓
   ↙ Sucesso        Falha ↘
CLOSED              OPEN
```

#### **Retry com Backoff Exponencial**
- Primeira tentativa: imediata
- Segunda: 1s + jitter
- Terceira: 2s + jitter
- Máximo: 5 tentativas em 32s

#### **Bulkhead Pattern**
- Pools de conexão isolados
- Semáforos por operação crítica
- Threads separadas para I/O

### Escalabilidade

#### **Horizontal (mais instâncias)**
- Cloud Run: Autoscale 0-1000 instâncias
- Load Balancer distribui tráfego
- Celery workers em Cloud Run efêmeros

#### **Vertical (máquinas maiores)**
- Cloud SQL: Upgrade de CPU/RAM sem downtime
- Memorystore: Redimensionamento com pequena janela

#### **Caching Agressivo**
- Browser: 1 dia para assets estáticos
- CDN: 1 hora para respostas de API
- Backend: 5 minutos para análises custosas

### Disaster Recovery

| Cenário | RTO | Estratégia |
|---------|-----|-----------|
| Falha de Banco | 5 min | Failover automático HA |
| Região Indisponível | 30 min | Restore de backup em outra região |
| Data Corruption | 1 hora | Point-in-time restore |
| DDoS | < 1 min | Cloud Armor + DDoS protection |

---

## Custo-Benefício e Otimizações

### Modelo de Custo

**Estimativa mensal (para 1.000 advogados):**

- **Cloud Run (API):** $500-1000 (conforme tráfego)
- **Cloud SQL:** $300-500 (pequena instância)
- **Pub/Sub:** $200-300 (conforme mensagens)
- **Cloud Storage:** $100-200 (armazenamento)
- **Firestore:** $100-300 (conforme leitura/escrita)
- **IA/Vertex:** $1000-2000 (chamadas de modelo)
- **Networking/Outros:** $200-400

**Total:** ~$2500-5000/mês

### Otimizações

1. **Instâncias Preemptivas**
   - Workers Celery usam preemptive VMs (70% desconto)
   - Backup automático em caso de interrupção

2. **Reserved Capacity**
   - Cloud SQL: Reserve instância para 1 ano (-30% custo)
   - Memorystore: Reserve nós (-25% custo)

3. **Rate Limiting na IA**
   - Batch chamadas a GPT-4 quando possível
   - Cache de respostas idênticas
   - Fine-tuning de modelos próprios para reduzir chamadas

4. **Compressão e Deduplicação**
   - Documentos comprimidos em Cloud Storage
   - Deduplicação de embeddings em Vector DB

---

## Segurança na GCP

### Camadas de Segurança

#### **1. IAM (Identity and Access Management)**
- Service Accounts para cada componente
- Princípio do menor privilégio
- Auditoria de todas as ações via Cloud Audit Logs

#### **2. VPC e Networking**
- VPC isolada por ambiente (dev, staging, prod)
- Firewall rules restritivas
- Private Service Connection para Cloud SQL

#### **3. Encryption**
- Em repouso: KMS (Cloud Key Management Service)
- Em trânsito: TLS 1.3 obrigatório
- Chaves rotacionadas automaticamente (90 dias)

#### **4. Secret Management**
- Senhas e credenciais em Secret Manager
- Injetadas como variáveis de ambiente
- Rotação automática

#### **5. DDoS Protection**
- Cloud Armor com regras customizadas
- Rate limiting por IP/cookie
- Detecção de padrões de ataque

#### **6. Auditoria**
- Todos os acessos logados em Cloud Audit Logs
- 1 ano de retenção obrigatória
- Alertas para atividades suspeitas

### Implicações Práticas

- Dados jurídicos (sensíveis) armazenados com criptografia KMS
- Acesso a dados jurídicos requer VPN + 2FA
- Dumps de banco de dados feitos em VPC privada
- Logs de acesso a documentos gera auditoria

---

## Integração de Serviços GCP

### Pub/Sub para Processamento Assíncrono

```
Evento de Upload
     ↓
Backend publica em Pub/Sub
     ↓
Worker subscreve
     ↓
OCR + Processamento
     ↓
Publica evento "DocumentoProcessado"
     ↓
Backend consome evento
     ↓
Notifica usuário
```

### Cloud Functions para Webhooks

- Recebe notificações de serviços externos
- Transforma em eventos de domínio
- Publica em Pub/Sub para o backend processar

### Cloud Tasks para Agendamento

- Cron job para "Calcular Prazos Vencendo Amanhã"
- Retry automático se falhar
- Deduplicação de tarefas

---

## Decisões de Design Importantes

### 1. **Por que não Kubernetes (GKE)?**
- Cloud Run mais simples para este caso de uso
- Menor overhead operacional
- Custo similar ou menor
- Escalabilidade suficiente

### 2. **Por que Pub/Sub ao invés de RabbitMQ?**
- Integração nativa com GCP
- Sem infraestrutura para gerenciar
- Garantias de entrega at-least-once
- Escalabilidade ilimitada

### 3. **Por que Cloud SQL + Firestore (híbrido)?**
- SQL para dados transacionais (integridade crítica)
- Firestore para documentos semiestruturados (flexibilidade)
- Evita "NoSQL everywhere" que complica manutenção

### 4. **Por que não API Gateway?**
- Cloud Run tem SSL/TLS nativo
- Load Balancer gerenciado suficiente
- Cloud Armor integrado para segurança

---

## Implicações Práticas

1. **Developers não gerenciam infraestrutura**
   - Foco em código
   - Deploys simplificados

2. **Custos são previsíveis**
   - Modelo de pagamento por consumo
   - Budget alerts configurados

3. **Escalabilidade automática**
   - Tráfego 10x não quebra o sistema
   - Sem provisionamento manual

4. **Compliance facilitado**
   - LGPD: Criptografia de dados jurídicos
   - Auditoria: Logs de acesso automáticos
   - Recovery: Backups automáticos

---

## Próximos Passos

1. **Implementar CI/CD** com Cloud Build
2. **Configurar monitoramento** com Cloud Monitoring
3. **Estabelecer SLOs** (Service Level Objectives)
4. **Testar disaster recovery** mensalmente
5. **Otimizar custos** baseado em métricas reais
6. **Evoluar para multi-region** conforme escala

---

**Versão:** 1.0  
**Data:** 20 de abril de 2026  
**Mantido por:** Arquitetura JuriSense / DevOps  
**Status:** Em Implementação
