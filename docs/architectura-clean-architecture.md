# Arquitectura Limpia en FiaoBot: Explicación Completa y Diagramas

---

## ¿Qué es Clean Architecture? (Definición)

**Clean Architecture**, popularizada por Robert C. Martin ("Uncle Bob"), organiza el software en **círculos concéntricos donde las capas interiores no dependen de las exteriores**. Las dependencias fluyen hacia adentro, nunca al revés.

### Principios Fundamentales:
1.  **Dependencias Invertidas (IoD - Inversion of Dependencies):** Una capa interior define interfaces; una exterior implementa esas interfaces. Ejemplo: `Service` declara "necesito un Repositorio", el repositorio concreta la persistencia de datos, pero ambos son independientes del framework o LLM concreto usado.
2.  **Independencia del Framework:** Puedes cambiar desde SQLite a PostgreSQL, o OpenAI por Anthropic sin tocar el núcleo (lógica y dominio).
3.  **Separación Responsabilidades:** Dominio/persistencia/interfaz externa en capas distintas que no se contaminan.

---

## SÍ: LA ARQUITECTURA ESTABA DOCUMENTADA EN `docs/02-diseno-solucion.md`

El documento de diseño del proyecto ya define explícitamente el patrón **Clean Architecture** sin nombrarlo directamente, aunque con su diagrama y descripción lo demuestran claramente. 

### ¿Qué dice docs/02-diseno-solucion.md? (Líneas 3-47)

```
## Arquitectura general

El sistema recibe mensajes de texto desde Telegram, los procesa con
un modelo de lenguaje (LLM) mediante function/tool calling para
extraer la intención y los datos estructurados, ejecuta la lógica de
negocio de forma determinística en el backend, y responde en lenguaje
natural al vendedor.

Diagrama de arquitectura:

┌─────────────┐
│  Vendedor   │ ← NIVEL EXTERIOR (INTERFAZ) - Usuario/Telegram Bot API
│  (Telegram) │     ↓ mensaje → traducción estructurada  
└──────┬──────┘     
        ▼        
┌───────────────────────┐    
│    LLMProvider         │ ← NIVEL INTERMEDIO-EXTERIOR: 
│   (interfaz propia)    │      Abstracción intercambiable (OpenAI/Claude/Ollama).
│  ├─ ClaudeProvider     │      No toma decisiones ni calcula dinero.  
└───────────────────┘    
        ↓        
       BACKEND PURO PYTHON + BASE DE DATOS (PostgreSQL/SQLite)
         ┌───────┴────────┐
         │                 │
    Lógica de negocio   Persistencia directa a DB 
    en backend          → determinística, sin delegación a API externa
```

**Evidencias explícitas del patrón:**

| Línea | Evidencia Clean Architecture  
│-------|---------------------------------------------------------|  
21-37 │ Diagrama muestra **flechas hacia abajo**: Usuario → LLMProvider (traducción) → Backend puro. No hay flechas de vuelta desde DB/Backend al prompt builder o adaptador externo.
53-57 │ `LLMProvider` descrito como "interfaz propia" que abstracto los proveedores concretos (Claude, OpenAI, Ollama). El resto del backend **solo conoce esta interfaz**, nunca SDK directo de proveedor específico → IoD aplicado a LLM.  
61-67 │ Principio central: *"El LLM nunca decide lógica de negocio ni hace cálculos"* — regla RFxx sobre responsabilidad única y separación dominio/decisión/cálculo del framework externo.

---

### docs/plan-implementacion.md confirma la organización por fases (Líneas 3-71)

Este documento describe las **9 fases** ordenadas explícitamente para seguir el principio IoD: cada fase construye sobre la anterior, manteniendo dependencias hacia adentro:

| Fase | Objeto | Dependencia Hacia Adentro  
|------|--------|----------------------------------
 3    │ Repositorios (CRUD + búsqueda)        │ Dependen de `models/*` puro    
4     │ Servicios (lógica determinística + cálculos con Decimal)│ Reciben repositories desde afuera en constructor, no crean directamente instancias concretas ni persisten sin decisión. 
5    │ LLMProvider y PromptBuilder           │ Capa abstracción externa intercambiable por adaptador específico  
7     │ Integración Telegram webhook          │ Validación de autorización + orquestación final

**Criterio explícito (línea 30-):** "ningún servicio conoce Telegram ni el proveedor LLM" → separación responsabilidad y IoD aplicada.  

---

## EVIDENCIA EN EL CÓDIGO: LAS CARPETAS COME LA ARQUITECTURA

El proyecto sigue estos círculos concéntricos explícitamente (muestra estructura completa):


