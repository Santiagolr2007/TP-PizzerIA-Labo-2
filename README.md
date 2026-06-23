# TP-PizzerIA-Labo-2

PizzerIA es un sistema de gestion para una pizzeria desarrollado en Python. Permite crear pedidos, consultar productos, controlar stock, procesar pedidos en cocina, registrar ventas, reponer ingredientes, consultar un proveedor externo, generar reportes en Excel y guardar o cargar respaldos en JSON.

Al ejecutar `main.py`, se abre una interfaz grafica hecha con Tkinter. La app muestra un panel general con metricas del negocio, un menu lateral, tablas visuales, formularios para crear pedidos y acciones para operar la cocina, el inventario, los reportes y los respaldos.

La logica principal esta organizada con programacion orientada a objetos. Los productos se representan con una clase base `Producto` y clases hijas como `Pizza`, `Empanada` y `Bebida`. Cada producto calcula su precio y define los ingredientes necesarios para su preparacion.

Los pedidos se procesan con hilos (`threading`) y una cola (`queue.Queue`). Si hay stock suficiente, el pedido se entrega, se descuentan los ingredientes y se registra la venta. Si falta stock, el pedido se cancela.

Los reportes de ventas y stock se generan en archivos Excel usando `openpyxl`. Las transformaciones trabajan con listas y diccionarios nativos de Python.

## Instalacion de dependencias

El proyecto utiliza estas dependencias externas:

- `openpyxl`: creacion y lectura de reportes Excel.
- `requests`: consulta de recursos externos, como la cotizacion del dolar.

Para instalarlas:

```bash
python -m pip install -r requirements.txt
```

Para ejecutar la aplicacion:

```bash
python main.py
```

## Temas aplicados

- Programacion Orientada a Objetos
- Encapsulamiento
- Herencia
- Polimorfismo
- Abstraccion
- Decoradores
- Excepciones personalizadas
- Threading
- Lock
- Requests
- Reportes Excel con openpyxl
- Persistencia en JSON
