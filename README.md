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
El proyecto integra varios temas de la materia, como programación orientada a objetos, herencia, encapsulamiento, excepciones, decoradores, archivos JSON, APIs con `requests`, reportes con `pandas`, concurrencia con hilos y organización modular del código.

## Instalación de dependencias
El proyecto utiliza algunas librerías externas de Python, declaradas en el archivo requirements.txt.
Las dependencias utilizadas son:

**pandas**
**openpyxl**
**requests**
**tabulate**

* pandas: se utiliza para procesar datos y generar reportes de ventas y stock.
* openpyxl: permite exportar los reportes a archivos Excel con extensión .xlsx.
* requests: se utiliza para consultar recursos externos mediante internet, como una API de cotización del dólar.
* tabulate: mostrar dataframe de manera mas estetica

Para instalar todas las dependencias necesarias, se debe abrir una terminal en la carpeta principal del proyecto y ejecutar:

python -m pip install -r requirements.txt

Para ejecutar la aplicacion:

python main.py

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
- Dataframes de Pandas y ETL
- Persistencia en JSON
