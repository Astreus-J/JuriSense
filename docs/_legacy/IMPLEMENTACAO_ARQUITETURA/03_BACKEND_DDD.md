# 🏛️ BACKEND COM DOMAIN-DRIVEN DESIGN

## Introdução: Por que Domain-Driven Design?

O setor jurídico é complexo. Não é falta de informação, mas *excesso de informação e contexto* que cria o desafio. Um advogado precisa raciocinar em termos de **processos**, **prazos**, **documentos**, **partes** e **regras jurídicas específicas**. O Backend do JuriSense não pode ser um CRUD genérico; deve ser um reflexo direto do domínio jurídico. Isso é Domain-Driven Design (DDD).

## Princípios de Domain-Driven Design

### O Que é DDD?

Domain-Driven Design é uma abordagem arquitetônica que prioriza o **domínio de negócio** sobre tecnologia. A estrutura de código espelha a estrutura de negócio.

**Princípios Core:**

1. **Bounded Contexts:** Cada contexto tem seu próprio modelo
2. **Ubiquitous Language:** Desenvolvedores falam a língua do domínio
3. **Agregados:** Grupos coesos de entidades com invariantes
4. **Value Objects:** Objetos imutáveis que representam conceitos
5. **Repositórios:** Abstrações para acesso a dados
6. **Eventos de Domínio:** Fatos que aconteceram no domínio

### Por que DDD é Crítico no JuriSense?

| Aspecto | Sem DDD | Com DDD |
|--------|---------|---------|
| Entendimento | O código é técnico; negócio é separado | Código fala linguagem do domínio |
| Mudanças | Reescrita massiva quando requisitos mudam | Refatoração isolada em um Bounded Context |
| Testes | Testes técnicos (BD, API) | Testes de regras de negócio |
| Onboarding | Novo dev entende Django, não direito | Novo dev entende direito, depois Django |
| Escalabilidade | Monolito cresce sem limites | Contextos crescem independentemente |

---

## Estrutura Hexagonal / Clean Architecture

### Arquitetura em Camadas

```
┌──────────────────────────────────────────┐
│           CAMADA DE APRESENTAÇÃO         │
│         (API REST, GraphQL, CLI)         │
└───────────────────┬──────────────────────┘
                    │
┌───────────────────▼──────────────────────┐
│        CAMADA DE APLICAÇÃO               │
│   (Use Cases, Application Services)      │
└───────────────────┬──────────────────────┘
                    │
┌───────────────────▼──────────────────────┐
│          CAMADA DE DOMÍNIO               │
│  (Entidades, Value Objects, Agregados,   │
│   Serviços de Domínio, Repositórios)     │
└───────────────────┬──────────────────────┘
                    │
┌───────────────────▼──────────────────────┐
│        CAMADA DE INFRAESTRUTURA          │
│   (BD, APIs Externas, Filas, Storage)    │
└──────────────────────────────────────────┘
```

### Isolamento de Camadas

**Regra Core:** Nunca pule camadas.

```
❌ ERRADO:
Views → Banco de Dados
        (sem lógica de negócio)

✅ CERTO:
Views → Use Case → Agregado (Domínio) → Repositório → BD
        (aplicação)  (negócio)      (infraestrutura)
```

### Benefícios

1. **Testabilidade:** Cada camada testável isoladamente
2. **Manutenibilidade:** Mudanças isoladas por camada
3. **Independência Técnica:** Trocar BD sem afetar domínio
4. **Reutilização:** Use Cases podem ser chamados por API, CLI, ou Background Job

---

## Bounded Contexts do JuriSense

### Mapa de Contextos

```
┌─────────────────────────────────────────────────┐
│               JuriSense                         │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐  ┌──────────────┐            │
│  │  ACCOUNTS    │  │  PROCESSES   │            │
│  │  (Usuarios)  │  │  (Processos) │            │
│  └──────────────┘  └──────────────┘            │
│         │                  │                    │
│         └────┬─────────────┘                    │
│              │                                  │
│  ┌───────────▼────┐  ┌──────────────┐          │
│  │  DOCUMENTS     │  │  DEADLINES   │          │
│  │  (Documentos)  │  │  (Prazos)    │          │
│  └────────────────┘  └──────────────┘          │
│         │                  │                    │
│         └────┬─────────────┘                    │
│              │                                  │
│      ┌───────▼────────┐                        │
│      │  IA_SERVICES   │                        │
│      │  (Inteligência)│                        │
│      └────────────────┘                        │
│                                                 │
└─────────────────────────────────────────────────┘
```

