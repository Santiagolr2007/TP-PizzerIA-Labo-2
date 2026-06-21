from src.servicios.reportes_pandas import (generar_reporte_stock,generar_reporte_ventas,leer_reporte_excel)
from src.servicios.persistencia import (guardar_json,cargar_respaldo_pizzeria)
from src.utils.validaciones import (validar_entero_positivo,validar_texto)
from src.servicios.cocina_threads import procesar_pedidos_con_hilos
from src.servicios.proveedores import consultar_dolar_oficial
from src.servicios.inicializacion import crear_sistema
from src.utils.excepciones import PizzeriaError
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

    cliente = validar_texto(input("Cliente: "), "cliente")
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
    print(tabulate(dataframe_productos, headers="keys", tablefmt="grid", showindex=False))
    items = []

    while True:
        numero_producto = validar_entero_positivo(input("\nNúmero de producto: "),"número de producto")

        if numero_producto < 1 or numero_producto > len(catalogo):
            raise ValueError("El número de producto no existe.")

        cantidad = validar_entero_positivo(input("Cantidad: "), "cantidad")
        producto_elegido = catalogo[numero_producto - 1]
        nombre_producto = producto_elegido.nombre
        producto_ya_cargado = False

        # Agrupa productos iguales dentro del pedido.
        for item in items:
            if item[0] == nombre_producto:
                item[1] += cantidad
                producto_ya_cargado = True

        if producto_ya_cargado == False:
            items.append([nombre_producto, cantidad])

        while True:
            respuesta = input("¿Agregar otro producto? (s/n): ").lower()
            if respuesta == "s" or respuesta == "n":
                break

            print("Debe responder 's' o 'n'.")

        if respuesta == "n":
            break

    filas_resumen = []
    total_estimado = 0
    # Arma un resumen del pedido antes de confirmarlo.
    for item in items:
        nombre_producto = item[0]
        cantidad = item[1]
        producto_encontrado = None

        for producto in catalogo:
            if producto.nombre == nombre_producto:
                producto_encontrado = producto

        subtotal = producto_encontrado.calcular_precio() * cantidad
        total_estimado += subtotal

        fila = {"producto": nombre_producto,"cantidad": cantidad,"subtotal": subtotal}
        filas_resumen.append(fila)

    dataframe_resumen = pd.DataFrame(filas_resumen)
    print("\n--- RESUMEN DEL PEDIDO ---\n")
    print(tabulate(dataframe_resumen, headers="keys", tablefmt="grid", showindex=False))
    print(f"\nTotal estimado: ${total_estimado:.2f}")

    while True:
        confirmacion = input("¿Confirmar pedido? (s/n): ").lower()
        if confirmacion == "s" or confirmacion == "n":
            break

        print("Debe responder 's' o 'n'.")

    if confirmacion == "n":
        print("Pedido cancelado.")
        return

    pedido = pizzeria.crear_pedido(cliente, items)
    print(f"Pedido #{pedido.pedido_id} creado correctamente.")
    imprimir_ticket_pedido(pedido)


def mostrar_stock(pizzeria):
    # Obtiene el stock con cantidad, precio unitario y valor total.
    stock_detallado = pizzeria.inventario.obtener_stock_detallado()
    dataframe_stock = pd.DataFrame(stock_detallado)
    print("\n--- STOCK DETALLADO ---\n")
    print(tabulate(dataframe_stock, headers="keys", tablefmt="grid", showindex=False))



def procesar_cocina(pizzeria):
    pedidos_antes = pizzeria.obtener_pedidos()
    # Cuenta cuántos pedidos pendientes hay antes de procesar.
    pendientes_antes = 0
    entregados_antes = 0
    cancelados_antes = 0

    for pedido in pedidos_antes:
        if pedido.estado == "pendiente":
            pendientes_antes += 1
        elif pedido.estado == "entregado":
            entregados_antes += 1
        elif pedido.estado == "cancelado":
            cancelados_antes += 1

    # Si no hay pendientes, no tiene sentido ejecutar cocina.
    if pendientes_antes == 0:
        print("No hay pedidos pendientes para procesar.")
        return

    # Procesa los pedidos con hilos.
    procesar_pedidos_con_hilos(pizzeria,cantidad_cocineros=2)

    pedidos_despues = pizzeria.obtener_pedidos()
    entregados_despues = 0
    cancelados_despues = 0

    for pedido in pedidos_despues:
        if pedido.estado == "entregado":
            entregados_despues += 1
        elif pedido.estado == "cancelado":
            cancelados_despues += 1

    nuevos_entregados = entregados_despues - entregados_antes
    nuevos_cancelados = cancelados_despues - cancelados_antes
    print("\n--- RESUMEN DE COCINA ---")
    print(f"Pedidos procesados: {pendientes_antes}")
    print(f"Pedidos entregados: {nuevos_entregados}")
    print(f"Pedidos cancelados: {nuevos_cancelados}")


