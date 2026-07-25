# Plan de implementación por fases

Este plan mantiene el orden sugerido porque cada fase construye la anterior y reduce el acoplamiento entre capas.

## Fase 1: Setup

- Objetivo de la fase: dejar lista la base ejecutable del proyecto Python 3.11 con estructura de paquetes, entorno virtual, dependencias y configuración de linters.
- Archivos/módulos que se crearán o modificarán: `requirements.txt`, `.flake8`, `.pylintrc`, `.gitignore`, `src/fiadobot/__init__.py`, `src/fiadobot/config.py`, `src/fiadobot/main.py`, y la estructura mínima de carpetas bajo `src/fiadobot/` y `tests/`.
- Requisitos que cubre: RNF01, RNF02 y RNF03 como soporte de despliegue y operación.
- Criterio de hecho: el proyecto arranca localmente con `venv`, las dependencias quedan fijadas en `requirements.txt`, `.flake8` y `.pylintrc` existen y reflejan la política del repo, y una ejecución básica de flake8 y pylint sobre el esqueleto no reporta errores. Pylint debe quedar configurado para exigir score >= 9.0.

## Fase 2: Modelo de datos

- Objetivo de la fase: definir modelos SQLAlchemy y migraciones Alembic para todas las entidades persistentes, sin lógica de negocio todavía.
- Archivos/módulos que se crearán o modificarán: `alembic.ini`, `alembic/env.py`, `alembic/versions/*`, `src/fiadobot/db/base.py`, `src/fiadobot/db/session.py`, `src/fiadobot/models/client.py`, `src/fiadobot/models/product.py`, `src/fiadobot/models/transaction.py`, `src/fiadobot/models/transaction_detail.py`, `src/fiadobot/models/payment.py`, `src/fiadobot/models/conversation_state.py`, `src/fiadobot/models/authorized_user.py`.
- Requisitos que cubre: RF06, RF07, RF08, RF09, RNF02, RNF04 y RNF05.
- Criterio de hecho: las tablas, claves, constraints e índices requeridos por `docs/03-modelo-datos.md` existen en migraciones ejecutables; la extensión `pg_trgm` queda contemplada; los modelos reflejan tipos monetarios `NUMERIC` y relaciones correctas; flake8 y pylint pasan con score >= 9.0 sobre esta capa.

## Fase 3: Repositorios

- Objetivo de la fase: implementar acceso determinístico a datos para insertar, consultar y anular clientes, productos, transacciones, pagos y estado conversacional, incluyendo búsqueda difusa de clientes con `pg_trgm`.
- Archivos/módulos que se crearán o modificarán: `src/fiadobot/repositories/client_repository.py`, `src/fiadobot/repositories/product_repository.py`, `src/fiadobot/repositories/transaction_repository.py`, `src/fiadobot/repositories/payment_repository.py`, `src/fiadobot/repositories/conversation_state_repository.py`, y utilidades comunes en `src/fiadobot/repositories/base_repository.py` o equivalente.
- Requisitos que cubre: RF03, RF06, RF07, RF08, RF09, RNF02, RNF04 y RNF05.
- Criterio de hecho: existen operaciones de lectura y escritura bien tipadas para crear, buscar, actualizar y anular registros; la búsqueda difusa devuelve candidatos consistentes para desambiguación; no hay lógica de negocio fuera del repositorio pero sí toda la persistencia necesaria; flake8 y pylint pasan con score >= 9.0.

## Fase 4: Servicios

- Objetivo de la fase: concentrar toda la lógica de negocio en servicios puros o casi puros, sin dependencia de Telegram ni del LLM.
- Archivos/módulos que se crearán o modificarán: `src/fiadobot/services/balance_service.py`, `src/fiadobot/services/sale_service.py`, `src/fiadobot/services/payment_service.py`, `src/fiadobot/services/collection_summary_service.py`, `src/fiadobot/services/transaction_cancellation_service.py`, `src/fiadobot/services/product_price_service.py`, `src/fiadobot/services/analytics_service.py` si alguna parte analítica requiere agregación de negocio.
- Requisitos que cubre: RF02, RF03, RF04, RF05, RF06, RF07, RNF04 y RNF05.
- Criterio de hecho: el saldo pendiente se calcula determinísticamente excluyendo transacciones anuladas; registrar venta, registrar pago, generar resumen de cobro y anular transacción producen resultados correctos y auditables; ningún servicio conoce Telegram ni el proveedor LLM; flake8 y pylint pasan con score >= 9.0.

## Fase 5: LLMProvider

- Objetivo de la fase: definir primero `PromptBuilder` como capa agnóstica de proveedor y después la abstracción `LLMProvider` con un primer adaptador inicial para OpenAI, sin mezclar armado de prompt con integración técnica.
- Archivos/módulos que se crearán o modificarán: `prompts/system_prompt.md`, `prompts/tools_schema.json`, `src/fiadobot/prompting/prompt_builder.py`, `src/fiadobot/prompting/types.py`, `src/fiadobot/llm/provider.py`, `src/fiadobot/llm/types.py`, `src/fiadobot/llm/openai_provider.py`, y las definiciones internas necesarias para ensamblar y transportar prompts y tools.
- Requisitos que cubre: RF01, RF02, RF03, RF04, RF05, RF06 y RF07.
- Criterio de hecho: `PromptBuilder` carga los activos desde `/prompts`, combina el contexto dinámico y entrega al proveedor un prompt ya armado; `LLMProvider` solo recibe ese prompt y las tools, no conoce reglas de negocio ni tono, y el adaptador inicial de OpenAI produce una representación interna unificada de tool call; no accede a base de datos ni calcula montos; flake8 y pylint pasan con score >= 9.0.