### **Bounded Context 1: ACCOUNTS**

**Responsabilidade:** Autenticação, autorização, multi-tenancy

**Agregado Raiz:** `UserAccount`
- Usuário (email, senha, nome, assinatura digital)
- Tenant/Firma (para multi-tenancy)
- Permissões e Roles

**Value Objects:**
- `Email`: Email validado, único
- `PasswordHash`: Senha criptografada
- `Role`: Enum (Advogado, Gestor, Admin, Assistente)
- `DigitalSignature`: Certificado X.509 para assinatura

**Serviços de Domínio:**
- `AutenticacaoService`: Valida credenciais, emite JWT
- `AutorizacaoService`: Verifica permissões
- `TenantService`: Isola dados por firma

**Eventos de Domínio:**
- `UsuarioCriadoEvent`
- `UsuarioAutenticadoEvent`
- `PermissaoAlteradaEvent`

### **Bounded Context 2: PROCESSES**

**Responsabilidade:** Gestão de processos jurídicos, prazos, partes

**Agregado Raiz:** `ProcessoJuridico`
```
ProcessoJuridico
├── numero (único)
├── classe (civil, criminal, trabalhista)
├── tribunal
├── partes (autor, réu, advogados)
├── status (ativo, arquivado, encerrado)
├── dataProtocolo
├── prazos (lista de Prazo)
└── historico (eventos)
```

**Value Objects:**
- `NumeroProcesso`: CNJ standard format
- `ClasseJuridica`: Enum jurídico
- `Tribunal`: Tribunal responsável
- `Parte`: Pessoa jurídica ou natural na ação

**Serviços de Domínio:**
- `CalculoPrazoService`: Calcula prazos legais
- `SincronizacaoJudService`: Integra com JudiciárioDB
- `ValidacaoProcessoService`: Valida dados do processo

**Eventos de Domínio:**
- `ProcessoAbertOEvent`
- `PrazoProximoEvent`
- `StatusProcessoAlteradoEvent`

### **Bounded Context 3: DOCUMENTS**

**Responsabilidade:** Armazenamento, versionamento, processamento de documentos

**Agregado Raiz:** `DocumentoJuridico`
```
DocumentoJuridico
├── titulo
├── tipo (petição, parecer, sentença)
├── processo (referência)
├── conteudo (raw + estruturado)
├── versoes (histórico)
├── assinaturas (digitais)
├── metadados (criação, modificação)
└── permissoes (quem acessa)
```

**Value Objects:**
- `TipoDocumento`: Enum
- `Conteudo`: Raw (PDF) + Estruturado (JSON)
- `Versao`: Imutável, com hash e timestamp
- `Assinatura`: Digital, com certificado

**Serviços de Domínio:**
- `VersionamentoService`: Cria versões, diff
- `AssinaturaService`: Valida assinatura digital
- `ProcessamentoDocumentoService`: Orquestra OCR e IA
- `IntegracaoStorageService`: Armazena em Cloud Storage

**Eventos de Domínio:**
- `DocumentoUploadadoEvent`
- `DocumentoProcessadoEvent`
- `DocumentoAssinadoEvent`

### **Bounded Context 4: DEADLINES**

**Responsabilidade:** Cálculo e rastreamento de prazos legais

**Agregado Raiz:** `Prazo`
```
Prazo
├── tipo (legal, contratual, acordado)
├── dataVencimento
├── dataNotificacao
├── processo (referência)
├── descricao (matéria jurídica)
├── status (pendente, vencido, cumprido)
└── historico
```

**Value Objects:**
- `TipoPrazo`: Enum jurídico (peça processual, recurso, etc)
- `DiasUteis`: Cálculo de dias úteis (ignora fins de semana)
- `Status`: Enum

**Serviços de Domínio:**
- `CalculoPrazoService`: Calcula dias úteis, feriados
- `NotificacaoService`: Envia alertas (3 dias antes, dia anterior, dia do vencimento)
- `FeriadoService`: Integra com calendário de feriados

**Eventos de Domínio:**
- `PrazoCalculadoEvent`
- `PrazoProximoEvent` (3 dias antes)
- `PrazoVencidoEvent`

### **Bounded Context 5: IA_SERVICES**

**Responsabilidade:** Integração com serviços de IA, jurimetria, recomendações

**Agregado Raiz:** `AnaliseIA`
```
AnaliseIA
├── tipo (jurimetria, extração, classificação)
├── entrada (dados do domínio)
├── modelo (GPT-4, Claude, Vertex)
├── resultado (com confiança)
├── timestamp
├── auditoria (quem pediu, por que)
└── explicacao (SHAP, rationale)
```

