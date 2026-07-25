# Modelo de datos - Bot de fiados

## Diagrama entidad-relación (alto nivel)

```
clientes ──┐
           ├─< transacciones ──< transaccion_detalle >── productos
           ├─< pagos
           └─< estado_conversacion

usuarios_autorizados (tabla independiente, solo control de acceso)
```

Una transacción es la "cabecera" de una venta (quién, cuándo, monto
total, estado). Puede tener uno o varios productos asociados, cada
uno registrado como una fila en `transaccion_detalle` (patrón
factura/líneas de factura). Esto permite registrar en un solo mensaje
una venta con varios productos distintos (ej. "2 panelas y una leche")
sin duplicar cliente/fecha por cada producto.

## Tablas

### `clientes`

| Columna       | Tipo         | Descripción                                   |
|---------------|--------------|------------------------------------------------|
| id            | SERIAL PK    | Identificador único interno                     |
| nombre        | VARCHAR(150) | Nombre completo, único en la tabla              |
| alias         | VARCHAR(150) | Apodo o nombre corto usado en el chat (opcional)|
| telefono      | VARCHAR(30)  | Número de contacto (opcional)                   |
| creado_en     | TIMESTAMP    | Fecha de alta del cliente                       |

- `nombre` tiene constraint UNIQUE.
- La búsqueda difusa (RF08) se hace contra `nombre` y `alias`
  combinados, usando la extensión `pg_trgm` de PostgreSQL.

### `productos`

| Columna       | Tipo          | Descripción                                  |
|---------------|---------------|-------------------------------------------------|
| id            | SERIAL PK     | Identificador único interno                      |
| nombre        | VARCHAR(100)  | Nombre del producto, único                        |
| precio_actual | NUMERIC(12,2) | Precio vigente del producto                       |
| activo        | BOOLEAN       | Si el producto sigue en catálogo (default true)   |

- No se guarda historial de precios (RF07): al actualizar
  `precio_actual`, el valor anterior se pierde y no afecta ventas ya
  registradas, porque esas ventas guardan su propio precio congelado
  (ver `transaccion_detalle`).

### `transacciones`

| Columna       | Tipo          | Descripción                                       |
|---------------|---------------|------------------------------------------------------|
| id            | SERIAL PK     | Identificador único interno                           |
| cliente_id    | INTEGER FK    | Referencia a `clientes.id`                            |
| fecha         | TIMESTAMP     | Fecha y hora del registro de la venta                 |
| monto_total   | NUMERIC(12,2) | Suma de los subtotales de `transaccion_detalle`       |
| estado        | VARCHAR(20)   | `activa` o `anulada` (RF06)                           |
| motivo_anulacion | TEXT       | Motivo si `estado = anulada` (RNF04, nullable)        |
| anulada_en    | TIMESTAMP     | Fecha/hora de la anulación (nullable)                 |

- `monto_total` se calcula y guarda una única vez al insertar la
  transacción (RNF05); nunca se recalcula después.
- Una transacción anulada NO se elimina físicamente; solo cambia su
  `estado` (RF06, RNF04). El cálculo de saldo pendiente debe excluir
  las transacciones con `estado = anulada`.

### `transaccion_detalle`

| Columna              | Tipo          | Descripción                                   |
|----------------------|---------------|---------------------------------------------------|
| id                   | SERIAL PK     | Identificador único interno                         |
| transaccion_id       | INTEGER FK    | Referencia a `transacciones.id`                     |
| producto_id          | INTEGER FK    | Referencia a `productos.id`                         |
| cantidad             | NUMERIC(10,2) | Cantidad comprada de ese producto                   |
| precio_unitario_congelado | NUMERIC(12,2) | Precio del producto AL MOMENTO de la venta   |
| subtotal             | NUMERIC(12,2) | `cantidad * precio_unitario_congelado`              |

- `precio_unitario_congelado` y `subtotal` se calculan una sola vez
  al insertar el detalle y nunca se recalculan (RNF05), aunque el
  producto cambie de precio después.

### `pagos`

| Columna     | Tipo          | Descripción                            |
|-------------|---------------|---------------------------------------------|
| id          | SERIAL PK     | Identificador único interno                    |
| cliente_id  | INTEGER FK    | Referencia a `clientes.id`                     |
| monto       | NUMERIC(12,2) | Monto pagado                                    |
| fecha       | TIMESTAMP     | Fecha y hora del pago                          |

- El saldo pendiente de un cliente se calcula como:
  `SUM(transacciones.monto_total WHERE estado='activa') - SUM(pagos.monto)`

### `estado_conversacion`

| Columna           | Tipo       | Descripción                                        |
|-------------------|------------|--------------------------------------------------------|
| chat_id           | BIGINT PK  | Identificador de chat de Telegram                       |
| accion_pendiente  | VARCHAR(50)| Ej: `desambiguar_cliente`                               |
| contexto          | JSONB      | Datos parciales (opciones, venta pendiente, etc.)       |
| creado_en         | TIMESTAMP  | Fecha/hora en que se generó la pregunta pendiente       |

- Se usa para resolver RF08 (desambiguación de nombres) sin depender
  de infraestructura externa como Redis (ver `02-diseno-solucion.md`).
- Un chat_id solo puede tener un estado pendiente a la vez (PK simple).
- Se borra el registro apenas se resuelve la acción pendiente.

### `usuarios_autorizados`

| Columna     | Tipo        | Descripción                                  |
|-------------|-------------|---------------------------------------------------|
| chat_id     | BIGINT PK   | Identificador de chat de Telegram autorizado         |
| rol         | VARCHAR(20) | `vendedor` o `tester`                                |
| agregado_en | TIMESTAMP   | Fecha en que se autorizó el acceso                   |

- Tabla independiente de control de acceso (RF09, RNF02). Se gestiona
  manualmente (por variable de entorno o insert directo), no desde
  el chat, según lo definido en requisitos.

## Notas de implementación

- Extensión requerida en PostgreSQL: `CREATE EXTENSION pg_trgm;`
  para habilitar búsqueda difusa de nombres de clientes.
- Todas las columnas monetarias usan `NUMERIC(12,2)`, nunca `FLOAT`,
  para evitar errores de redondeo en dinero.
- Los borrados son siempre lógicos (campo `estado` o `activo`), nunca
  `DELETE` físico sobre transacciones, para preservar trazabilidad
  (RNF04).