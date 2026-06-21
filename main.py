from src.servicios.reportes_pandas import (generar_reporte_stock, generar_reporte_ventas,leer_reporte_excel)
from src.servicios.persistencia import (guardar_json,cargar_respaldo_pizzeria)
from src.utils.validaciones import (validar_entero_positivo, validar_texto)
from src.servicios.cocina_threads import procesar_pedidos_con_hilos
from src.servicios.proveedores import consultar_dolar_oficial
from src.utils.excepciones import ProveedorNoDisponibleError
from src.modelos.producto import (Pizza, Empanada, Bebida)
from src.servicios.inicializacion import crear_sistema
from src.utils.excepciones import PizzeriaError
from src.modelos.inventario import Inventario
from src.modelos.pizzeria import Pizzeria
from tabulate import tabulate
import pandas as pd


def mostrar_catalogo(pizzeria):
    print("\n--- PRODUCTOS ---")
    for numero, producto in enumerate(pizzeria.obtener_catalogo(), start=1):
        print(f"{numero}. {producto.nombre} - ${producto.calcular_precio():.2f}")

def cargar_pedido(pizzeria):
    catalogo = pizzeria.obtener_catalogo()

    if len(catalogo) == 0:
        print("No hay productos cargados en el catálogo.")
        return

    cliente = validar_texto(input("Cliente: "),"cliente")

    filas_productos = []

    # Arma un DataFrame con todos los productos disponibles.
    for numero, producto in enumerate(catalogo, start=1):
        fila = {
            "numero": numero,
            "producto": producto.nombre,
            "tipo": producto.__class__.__name__,
            "precio": producto.calcular_precio()
        }
        filas_productos.append(fila)

    dataframe_productos = pd.DataFrame(filas_productos)
    print("\n--- PRODUCTOS DISPONIBLES ---\n")
    print(tabulate(dataframe_productos,headers="keys",tablefmt="grid",showindex=False))
    items = []

    while True:
        numero_producto = validar_entero_positivo(input("\nNúmero de producto: "),"número de producto")

        if numero_producto < 1 or numero_producto > len(catalogo):
            raise ValueError("El número de producto no existe.")

        cantidad = validar_entero_positivo(input("Cantidad: "),"cantidad")

        producto_elegido = catalogo[numero_producto - 1]
        nombre_producto = producto_elegido.nombre
        producto_ya_cargado = False

        # Agrupa productos iguales dentro del pedido.
        for item in items:
            if item[0] == nombre_producto:
                item[1] += cantidad
                producto_ya_cargado = True

        if producto_ya_cargado == False:
            items.append([nombre_producto,cantidad])

        respuesta = input("¿Agregar otro producto? (s/n): ").lower()
        if respuesta == "n":
                    break
        elif respuesta == "s":
                    continue
        else:
                    print("Opción no válida. Se finalizará el pedido.")
                    break

    pedido = pizzeria.crear_pedido(cliente,items)
    print(f"Pedido #{pedido.pedido_id} creado correctamente.")


def obtener_productos_agrupados_pedido(pedido):
    # Agrupa productos iguales dentro de un mismo pedido.
    productos_agrupados = {}

    for producto, cantidad in pedido.productos:
        if producto.nombre not in productos_agrupados:
            productos_agrupados[producto.nombre] = {"cantidad": 0,"subtotal": 0}

        productos_agrupados[producto.nombre]["cantidad"] += cantidad
        productos_agrupados[producto.nombre]["subtotal"] += producto.calcular_precio() * cantidad
    textos_productos = []

    for nombre_producto, datos in productos_agrupados.items():
        texto = (
            f"{nombre_producto} x{datos['cantidad']} (${datos['subtotal']:.2f})")

        textos_productos.append(texto)

    return ", ".join(textos_productos)


def mostrar_pedidos(pizzeria):
    pedidos = pizzeria.obtener_pedidos()

    if len(pedidos) == 0:
        print("No hay pedidos cargados.")
        return

    filas = []

    for pedido in pedidos:
        productos = obtener_productos_agrupados_pedido(pedido)
        fila = {"pedido_id": pedido.pedido_id,"cliente": pedido.cliente,"estado": pedido.estado,"productos": productos,"total": pedido.calcular_total()}
        filas.append(fila)

    dataframe_pedidos = pd.DataFrame(filas)
    print("\n--- PEDIDOS ---\n")
    print(tabulate(dataframe_pedidos,headers="keys",tablefmt="grid",showindex=False))


def mostrar_stock(pizzeria):
    # Obtiene el stock actual.
    stock = pizzeria.inventario.obtener_stock()
    # Convierte el diccionario de stock en una lista de filas.
    filas = []

    for ingrediente, cantidad in stock.items():

        fila = {"ingrediente": ingrediente,"cantidad": cantidad}
        filas.append(fila)

    # Crea el DataFrame.
    dataframe_stock = pd.DataFrame(filas)
    print("\n--- STOCK ---\n")
    # Muestra el DataFrame completo en consola.
    print(tabulate(dataframe_stock,headers="keys",tablefmt="grid",showindex=False))