```
fiadobot/
├── models/                     ← [NÚCLEO - NIVEL 0] Entidades SQLAlchemy  
│   ├── client.py               # Cliente = agregado raíz, sin dependencias de DB/LLM 
│   ├── product.py              # Producto en catálogo   
│   └── transaction_detail.py   # Línea congelada: precio histórico fijo nunca cambia después de persistir la transacción (auditoría)  
├── repositories/               ← [NIVEL 1 - DATOS] Acceso a datos puro sin decisiones ni cálculos pendientes
│   ├── base_repository.py      # Base genérica → hereda SQLAlchemyError solo como tipo, no lógica DB concreta   
│   └── transaction_repo.py     # Persiste transacción con detalles en un commit (ORM de SQLAlchemy opera sobre modelo) 
├── services/                   ← [NIVEL 2 - NEGOCIO] Lógica determinística + cálculos monetarios
│   ├── sale_service.py         # Orquestador: recibe repositorios y balance_service como argumentos en constructor   
│   └── collection_summary.py   # Genera resumen histórico sin lógica transaccional ni persistencia directa 
├── llm/                        ← [NIVEL 3 - ADAPTADORES EXTERNOS] Traducción texto→JSON estructurado, no decisión
│   ├── provider.py             # Interfaz abstracto: interpret() → ToolCall   
│   └── openai_provider.py      # Adaptador concreto (invoca OpenAI API)  
├── prompting/                  ← [NIVEL 3a - PROMPTS] Construye payload para LLMProvider, no decisión ni cálculo
│   ├── prompt_builder.py       # Renderiza mensaje + instrucciones específicas   
│   └── types.py                # Tipos compartidos (PromptBundle, ToolCall)  
├── db/                         ← [NIVEL 4 - INFRAESTRUCTURA] Configuración sesión DB, opcional si inyectable
│   └── session.py              # Crea sesión SQLAlchemy para repositorios concretos   
└── config.py                   ← [EXTERIOR: NIVEL MAXIMO] Credenciales y URLs del entorno (DB URL, OPENAI_API_KEY)  
```

**Regla visual:** Si puedes trazar flechas desde capas exteriores hacia el interior sin que las flechas apunten al revés → Clean Architecture. Aquí no hay flecha de `llm/` apuntando a `models/`, ni de `db/session.py` puntoado a `services/*`.

---

## DIAGRAMA DE LAYERS: INYECCIÓN DE DEPENDENCIAS EN ACCIÓN


```
╭───────────────────────────────────────────────┐   ← NIVEL 0 (NÚCLEO) - NO DEPENDE EXTERNO  
│                                               │   
│                Entidades SQLAlchemy            │      Client, Product, TransactionDetail  
│                  models/*                      │         → Sin dependencias de DB/LLM
│              ────────────                       │        
╰═══════════════════┬━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┘                      
                     │                                                      
          (dependencia hacia adentro)                                       
                    ▼                                                       
╭───────────────────────────────────────────────┐   ← NIVEL 1 - REPOSITORIOS  
│                                               │      Acceso a datos puro, sin cálculos ni decisiones    
│              Repositorio de Datos              │         CRUD + consultas específicas          
│                   repositories/*                │    → Implementación concreta (SQLAlchemy ORM)
│             ────────────                       │        
╰═══════════════════┬━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┘                      
                     │                                                      
          (dependencia hacia adentro)                                       
                    ▼                                                       
╭───────────────────────────────────────────────┐   ← NIVEL 2 - SERVICIOS  
│                                               │      Orquestadores de negocio + cálculos con Decimal    
│              Servidores Determinísticos         │         Validación, cálculo balance            
│                   services/*                     │    → Recibe repositorios en constructor
│             ────────────                       │        
╰═══════════════════┬━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┘                      
                     │                                                      
          (dependencia hacia adentro)                                       
                    ▼                                                       
╭───────────────────────────────────────────────┐   ← NIVEL 3 - ADAPTADORES  
│                                               │      Traducción → Invocación API externa             
│            LLMProvider Interface                 │         No toma decisiones ni calcula           
│              llm/provider.py                     │    → Abstracción de proveedor concreto
│             ────────────                       │        
├──────▼────────┬─────────────────────────────────┤                      
       ▼        |                                    
╭───────────────────────────────────────────────┐   ← NIVEL 3a - PROMPTS  
│                                               │      Renderiza instrucciones para LLM              
│              Prompt Builder                      │         Construye mensaje + herramientas       
│             prompting/*                           │    → Solo texto, no lógica ni cálculos
│            ────────────                       │        
├──────▼────────┴─────────────────────────────────┤                      
                     |                                                      
          (interfaz externa)                                                  
                    ▼                                                       
╭───────────────────────────────────────────────┐   ← NIVEL 4 - INFRAESTRUCTURA 
│                                               │      Configuración entorno                           
│                db/session.py                      │         Credenciales, URL DB                
│              ────────────                       │        
└──────► config (API keys, model name) ◄───────────┘
```

