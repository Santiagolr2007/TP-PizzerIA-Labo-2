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





if __name__ == "__main__":
    ejecutar_menu()