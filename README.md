# TP-PizzerIA-Labo-2

PizzerIA es un sistema de escritorio para gestionar una pizzería desde una interfaz gráfica hecha con Tkinter. Permite administrar pedidos, catálogo, productos, stock, cocina, ventas, promociones, comprobantes PDF, reportes Excel, gráficos simples y respaldos JSON.

La aplicación incluye un panel general, login por roles, gestión de productos, carga de pedidos con retiro o delivery, control de estados operativos, reposición de stock, consulta de proveedor externo, exportación de reportes y tickets PDF.

Los productos se modelan con programación orientada a objetos usando una clase base `Producto` y clases hijas como `Pizza`, `Empanada` y `Bebida`. El catálogo puede ampliarse desde la interfaz gráfica.

Los pedidos pasan por estados como pendiente, en preparación, listo, en camino, entregado o cancelado. La cocina procesa pedidos con hilos: cada cocinero toma pedidos en paralelo, se asignan estaciones como Horno, Empanadas o Bebidas, se calcula un tiempo estimado y se descuenta stock al entrar a preparación. Luego el usuario puede avanzar el estado según corresponda a retiro o delivery.

Las promociones se aplican automáticamente sobre empanadas: media docena obtiene 10% de descuento y docena o más obtiene 15%. El descuento queda reflejado en el pedido, las ventas, los reportes y el comprobante PDF.

Los reportes se generan con `openpyxl` usando listas y diccionarios nativos de Python. La interfaz también muestra gráficos simples con `Canvas` de Tkinter.

## Usuarios iniciales

- Administrador: `administrador` / `admin123`
- Empleado: `empleado` / `empleado123`

El administrador puede usar todo el sistema y cambiar ambas contraseñas desde Herramientas. El empleado puede cargar pedidos, procesar cocina, avanzar pedidos, ver stock y generar comprobantes PDF, pero no puede reponer stock, administrar catálogo, ver reportes/historial de ventas ni modificar respaldos.

## Instalación

python -m pip install -r requirements.txt

## Ejecución

python main.py

## Dependencias

- `openpyxl`: lectura y escritura de reportes Excel.
- `requests`: consulta opcional del proveedor externo.
- `reportlab`: generación de comprobantes PDF.

## Temas aplicados

- Programación Orientada a Objetos
- Encapsulamiento
- Herencia
- Polimorfismo
- Decoradores
- Excepciones personalizadas
- Threading
- Lock
- Requests
- Reportes Excel con openpyxl
- Comprobantes PDF con reportlab
- Generadores con `yield`
- Persistencia en JSON
