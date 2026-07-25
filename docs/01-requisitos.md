# Requisitos - Bot de fiados

## Descripción del problema

Un vendedor de productos a menudeo maneja ventas a crédito informal
("fiado") con sus clientes. Actualmente registra estas deudas usando
el chat de cada cliente en su celular como si fuera un libro contable:
escribe ahí lo que cada persona debe, y esa conversación sirve como
comprobante para ambas partes.

El problema surge al final de cada mes o quincena, cuando el vendedor
debe sentarse manualmente a revisar los chats de cada cliente, sumar
con calculadora y cuaderno cuántos productos le debe cada uno (cada
producto tiene un precio distinto) y calcular el saldo total antes de
empezar a enviar los mensajes de cobro. Este proceso le toma varias
horas adicionales de trabajo cada mes y es propenso a errores humanos
de cálculo, además de no dejar ningún tipo de trazabilidad ni
analítica sobre su negocio (qué productos vende más, qué clientes
compran con más frecuencia, etc.).

El vendedor ya tiene la información (la escribe todos los días), pero
no tiene una estructura de datos que se lo organice automáticamente.
El objetivo de este proyecto es capturar esa información de la forma
más natural posible para él (escribiendo en un chat) y convertirla en
datos estructurados, para eliminar el proceso manual de cálculo y
cobro, y habilitar consultas analíticas sobre el histórico del negocio.

## Requisitos

### Funcionales

- RF01: El sistema debe permitir registrar una venta a partir de un mensaje
  en lenguaje natural (ej. "Juan se llevó 2 panelas").
- RF02: El sistema debe calcular y mostrar el saldo pendiente de un cliente
  cuando se solicite.
- RF03: El sistema debe permitir registrar un pago parcial o total,
  descontándolo del saldo pendiente.
- RF04: El sistema debe generar un resumen de cobro (productos, fechas,
  saldo total) SOLO cuando el vendedor lo solicite explícitamente.
- RF05: El sistema debe permitir consultas analíticas históricas
  (ej. ventas por producto en un rango de fechas, clientes más frecuentes).
- RF06: El sistema debe permitir anular una transacción ya registrada
  (nunca se elimina físicamente; se marca como `anulada` para mantener
  trazabilidad).
- RF07: El sistema debe permitir actualizar el precio de un producto.
  El precio anterior no necesita conservarse; el monto de ventas ya
  registradas nunca se recalcula.
- RF08: Cada cliente tiene un nombre único en la base de datos, pero el
  vendedor puede escribir el nombre de forma imprecisa (mal escrito,
  incompleto, apodo). El sistema debe buscar coincidencias aproximadas
  y, si hay más de una posible, preguntar al vendedor cuál de los
  clientes corresponde antes de continuar.
- RF09: Solo los chat_id incluidos en una lista de usuarios autorizados
  (vendedor + testers) pueden interactuar con el bot.

### No funcionales

- RNF01: El tiempo de respuesta del bot no debe superar los 5 segundos.
- RNF02: El sistema debe validar el chat_id contra una tabla/lista de
  usuarios autorizados antes de procesar cualquier mensaje.
- RNF03: El volumen esperado es de ~200 clientes activos y ~80
  transacciones/día (~2.400/mes); no se requiere infraestructura de
  alta escala.
- RNF04: Toda anulación de transacción debe quedar registrada
  (quién, cuándo, por qué se anuló) para poder auditar errores.
- RNF05: El monto de una transacción se calcula y almacena una única
  vez al momento de su creación; no se recalcula si el precio del
  producto cambia después.