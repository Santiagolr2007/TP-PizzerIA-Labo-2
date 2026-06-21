from src.modelos.inventario import Inventario
from src.modelos.pizzeria import Pizzeria
from src.modelos.producto import Pizza, Empanada, Bebida
from src.servicios.cocina_threads import procesar_pedidos_con_hilos
from src.servicios.proveedores import consultar_dolar_oficial
from src.servicios.reportes_pandas import generar_reporte_stock, generar_reporte_ventas
from src.servicios.persistencia import (guardar_json,cargar_respaldo_pizzeria)
from src.utils.excepciones import PizzeriaError
from src.utils.validaciones import validar_entero_positivo, validar_texto
import random

def crear_sistema():
    stock_inicial = {
        "harina": random.randint(10, 100),
        "salsa": random.randint(10, 100),
        "mozzarella": random.randint(10, 100),
        "tapas_empanada": random.randint(10, 100),
        "relleno_empanada": random.randint(10, 100),
        "gaseosa": random.randint(10, 100),
    }

    inventario = Inventario(stock_inicial)
    pizzeria = Pizzeria(inventario)

    pizzeria.registrar_producto(Pizza("Pizza muzzarella", 8000, "grande"))
    pizzeria.registrar_producto(Empanada("Empanada de carne", 1200))
    pizzeria.registrar_producto(Bebida("Gaseosa", 2500))

    return pizzeria


def mostrar_catalogo(pizzeria):
    print("\n--- PRODUCTOS ---")
    for numero, producto in enumerate(pizzeria.obtener_catalogo(), start=1):
        print(f"{numero}. {producto.nombre} - ${producto.calcular_precio():.2f}")


def cargar_pedido(pizzeria):
    cliente = validar_texto(input("Nombre del cliente: "), "cliente")
    catalogo = pizzeria.obtener_catalogo()
    items = []

    while True:
        mostrar_catalogo(pizzeria)
        opcion = validar_entero_positivo(input("Número de producto: "), "producto")
        if opcion > len(catalogo):
            print("Producto inexistente.")
            continue

        cantidad = validar_entero_positivo(input("Cantidad: "), "cantidad")
        items.append((catalogo[opcion - 1].nombre, cantidad))

        continuar = input("¿Agregar otro producto? (s/n): ").strip().lower()
        if continuar != "s":
            break

    pedido = pizzeria.crear_pedido(cliente, items)
    print(f"Pedido #{pedido.pedido_id} cargado. Total: ${pedido.calcular_total():.2f}")


def mostrar_pedidos(pizzeria):
    pedidos = pizzeria.obtener_pedidos()
    if not pedidos:
        print("No hay pedidos cargados.")
        return

    print("\n--- PEDIDOS ---")
    for pedido in pedidos:
        print(
            f"Pedido #{pedido.pedido_id} | Cliente: {pedido.cliente} | "
            f"Estado: {pedido.estado} | Total: ${pedido.calcular_total():.2f}"
        )


def mostrar_stock(pizzeria):
    print("\n--- STOCK ---")
    for producto, cantidad in pizzeria.inventario.obtener_stock().items():
        print(f"{producto}: {cantidad}")


def reponer_stock(pizzeria):
    ingrediente = validar_texto(input("Ingrediente a reponer: "), "ingrediente").lower()
    cantidad = validar_entero_positivo(input("Cantidad: "), "cantidad")
    pizzeria.inventario.reponer(ingrediente, cantidad)
    print("Stock actualizado.")


def consultar_proveedor():
    try:
        valor = consultar_dolar_oficial()
        print(f"Dólar oficial de venta: ${valor:.2f}")
    except Exception as error:
        print(f"No se pudo consultar el recurso externo: {error}")


def generar_reportes(pizzeria):
    ruta_ventas = generar_reporte_ventas(pizzeria.obtener_ventas())
    ruta_stock = generar_reporte_stock(pizzeria.inventario.obtener_stock())
    print(f"Reporte de ventas generado: {ruta_ventas}")
    print(f"Reporte de stock generado: {ruta_stock}")


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
9. Salir\n""")

        opcion = input("Elegí una opción: ").strip()

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