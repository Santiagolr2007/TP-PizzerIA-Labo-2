# Puente entre la interfaz y los reportes Excel. Mantiene la sincronización de ventas en un solo lugar antes de generar archivos.
from src.servicios.reportes_excel import generar_reporte_stock, generar_reporte_ventas


def sincronizar_ventas_entregadas(pizzeria):
    # Antes de mostrar reportes se asegura que los pedidos entregados ya figuren
    # en ventas, incluso si fueron entregas por retiro o delivery.
    # Completa ventas faltantes desde pedidos entregados antes de mostrar o guardar reportes.
    return pizzeria.sincronizar_ventas_entregadas()


def generar_archivos_reportes_actualizados(pizzeria):
    # Flujo completo de exportacion: sincroniza ventas, genera Excel de ventas
    # y genera Excel de stock usando los datos actualizados del sistema.
    sincronizar_ventas_entregadas(pizzeria)
    ruta_ventas = generar_reporte_ventas(pizzeria.obtener_ventas())
    ruta_stock = generar_reporte_stock(pizzeria.inventario.obtener_stock_detallado())
    return ruta_ventas, ruta_stock