def reponer_stock(pizzeria):
    stock = pizzeria.inventario.obtener_stock()
    filas = []

    for ingrediente, cantidad in stock.items():
        fila = {"ingrediente": ingrediente,"stock_actual": cantidad}
        filas.append(fila)

    dataframe_stock = pd.DataFrame(filas)
    print("\n--- INGREDIENTES DISPONIBLES PARA REPONER ---\n")
    print(tabulate(dataframe_stock,headers="keys",tablefmt="grid",showindex=False))
    ingrediente = validar_texto(input("\nIngrediente a reponer: "),"ingrediente").lower()

    if ingrediente not in stock:
        raise ValueError(f"El ingrediente '{ingrediente}' no existe. Debe elegir uno de la lista.")

    cantidad = validar_entero_positivo(input("Cantidad: "),"cantidad")
    pizzeria.inventario.reponer(ingrediente,cantidad)
    print("Stock actualizado.")


def consultar_proveedor():
    try:
        valor = consultar_dolar_oficial()
        print(f"Dólar oficial de venta: ${valor:.2f}")
    except Exception as error:
        print(f"No se pudo consultar el recurso externo: {error}")


def generar_reportes(pizzeria):
    ruta_ventas = generar_reporte_ventas(pizzeria.obtener_ventas())
    ruta_stock = generar_reporte_stock(pizzeria.inventario.obtener_stock_detallado())
    print("Reportes generados correctamente.")
    print(f"Reporte de ventas: {ruta_ventas}")
    print(f"Reporte de stock: {ruta_stock}")

def ver_reportes_consola():

    print("\n========== VER REPORTES ==========")
    print("1. Reporte de ventas")
    print("2. Reporte de stock")
    opcion = input("Elegí un reporte: ")

    if opcion == "1":
        nombre_archivo = "reporte_ventas.xlsx"

    elif opcion == "2":
        nombre_archivo = "reporte_stock.xlsx"

    else:
        raise ValueError("La opción de reporte no existe.")
    
    dataframe = leer_reporte_excel(nombre_archivo)
    print(f"\n========== {nombre_archivo} ==========\n")

    if dataframe.empty:
        print("El reporte está vacío.")
    else:
        print(tabulate(dataframe,headers="keys",tablefmt="grid",showindex=False))

def guardar_respaldo(pizzeria):
    datos = {
        "stock": pizzeria.inventario.obtener_stock(),
        "ventas": pizzeria.obtener_ventas(),
        "pedidos": [pedido.to_dict() for pedido in pizzeria.obtener_pedidos()],
    }
    ruta = guardar_json(datos, "respaldo_pizzeria.json")
    print(f"Respaldo guardado en: {ruta}")


def cargar_guardado(pizzeria):
    try:
        cargar_respaldo_pizzeria(pizzeria,"respaldo_pizzeria.json")

        cantidad_pedidos = len(pizzeria.obtener_pedidos())

        cantidad_ventas = len(pizzeria.obtener_ventas())

        print("Guardado cargado correctamente.")
        print(f"Pedidos cargados: {cantidad_pedidos}")
        print(f"Ventas cargadas: {cantidad_ventas}")

    except FileNotFoundError as error:
        print(f"Error: {error}")

    except (ValueError, KeyError) as error:
        print(f"El archivo de guardado no es válido: {error}")


def ejecutar_menu():
    # Crea la pizzería, el inventario, el stock y los productos iniciales.
    pizzeria = crear_sistema()

    while True:
        print(
            """
========== PizzerIA ==========
0. Cargar guardado
1. Crear pedido
2. Ver pedidos
3. Procesar pedidos en cocina
4. Ver stock
5. Reponer stock
6. Consultar recurso externo
7. Generar reportes
8. Guardar respaldo
9. Ver reportes
10. Salir""")

        opcion = input("\nElegí una opción: ").strip()
        print()  # Salto de línea para mejorar legibilidad.

        try:
            if opcion == "0":
                cargar_guardado(pizzeria)
            elif opcion == "1":
                cargar_pedido(pizzeria)
            elif opcion == "2":
                mostrar_pedidos(pizzeria)
            elif opcion == "3":
                procesar_pedidos_con_hilos(pizzeria, cantidad_cocineros=2)
            elif opcion == "4":
                mostrar_stock(pizzeria)
            elif opcion == "5":
                reponer_stock(pizzeria)
            elif opcion == "6":
                consultar_proveedor()
            elif opcion == "7":
                generar_reportes(pizzeria)
            elif opcion == "8":
                guardar_respaldo(pizzeria)
            elif opcion == "9":
                ver_reportes_consola()
            elif opcion == "10":
                guardar_respaldo(pizzeria)
                print("Programa finalizado.")
                break
            else:
                print("Opción inválida.")
        except (PizzeriaError, ValueError) as error:
            print(f"Error: {error}")
        except Exception as error:
            print(f"Error inesperado: {error}")


if __name__ == "__main__":
    ejecutar_menu()