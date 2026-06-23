# TP-PizzerIA-Labo-2

PizzerIA es un sistema de escritorio para gestionar una pizzeria desde una interfaz grafica hecha con Tkinter. Permite administrar pedidos, catalogo, productos, stock, cocina, ventas, reportes Excel y respaldos JSON.

La aplicacion incluye un panel general, gestion de productos, carga de pedidos con retiro o delivery, control de estados operativos, reposicion de stock, consulta de proveedor externo y exportacion de reportes.

Los productos se modelan con programacion orientada a objetos usando una clase base `Producto` y clases hijas como `Pizza`, `Empanada` y `Bebida`. El catalogo puede ampliarse desde la interfaz grafica.

Los pedidos pasan por estados como pendiente, en preparacion, listo, en camino, entregado o cancelado. La cocina procesa pedidos con hilos y deja los pedidos listos; luego el usuario puede avanzar el estado segun corresponda a retiro o delivery.

Los reportes se generan con `openpyxl` usando listas y diccionarios nativos de Python.

## Instalacion

```bash
python -m pip install -r requirements.txt
```

## Ejecucion

```bash
python main.py
```

## Dependencias

- `openpyxl`: lectura y escritura de reportes Excel.
- `requests`: consulta opcional del proveedor externo.

## Temas aplicados

- Programacion Orientada a Objetos
- Encapsulamiento
- Herencia
- Polimorfismo
- Decoradores
- Excepciones personalizadas
- Threading
- Lock
- Requests
- Reportes Excel con openpyxl
- Persistencia en JSON
