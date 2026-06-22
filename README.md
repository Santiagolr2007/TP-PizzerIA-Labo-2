# TP-PizzerIA-Labo-2
# Funcionamiento del proyecto

**PizzerIA** es un sistema desarrollado en Python que simula la gestión de una pizzería. Permite crear pedidos, administrar productos, controlar stock, procesar pedidos en cocina, registrar ventas, reponer ingredientes, consultar un recurso externo, generar reportes y guardar/cargar respaldos.

Al ejecutar `main.py`, se crea una pizzería con productos iniciales, inventario de ingredientes y una caja de dinero aleatoria entre $5000 y $20000. El menú principal se muestra por consola usando `pandas` y `tabulate`, lo que permite visualizar las opciones de forma ordenada.

El sistema trabaja con programación orientada a objetos. Los productos se representan mediante una clase base `Producto` y clases hijas como `Pizza`, `Empanada` y `Bebida`. Cada producto calcula su precio y define los ingredientes necesarios para su preparación.

Al crear un pedido, el usuario elige productos desde una tabla, indica cantidades y puede confirmar o cancelar el pedido. Antes de confirmarlo, el sistema muestra un resumen con subtotales y total estimado. Si se confirma, se genera un ticket del pedido.

Los pedidos se procesan en cocina usando hilos (`threading`) y una cola (`queue.Queue`). Si hay stock suficiente, el pedido se entrega, se descuentan los ingredientes y se registra la venta. Si falta stock, el pedido se cancela. Luego se muestra un resumen con pedidos procesados, entregados y cancelados.

El inventario permite consultar ingredientes, cantidades, precio unitario y valor total del stock. Al reponer ingredientes, el sistema calcula el costo de compra y lo descuenta del dinero disponible. Las ventas, en cambio, suman dinero a la caja de la pizzería.

El proyecto también genera reportes en Excel con `pandas` y `openpyxl`, incluyendo reportes de ventas y stock. Además, permite guardar y cargar respaldos en formato JSON, conservando stock, pedidos, ventas y dinero disponible.

Se aplican validaciones y manejo de excepciones para evitar errores comunes, como cantidades inválidas, productos inexistentes, falta de stock o problemas al cargar archivos.

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

Luego de instalar las dependencias, el programa puede ejecutarse con:

python main.py

## Temas aplicados
- Programación Orientada a Objetos
- Encapsulamiento
- Herencia
- Polimorfismo
- Abstracción
- Decoradores
- Excepciones personalizadas
- Threading
- Lock
- Requests
- Dataframes de Pandas y ETL
- Persistencia en JSON