def cargar_guardado(pizzeria):
    try:
        cargar_respaldo_pizzeria(pizzeria, "respaldo_pizzeria.json")
        cantidad_pedidos = len(pizzeria.obtener_pedidos())
        cantidad_ventas = len(pizzeria.obtener_ventas())
        cantidad_ingredientes = len(pizzeria.inventario.obtener_stock())
        dinero_disponible = pizzeria.obtener_dinero()
        print("Guardado cargado correctamente.")
        print(f"Pedidos cargados: {cantidad_pedidos}")
        print(f"Ventas cargadas: {cantidad_ventas}")
        print(f"Ingredientes cargados: {cantidad_ingredientes}")
        print(f"Dinero disponible: ${dinero_disponible:.2f}")

    except FileNotFoundError as error:
        print(f"Error: {error}")

    except (ValueError, KeyError) as error:
        print(f"El archivo de guardado no es válido: {error}")


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

    try:
        dataframe = leer_reporte_excel(nombre_archivo)
    except FileNotFoundError:
        print("No se encontró el reporte. Primero debe usar la opción 7. Generar reportes.")
        return

    print(f"\n========== {nombre_archivo} ==========\n")

    if dataframe.empty:
        print("El reporte está vacío.")
    else:
        print(tabulate(dataframe, headers="keys", tablefmt="grid", showindex=False))


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

def imprimir_ticket_pedido(pedido):
    # Imprime un ticket simple del pedido creado.
    print("\n========== TICKET DEL PEDIDO ==========")
    print(f"Pedido #{pedido.pedido_id}")
    print(f"Cliente: {pedido.cliente}")
    print(f"Estado: {pedido.estado}")
    print("--------------------------------------")
    productos_agrupados = {}

    for producto, cantidad in pedido.productos:
        if producto.nombre not in productos_agrupados:
            productos_agrupados[producto.nombre] = {"cantidad": 0,"subtotal": 0}

        productos_agrupados[producto.nombre]["cantidad"] += cantidad
        productos_agrupados[producto.nombre]["subtotal"] += producto.calcular_precio() * cantidad

    for nombre_producto, datos in productos_agrupados.items():
        print(f"{nombre_producto} x{datos['cantidad']} - ${datos['subtotal']:.2f}")

    print("--------------------------------------")
    print(f"Total: ${pedido.calcular_total():.2f}")
    print("======================================\n")


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


def reponer_stock(pizzeria):
    stock_detallado = pizzeria.inventario.obtener_stock_detallado()
    dataframe_stock = pd.DataFrame(stock_detallado)
    # Renombra la columna cantidad para que sea más clara en la reposición.
    dataframe_stock = dataframe_stock.rename(columns={"cantidad": "stock_actual"})
    print("\n--- INGREDIENTES DISPONIBLES PARA REPONER ---\n")
    print(tabulate(dataframe_stock,headers="keys",tablefmt="grid",showindex=False))
    ingredientes_validos = []

    # Guarda los nombres de ingredientes válidos para poder validar la elección.
    for fila in stock_detallado:
        ingredientes_validos.append(fila["ingrediente"])

    ingrediente = validar_texto(input("\nIngrediente a reponer: "),"ingrediente").lower()

    if ingrediente not in ingredientes_validos:
        raise ValueError(f"El ingrediente '{ingrediente}' no existe. Debe elegir uno de la lista.")

    cantidad = validar_entero_positivo(input("Cantidad: "),"cantidad")
    costo_total = pizzeria.reponer_stock(ingrediente,cantidad)
    print("Stock actualizado.")
    print(f"Costo de reposición: ${costo_total:.2f}")
    print(f"Dinero disponible: ${pizzeria.obtener_dinero():.2f}")


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


def guardar_respaldo(pizzeria):
    datos = {
        "dinero": pizzeria.obtener_dinero(),
        "stock": pizzeria.inventario.obtener_stock(),
        "ventas": pizzeria.obtener_ventas(),
        "pedidos": [pedido.to_dict() for pedido in pizzeria.obtener_pedidos()],
    }

    ruta = guardar_json(datos, "respaldo_pizzeria.json")
    print(f"Respaldo guardado en: {ruta}")


def ejecutar_menu():
    # Crea la pizzería, el inventario, el stock y los productos iniciales.
    pizzeria = crear_sistema()

    opciones_menu = [
        {"OPCION": "0", "ACCION": "Cargar guardado"},
        {"OPCION": "1", "ACCION": "Crear pedido"},
        {"OPCION": "2", "ACCION": "Ver pedidos"},
        {"OPCION": "3", "ACCION": "Procesar pedidos en cocina"},
        {"OPCION": "4", "ACCION": "Ver stock"},
        {"OPCION": "5", "ACCION": "Reponer stock"},
        {"OPCION": "6", "ACCION": "Consultar recurso externo"},
        {"OPCION": "7", "ACCION": "Generar reportes"},
        {"OPCION": "8", "ACCION": "Guardar respaldo"},
        {"OPCION": "9", "ACCION": "Ver reportes"},
        {"OPCION": "10", "ACCION": "Salir"}
    ]

    dataframe_menu = pd.DataFrame(opciones_menu)

    while True:
        print("\n========== PizzerIA ==========\n")
        print(f"Dinero disponible: ${pizzeria.obtener_dinero():.2f}\n")
        print(tabulate(dataframe_menu,headers="keys",tablefmt="grid",showindex=False))
        opcion = input("\nElegí una opción: ").strip()
        print()

        try:
            if opcion == "0":
                cargar_guardado(pizzeria)

            elif opcion == "1":
                cargar_pedido(pizzeria)

            elif opcion == "2":
                mostrar_pedidos(pizzeria)

            elif opcion == "3":
                procesar_cocina(pizzeria)

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