**Value Objects:**
- `TipoAnalise`: Enum
- `Resultado`: Contém output + confiança + citações
- `Explicacao`: Justificativa em linguagem legível

**Serviços de Domínio:**
- `JurimetriaService`: Probabilidade de êxito
- `ExtracacaoService`: Extrai dados de texto
- `ClassificacaoService`: Classifica documentos
- `ComplianceIAService`: Verifica LGPD, auditoria

**Eventos de Domínio:**
- `AnaliseIARequisitadaEvent`
- `AnaliseIACompletadaEvent`
- `AnaliseIAValidadaEvent`

---

## Agregados, Value Objects, Entidades

### Agregado vs Entidade

**Entidade:** Objeto com identidade única (ID), pode ser mutável
**Agregado:** Grupo de entidades + Value Objects, com raiz agregada

**Exemplo:**

```python
# ❌ SEM DDD: Tudo é entidade
class Usuario(models.Model):
    id = models.UUID()
    email = models.EmailField()
    senha = models.CharField()  # ❌ Nunca armazenar senha em texto

# ✅ COM DDD: Agregado + Value Objects
class Email(ValueObject):
    """Value Object: Imutável, validado"""
    def __init__(self, email: str):
        if not self._valid_email(email):
            raise InvalidEmailError()
        self.value = email.lower()
    
    def __eq__(self, other):
        return self.value == other.value

class PasswordHash(ValueObject):
    """Value Object: Hash seguro"""
    def __init__(self, password: str):
        self.hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    
    def verify(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), self.hash)

class UserAccount(AggregateRoot):
    """Agregado: Raiz agregada"""
    def __init__(self, id: UUID, email: Email, name: str):
        self.id = id
        self.email = email  # Value Object
        self.name = name
        self.password_hash: Optional[PasswordHash] = None
    
    def set_password(self, password: str):
        self.password_hash = PasswordHash(password)
        self.add_event(UserPasswordSetEvent(self.id))

    def verify_password(self, password: str) -> bool:
        return self.password_hash.verify(password)
```

### Invariantes de Agregado

**Regra:** Agregado é responsável por manter seus invariantes (regras de negócio).

```python
class ProcessoJuridico(AggregateRoot):
    def adicionar_prazo(self, prazo: Prazo):
        # INVARIANTE: Prazo não pode ser no passado
        if prazo.data_vencimento < datetime.now():
            raise PrazoNoPassadoError()
        
        # INVARIANTE: Não pode ter dois prazos do mesmo tipo
        if any(p.tipo == prazo.tipo for p in self.prazos):
            raise PrazoDoMesmoTipoDuplicadoError()
        
        self.prazos.append(prazo)
        self.add_event(PrazoAdicionadoEvent(self.id, prazo))
```

---

## Repositórios e Data Mappers

### Padrão de Repositório

**Objetivo:** Abstrair acesso a dados, não expor detalhes de BD

```python
# ✅ CORRETO: Interface de repositório
class RepositorioProcesso(ABC):
    @abstractmethod
    def por_id(self, id: UUID) -> Optional[ProcessoJuridico]:
        pass
    
    @abstractmethod
    def salvar(self, processo: ProcessoJuridico) -> None:
        pass
    
    @abstractmethod
    def listar_por_tribunal(self, tribunal: Tribunal) -> List[ProcessoJuridico]:
        pass

# ❌ ERRADO: Expor detalhes de BD
class ProcessoView(APIView):
    def get(self, request):
        processos = Processo.objects.filter(tribunal=request.GET['tribunal'])
        return JsonResponse(processos.values())
```

### Data Mapper

**Objetivo:** Converter entre modelo de domínio e schema de BD

```python
class ProcessoDataMapper:
    """Mapeia ProcessoJuridico ↔ Processo (model Django)"""
    
    @staticmethod
    def to_orm(processo: ProcessoJuridico) -> Processo:
        """Domínio → BD"""
        return Processo(
            id=processo.id,
            numero=processo.numero.value,  # Value Object
            classe=processo.classe.name,
            tribunal_id=processo.tribunal.id,
            status=processo.status.name
        )
    
    @staticmethod
    def from_orm(orm: Processo) -> ProcessoJuridico:
        """BD → Domínio"""
        return ProcessoJuridico(
            id=orm.id,
            numero=NumeroProcesso(orm.numero),
            classe=ClasseJuridica(orm.classe),
            tribunal=Tribunal.from_id(orm.tribunal_id),
            status=StatusProcesso(orm.status)
        )
```