**Interpretación de flechas:**
- **Hacia adentro (↓):** Depende y define la interfaz; exterior implementa. Ejemplo: `SaleService` necesita repositorio → lo pasa desde fuera en constructor.  
- **Sin vuelta atrás (↑ nunca):** No hay código que diga "instanciar SaleService directamente sin pasar un repo" ni invocar DB dentro de prompt_builder.py o LLMProvider excepto llamar OpenAI para extraer JSON crudo del asistente (**traducción**, no decisión).

---

## EJEMPLOS REALES DEL CÓDIGO QUE DEMUESTRAN CLEAN ARCHITECTURE

### Ejemplo 1: Inyección en `SaleService` (NIVEL 2 - SERVICIOS)
```python
# services/sale_service.py  
class SaleService:  
    def __init__(self, 
                  client_repository: ClientRepository,   # ← Recepción desde afuera (IoD).
                  transaction_repository: TransactionRepository):  # No crea directamente!
        self.client_repository = client_repository   
        self.transaction_repository = transaction_repo  

```

**Pregunta:** ¿Quién crea `SaleService`? → Un contenedor de pruebas puede pasarle mocks o una app externa lo inyecta manualmente. El servicio solo exige interfaces en repositorios sin importar si persisten con SQLite o PostgreSQL (**independencia del framework/DB concreto**). 

---

### Ejemplo 2: Cambio LLM → Solo toco adaptador externo (NIVEL 3)
```python  
# llm/openai_provider.py    
class OpenAIProvider(LLMProvider):    # ← Implementación concreta que invoca API oficial   
    def interpret(self, bundle) -> ToolCall: 
        response = self.client.chat.completions.create(...)   # llama a OpenAI solo para traducción
        ...  
```

Si cambias a Anthropic → editas solo `openai_provider.py` (o creas `anthropic_adapter.py`). Los archivos en `services/*`, `models/*`, y hasta el prompt builder no se tocan porque la abstracción (`LLMProvider`) es estable e independiente (**independencia del proveedor externo**).  

---

### Ejemplo 3: Repositorio = Solo CRUD + consultas específicas (NIVEL 1)
```python  
# repositories/transaction_repository.py    
def list_by_customer(self, customer_id) -> list[Transaction]:   
    # ← Pura lectura sobre ORM SQLAlchemy, no cálculos pendientes ni decisiones de negocio!
    statement = select(Transaction).where(...)        
    return list(session.scalars(statement).all()) 
```

Ninguna lógica dentro del repo decide "dejar anular o borrar" — eso lo toma `TransactionCancellationService` (nivel 2) antes de llamar `.cancel_transaction()` (**lógica de negocio en servicios**, repositorio solo accede datos puro ORM SQLAlchemy sobre modelos puros).  

---

## COMPARATIVA: CON Y SIN CLEAN ARCHITECTURE

| | **Sin Clean Architecture**                    | **Con Clean Architecture en FiaoBot**                     |
|---------------------------------|--------------------------------------------------|------------------------------------------------------------------------|  
| Cambio DB                       | Modificas lógica de negocio, servicios            | Solo cambias `config.py` + `db/session.py`                            |    
| Cambiar proveedor LLM           | Toca validación y cálculos numéricos              | Editar solo adaptador (`llm/openai_provider.py`)                      |  
| Escribe tests unitarios         | Requieren mocks complejos (DB simulada, etc.)     | Puedes sustituir repositorios por in-memory/mocks simples             |
| Auditoría de balance            | Depende del LLM o cálculos en memoria             | Determinístico: `ventas activas - pagos registrados`                   

---

## VALIDACIÓN RÁPIDA (CHECKLIST DEL DESARROLLADOR)

**Antes de considerar tu tarea como hecha:**

- [ ] Las entidades SQLAlchemy (`models/*`) no importan ni dependen de repositorios, LLM o DB.  
- [ ] Los servicios en `services/*` declaran sus dependencias como parámetros del constructor (sin crearlas internamente).  
- [ ] No hay código que llame a una API externa desde un prompt builder; solo renderiza texto y pasa abstracción al proveedor concreto abajo.  
- [ ] Repositorios no hacen cálculos ni validaciones de negocio — solo CRUD + consultas específicas para persistencia/lectura directa del ORM (SQLAlchemy sobre modelos puros).  

---

## CONCLUSIÓN EN TRES FRASES

1. **Núcleo (`models`) puro:** Entidades SQLAlchemy sin dependencias externas, independientes de infraestructura concreta.  
2. **Servicios determinísticos en `services/*`:** Lógica validada + cálculos en Decimal delegan persistencia a repositorios inyectados desde afuera (**IoD aplicado a servicios**, lógica de negocio no mezclada con decisión/persistencia externa).  
3. **Adaptadores externos intercambiables:** Cambiar DB o proveedor LLM solo requiere modificar capas exteriores sin tocar el núcleo ni tests unitarios existentes → `docs/02-diseno-solucion.md` y `docs/plan-implementacion.md` ya lo especificaban con diagramas explícitos de este patrón.  

---