## Fase 6: Estado conversacional

- Objetivo de la fase: implementar persistencia y lógica de `estado_conversacion` para desambiguación de nombres y continuidad conversacional.
- Archivos/módulos que se crearán o modificarán: `src/fiadobot/services/conversation_state_service.py`, ampliaciones en `src/fiadobot/repositories/conversation_state_repository.py`, y cualquier helper para serializar y deserializar contexto JSON.
- Requisitos que cubre: RF08 y RNF02.
- Criterio de hecho: un chat puede quedar en estado pendiente, responder a esa pregunta recupera el contexto correcto, la desambiguación se resuelve y el estado se elimina al finalizar; flake8 y pylint pasan con score >= 9.0.

## Fase 7: Telegram

- Objetivo de la fase: integrar webhook, validación de `chat_id` autorizado y orquestación completa mensaje -> LLM -> servicio -> respuesta.
- Archivos/módulos que se crearán o modificarán: `src/fiadobot/api/telegram_webhook.py`, `src/fiadobot/api/dependencies.py`, `src/fiadobot/api/auth.py`, `src/fiadobot/main.py`, y cualquier cliente o helper para Telegram.
- Requisitos que cubre: RF09, RNF01 y RNF02.
- Criterio de hecho: un mensaje entrante pasa primero por validación de autorización; solo chats permitidos continúan; el flujo completo ejecuta la acción correcta y devuelve respuesta; el código mantiene el objetivo de latencia RNF01 en diseño y validación básica; flake8 y pylint pasan con score >= 9.0.

## Fase 8: Analítica

- Objetivo de la fase: implementar `consultar_analitica` como operación de lectura sobre histórico.
- Archivos/módulos que se crearán o modificarán: `src/fiadobot/services/analytics_service.py` si no quedó completa en fases previas, `src/fiadobot/repositories/analytics_repository.py` o consultas específicas de agregado, y el mapeo de salida en la capa de aplicación.
- Requisitos que cubre: RF05.
- Criterio de hecho: consultas históricas como ventas por producto, clientes más frecuentes y rangos de fechas devuelven resultados consistentes y reproducibles; flake8 y pylint pasan con score >= 9.0.

## Fase 9: Tests

- Objetivo de la fase: asegurar con pruebas unitarias e integración básica la corrección de saldo, anulación y desambiguación, además de los flujos críticos del sistema.
- Archivos/módulos que se crearán o modificarán: `tests/unit/services/test_balance_service.py`, `tests/unit/services/test_transaction_cancellation_service.py`, `tests/unit/services/test_conversation_state_service.py`, `tests/integration/*` para repositorios y flujo mínimo de aplicación.
- Requisitos que cubre: RF02, RF03, RF06, RF08, RNF02, RNF04 y RNF05.
- Criterio de hecho: las pruebas unitarias de servicios pasan, existe al menos una verificación de integración básica por capa crítica, y la suite completa junto con flake8 y pylint supera los umbrales definidos; pylint debe mantenerse en score >= 9.0.

## Decisiones

- Se mantuvo el orden sugerido porque cada fase construye la anterior y evita mezclar persistencia, negocio e integración.
- La base de proyecto propuesta para la fase 1 es `requirements.txt + venv`.
- El adaptador inicial de la fase 5 será OpenAI.
- La fase 5 queda dividida conceptualmente en prompt engineering agnóstico de proveedor y adaptación técnica de LLM, siguiendo [docs/04-prompt-engineering.md](docs/04-prompt-engineering.md).
- No existe `docs/04-decisiones-tecnicas.md` en el repo; no se asumirán decisiones no documentadas fuera de lo que ya está en `docs/01-requisitos.md`, `docs/02-diseno-solucion.md` y `docs/03-modelo-datos.md`.

## Ambigüedades o vacíos detectados

- No existen `.flake8` ni `.pylintrc` en la raíz del repo, así que la fase 1 debe crearlos o, si se prefiere otra ubicación, definirla explícitamente antes de implementar.
- El repo no tiene aún código Python ni estructura de paquetes, así que los módulos listados arriba son una propuesta inicial de arquitectura y pueden ajustarse si quieres un nombre de paquete distinto.
- `docs/02-diseno-solucion.md` define las tools del LLM a nivel funcional, pero no fija el esquema interno exacto de `ToolCall`; conviene cerrarlo antes de implementar la fase 5 para evitar retrabajo.
- El detalle exacto del contrato entre `PromptBuilder` y `LLMProvider` debe validarse antes de iniciar la fase 5, aunque la separación conceptual ya quedó documentada en [docs/04-prompt-engineering.md](docs/04-prompt-engineering.md).
- `docs/01-requisitos.md` y `docs/03-modelo-datos.md` son suficientes para el núcleo, pero la capa de analítica en RF05 puede requerir concretar qué consultas entran en el primer alcance si quieres algo más amplio que los ejemplos mencionados.