### Implementação de Repositório

```python
class RepositorioProcessoDjango(RepositorioProcesso):
    """Implementação do repositório com Django ORM"""
    
    def por_id(self, id: UUID) -> Optional[ProcessoJuridico]:
        try:
            orm = Processo.objects.get(id=id)
            return ProcessoDataMapper.from_orm(orm)
        except Processo.DoesNotExist:
            return None
    
    def salvar(self, processo: ProcessoJuridico) -> None:
        orm = ProcessoDataMapper.to_orm(processo)
        orm.save()
        
        # Publicar eventos de domínio
        for event in processo.get_events():
            publish_event(event)
        
        processo.clear_events()
    
    def listar_por_tribunal(self, tribunal: Tribunal) -> List[ProcessoJuridico]:
        orms = Processo.objects.filter(tribunal_id=tribunal.id)
        return [ProcessoDataMapper.from_orm(orm) for orm in orms]
```

---

## Use Cases / Application Services

### Estrutura de Use Case

```python
class CriarProcessoUseCase:
    """Caso de uso: Criar novo processo jurídico"""
    
    def __init__(
        self,
        repositorio_processo: RepositorioProcesso,
        evento_publisher: EventPublisher
    ):
        self.repositorio = repositorio_processo
        self.evento_publisher = evento_publisher
    
    def executar(self, comando: CriarProcessoCommand) -> ProcessoDTO:
        """
        Orquestra a criação de um processo
        
        1. Validar entrada
        2. Criar agregado de domínio
        3. Salvar em repositório
        4. Publicar eventos
        5. Retornar DTO
        """
        
        # 1. Validação
        if not comando.numero:
            raise NumeroProcessoInvalidoError()
        
        # 2. Criar agregado
        novo_processo = ProcessoJuridico(
            id=UUID4(),
            numero=NumeroProcesso(comando.numero),
            classe=ClasseJuridica(comando.classe),
            tribunal=Tribunal.from_name(comando.tribunal)
        )
        
        # 3. Salvar
        self.repositorio.salvar(novo_processo)
        
        # 4. Publicar eventos (ocorre dentro de salvar())
        # 5. Retornar DTO
        return ProcessoDTO.from_dominio(novo_processo)
```

### DTO (Data Transfer Object)

```python
@dataclass
class ProcessoDTO:
    """Representa um processo para saída de API"""
    id: str
    numero: str
    classe: str
    tribunal: str
    status: str
    data_protocolo: str
    
    @staticmethod
    def from_dominio(processo: ProcessoJuridico) -> "ProcessoDTO":
        return ProcessoDTO(
            id=str(processo.id),
            numero=processo.numero.value,
            classe=processo.classe.name,
            tribunal=processo.tribunal.nome,
            status=processo.status.name,
            data_protocolo=processo.data_protocolo.isoformat()
        )
```

### Orquestração de Use Cases

```python
class ProcessoApplicationService:
    """Application Service: Orquestra use cases de Processo"""
    
    def __init__(self, repositorio: RepositorioProcesso):
        self.criar_processo = CriarProcessoUseCase(repositorio)
        self.obter_processo = ObterProcessoUseCase(repositorio)
        self.listar_processos = ListarProcessosUseCase(repositorio)
    
    def criar(self, comando: CriarProcessoCommand) -> ProcessoDTO:
        return self.criar_processo.executar(comando)
```

---

## Infrastructure Layer

### Celery para Processamento Assíncrono

```python
@celery_app.task
def processar_documento_task(documento_id: str):
    """Tarefa assíncrona: Processar documento com IA"""
    
    # Usar repositório para carregar agregado
    repositorio = RepositorioDocumentoImpl()
    documento = repositorio.por_id(UUID(documento_id))
    
    # Chamar serviço de domínio
    servico = ProcessamentoDocumentoService()
    resultado = servico.processar(documento)
    
    # Publicar evento
    evento = DocumentoProcessadoEvent(documento_id, resultado)
    event_bus.publish(evento)
```

### Integração com APIs Externas

