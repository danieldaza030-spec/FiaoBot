# Diseño de la solución - Bot de fiados

## Arquitectura general

El sistema recibe mensajes de texto desde Telegram, los procesa con
un modelo de lenguaje (LLM) mediante function/tool calling para
extraer la intención y los datos estructurados, ejecuta la lógica de
negocio de forma determinística en el backend, y responde en lenguaje
natural al vendedor.

Diagrama de arquitectura:

```
┌─────────────┐
│  Vendedor   │
│  (Telegram) │
└──────┬──────┘
       │ mensaje de texto
       ▼
┌─────────────────────┐
│   Telegram Bot API   │
└──────┬───────────────┘
       │ webhook
       ▼
┌──────────────────────────────────────────┐
│           Backend (FastAPI)               │
│                                            │
│  1. Valida chat_id autorizado (RNF02)     │
│  2. ¿Hay estado_conversacion pendiente?   │
│     → Sí: interpreta como respuesta       │
│     → No: envía a LLMProvider (tool call) │
│  3. Ejecuta lógica de negocio en BD       │
│     (búsqueda difusa, cálculo de saldo,   │
│      inserción de transacción, etc.)      │
│  4. Genera respuesta en texto natural     │
└──────┬─────────────────────────┬──────────┘
       │                         │
       ▼                         ▼
┌───────────────────┐   ┌──────────────────────┐
│   LLMProvider       │   │   PostgreSQL         │
│   (interfaz propia) │   │  - clientes           │
│                      │   │  - productos          │
│  ├─ ClaudeProvider   │   │  - transacciones       │
│  ├─ OpenAIProvider   │   │  - pagos               │
│  └─ OllamaProvider   │   │  - estado_conversacion │
└───────────────────┘   └──────────────────────┘
```

Componentes:
- **Telegram Bot API**: canal de entrada/salida de mensajes.
- **Backend (FastAPI)**: orquesta la lógica, valida autorización,
  gestiona estado conversacional, ejecuta queries.
- **LLMProvider (interfaz propia)**: capa de abstracción que interpreta
  lenguaje natural y determina qué acción ejecutar y con qué
  parámetros, sin importar qué proveedor de LLM esté detrás (Claude,
  OpenAI, Gemini, o un modelo local vía Ollama). No realiza cálculos
  ni accede directamente a la base de datos.
- **PostgreSQL**: fuente única de verdad de clientes, productos,
  transacciones, pagos y estado conversacional.

## Principio de diseño central

El LLM nunca decide lógica de negocio ni hace cálculos. Su única
responsabilidad es traducir lenguaje natural a una llamada de función
estructurada (tool call). Toda validación, búsqueda, cálculo de saldo
y persistencia ocurre en código determinístico del backend. Esto
evita errores de cálculo y hace el sistema auditable.

## Abstracción del proveedor de LLM

El sistema no debe depender directamente de la sintaxis o SDK de un
proveedor de LLM específico. Para lograr esto, el backend define una
interfaz propia `LLMProvider`, y cada proveedor real (Claude, OpenAI,
Ollama, etc.) implementa esa interfaz mediante un adaptador:

```python
class LLMProvider(ABC):
    @abstractmethod
    def interpretar_mensaje(self, mensaje: str, tools: list) -> ToolCall:
        pass

class ClaudeProvider(LLMProvider):
    def interpretar_mensaje(self, mensaje, tools):
        # llamada específica a la API de Anthropic
        ...

class OpenAIProvider(LLMProvider):
    def interpretar_mensaje(self, mensaje, tools):
        # llamada específica a la API de OpenAI
        ...

class OllamaProvider(LLMProvider):
    def interpretar_mensaje(self, mensaje, tools):
        # llamada a un servidor local (Ollama, vLLM, LM Studio, etc.)
        ...
```

El resto del backend solo conoce la interfaz `LLMProvider`, nunca
llama directamente al SDK de un proveedor específico. El proveedor
activo se selecciona mediante variable de entorno (ej.
`LLM_PROVIDER=claude` o `LLM_PROVIDER=ollama`), sin requerir cambios
en el resto del código.

Esto permite:
- Cambiar de proveedor sin reescribir lógica de negocio.
- Comparar precisión/costo/latencia entre proveedores fácilmente.
- Correr un modelo local (Ollama) para desarrollo o para operar sin
  dependencia de un servicio externo, si se requiere en el futuro.

## Tools (funciones) expuestas al LLM

Estas funciones son independientes del proveedor; cualquier
`LLMProvider` debe recibir esta misma definición de tools y devolver
un `ToolCall` en un formato interno unificado:

- `registrar_venta(cliente_texto, items: [{producto, cantidad}])`
- `registrar_pago(cliente_texto, monto)`
- `consultar_saldo(cliente_texto)`
- `generar_resumen_cobro(cliente_texto)`
- `anular_transaccion(transaccion_id, motivo)`
- `actualizar_precio(producto_texto, nuevo_precio)`
- `consultar_analitica(tipo, rango_fechas)`

## Manejo de estado conversacional (RF08)

Dado que el sistema debe soportar preguntas de desambiguación
(ej. varios clientes con el mismo nombre), el backend mantiene una
tabla `estado_conversacion` que registra si un chat_id tiene una
acción pendiente de confirmación. Cada mensaje entrante primero se
valida contra esta tabla:

- Si existe un estado pendiente para ese chat_id, el mensaje se
  interpreta como respuesta a la pregunta pendiente.
- Si no existe, el mensaje se envía al `LLMProvider` activo para su
  interpretación normal vía tool calling.

Este enfoque evita depender de infraestructura adicional (como Redis)
dado el volumen esperado del sistema (RNF03).

## Búsqueda difusa de clientes

La coincidencia de nombres escritos de forma imprecisa (RF08) se
resuelve en el backend usando la extensión `pg_trgm` de PostgreSQL
para búsqueda por similitud de texto, no mediante el LLM. El LLM
solo entrega el texto literal escrito por el vendedor; el backend
decide si hay 0, 1 o varias coincidencias posibles.

## Flujo conversacional de ejemplo (con desambiguación)

```
Vendedor: "Juan se llevó 2 panelas"
   ↓
Backend: no hay estado pendiente → envía a LLMProvider activo
   ↓
LLMProvider: devuelve ToolCall → registrar_venta(
                cliente_texto="Juan",
                items=[{producto:"panela", cantidad:2}])
   ↓
Backend: busca "Juan" en clientes con pg_trgm → encuentra 4 coincidencias
   ↓
Backend: guarda en estado_conversacion (chat_id, accion="desambiguar_cliente",
         contexto={opciones: [Juan Pérez, Juan Gómez, Juan Ríos, Juan Marín],
                    venta_pendiente: {producto:"panela", cantidad:2}})
   ↓
Bot responde: "Tengo 4 clientes llamados Juan:
   1. Juan Pérez
   2. Juan Gómez
   3. Juan Ríos
   4. Juan Marín
   ¿Cuál de ellos?"
   ↓
Vendedor: "el 2"
   ↓
Backend: SÍ hay estado pendiente → interpreta "el 2" como Juan Gómez
   ↓
Backend: recupera venta_pendiente del contexto, calcula monto
         (2 × precio_panela), inserta transacción, borra estado_conversacion
   ↓
Bot responde: "Anotado: Juan Gómez - 2 panelas - $6.000.
              Saldo total: $23.000"
```

## Seguridad

Todo mensaje entrante se valida contra una lista de chat_id
autorizados (vendedor + testers) antes de ser procesado (RNF02).
Mensajes de chat_id no autorizados se descartan silenciosamente o
reciben un mensaje de rechazo genérico.