```python
class ClienteJudiciarioIntegracao:
    """Integração com sistema de Judiciário"""
    
    def buscar_processo(self, numero: str) -> dict:
        """Busca processo no Judiciário Brasileiro"""
        response = requests.get(
            f"{JUDICIARIO_API}/processos/{numero}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if response.status_code != 200:
            raise ProcessoNaoEncontradoError()
        return response.json()
    
    def sincronizar_processo(self, numero: str) -> ProcessoJuridico:
        """Sincroniza processo com JudiciárioDB"""
        dados = self.buscar_processo(numero)
        
        # Converter dados externos em agregado de domínio
        processo = ProcessoJuridico(
            id=UUID4(),
            numero=NumeroProcesso(dados['numeroProcesso']),
            # ... mapear demais campos
        )
        
        return processo
```

---

## Testes em DDD

### Teste Unitário (Domínio)

```python
class TestProcessoJuridico(unittest.TestCase):
    """Testes da lógica de domínio"""
    
    def test_adicionar_prazo_no_passado_deve_falhar(self):
        # Arrange
        processo = ProcessoJuridico(
            id=UUID4(),
            numero=NumeroProcesso("0000000-00.0000.0.00.0000")
        )
        prazo_passado = Prazo(
            tipo=TipoPrazo.INICIAL,
            data_vencimento=datetime.now() - timedelta(days=1)
        )
        
        # Act & Assert
        with self.assertRaises(PrazoNoPassadoError):
            processo.adicionar_prazo(prazo_passado)
    
    def test_adicionar_prazo_valido(self):
        # Arrange
        processo = ProcessoJuridico(...)
        prazo = Prazo(
            tipo=TipoPrazo.INICIAL,
            data_vencimento=datetime.now() + timedelta(days=30)
        )
        
        # Act
        processo.adicionar_prazo(prazo)
        
        # Assert
        assert len(processo.prazos) == 1
        assert processo.get_events()[0] == PrazoAdicionadoEvent(...)
```

### Teste de Integração (Use Case)

```python
class TestCriarProcessoUseCase(unittest.TestCase):
    """Testes de use case com repositório real"""
    
    def setUp(self):
        self.repositorio = RepositorioProcessoEmMemoria()
        self.use_case = CriarProcessoUseCase(self.repositorio)
    
    def test_criar_processo_deve_salvar_em_repositorio(self):
        # Arrange
        comando = CriarProcessoCommand(
            numero="0000000-00.0000.0.00.0000",
            classe="Ação Ordinária"
        )
        
        # Act
        dto = self.use_case.executar(comando)
        
        # Assert
        assert dto.id is not None
        processo_salvo = self.repositorio.por_id(UUID(dto.id))
        assert processo_salvo is not None
```

### Teste de API (E2E)

```python
class TestProcessoAPI(APITestCase):
    """Testes end-to-end da API"""
    
    def test_criar_processo_deve_retornar_201(self):
        # Arrange
        payload = {
            "numero": "0000000-00.0000.0.00.0000",
            "classe": "Ação Ordinária",
            "tribunal": "TJSP"
        }
        
        # Act
        response = self.client.post('/api/processos', payload)
        
        # Assert
        self.assertEqual(response.status_code, 201)
        self.assertIn('id', response.json())
```

---

## Evolução de Domínios: Crescimento Sem Caos

### Problema: Monolito que Cresce

Conforme o projeto cresce:

```
Mês 1: 2 Bounded Contexts
Mês 6: 5 Bounded Contexts
Ano 1: 15+ Contextos entrelaçados, dependências circulares
```

**Sintomas:**
- Mudança em um contexto quebra outro
- Testes levam horas
- Deploy é arriscado

### Solução: Modularização e Independência

#### **Fase 1: Monolito Modular (Atual)**
- Código separado por Bounded Context
- Imports internos apenas
- Compartilhamento de BD (schema separation)

#### **Fase 2: Serviços Distribuídos (Futuro)**
- Cada Bounded Context é serviço independente
- API gRPC ou REST para comunicação
- BD isolado por contexto
- Event Bus assíncrono para coordenação

### Exemplo: Evolução PROCESSES → ProcessService

```python
# ✅ MONOLITO MODULAR (agora)
apps/
    processes/
        domain/
            entities.py
            aggregates.py
            services.py
        application/
            use_cases.py
        infrastructure/
            repositories.py
    documents/
        domain/
        application/
        infrastructure/
    # Ambos em mesmo banco, monolito

# ❌ → SERVIÇO INDEPENDENTE (depois)
services/
    process-service/
        domain/
        application/
        infrastructure/
        docker-compose.yml
        Dockerfile
    document-service/
        domain/
        application/
        infrastructure/
        docker-compose.yml
    # Cada um com DB próprio, comunicação via gRPC/Pub-Sub
```

### Anti-padrões a Evitar

| Anti-padrão | Problema | Solução |
|-----------|----------|--------|
| Importar modelo de outro contexto | Acoplamento | Usar DTOs e APIs |
| Compartilhar agregados | Dependência | Agregados independentes |
| BD compartilha schema | Mudança quebra tudo | Schema por contexto |
| Transações entre contextos | Consistência eventual perdida | Event sourcing, sagas |

---

## Implicações Práticas

### Para Novos Desenvolvedores

1. **Aprender linguagem do domínio**
   - Não é "tabela de usuários", é "UserAccount"
   - Não é "update", é "UsuarioAlterou SuaSenha"

2. **Respeitar limites de agregados**
   - Não faça queries que cruzam agregados
   - Use repositórios, não queries diretas

3. **Escrever testes de domínio**
   - Não apenas testes de API
   - Testes de invariantes e regras

### Para Arquitetos

1. **Evitar Over-Engineering**
   - Começa simples: 1 agregado por contexto
   - Evolui conforme necessidade

2. **Documentar Ubiquitous Language**
   - Glosário de termos
   - Faz parte do código

3. **Planejar Evolução para Serviços**
   - Qual contexto sairá primeiro do monolito?
   - Quando fazer split?

---

## Decisões de Design

### 1. **Por que não usar Django genérico?**

Django é ótimo, mas incentiva:
- Fat models (toda lógica no model)
- Queries diretas de views
- Sem separação de concerns

**Com DDD:**
- Models são apenas mappers de ORM
- Lógica está em Agregados e Serviços
- Views apenas chamam Use Cases

### 2. **Por que usar Events?**

Events permitem:
- Logging de tudo que aconteceu
- Integração assíncrona entre contextos
- Replicação de dados entre BD
- Auditoria e compliance

### 3. **Por que Agregados são importantes?**

Agregados garantem:
- Invariantes são respeitados
- Transação ocorre em nível de agregado
- Concorrência segura

---

## Exemplo Completo: Flow de Criação de Processo

### 1. API recebe requisição
```python
# views.py (Presentation Layer)
@router.post("/processos")
def criar_processo(request, comando: CriarProcessoCommand):
    resultado = application_service.criar(comando)
    return JSONResponse(resultado, status_code=201)
```

### 2. Use Case orquestra
```python
# use_cases.py (Application Layer)
class CriarProcessoUseCase:
    def executar(self, comando):
        processo = ProcessoJuridico(...)  # Domínio
        self.repositorio.salvar(processo)  # Infraestrutura
        return ProcessoDTO.from_dominio(processo)
```

### 3. Agregado valida regras
```python
# aggregates.py (Domain Layer)
class ProcessoJuridico(AggregateRoot):
    def __init__(self, numero, classe, tribunal):
        # Invariante: número deve ser válido
        NumeroProcesso(numero)  # Levanta exceção se inválido
        self.id = UUID4()
        self.add_event(ProcessoCriadoEvent(...))
```

### 4. Repositório persiste
```python
# repositories.py (Infrastructure Layer)
class RepositorioProcessoDjango(RepositorioProcesso):
    def salvar(self, processo):
        orm = ProcessoDataMapper.to_orm(processo)
        orm.save()
        for event in processo.get_events():
            publish_event(event)  # Assíncrono
```

### 5. Eventos propagam
```python
# celery_tasks.py (Infrastructure Layer)
@celery_app.task
def on_processo_criado(evento: ProcessoCriadoEvent):
    # Calcular prazos
    servico = CalculoPrazoService()
    prazos = servico.calcular(evento.processo_id)
    
    # Sincronizar com Judiciário
    integracao = ClienteJudiciarioIntegracao()
    integracao.sincronizar_processo(evento.numero)
    
    # Notificar usuário
    notificador = NotificadorService()
    notificador.notificar_processo_criado(evento.usuario_id)
```

---

## Próximos Passos

1. **Implementar padrão de sagas** para transações entre contextos (Q2 2026)
2. **Event sourcing** para auditoria completa (Q3 2026)
3. **GraphQL API** além de REST (Q2 2026)
4. **Split de serviços** começando com IA_SERVICES (Q4 2026)
5. **CQRS** para queries otimizadas (Q3 2026)
6. **Documentação de Ubiquitous Language** automática (Q2 2026)

---

**Versão:** 1.0  
**Data:** 20 de abril de 2026  
**Mantido por:** Arquitetura JuriSense / Backend Team  
**Status:** Em Produção com Evolução Contínua
