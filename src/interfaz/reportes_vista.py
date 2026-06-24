from src.servicios.reportes_excel import generar_reporte_stock, generar_reporte_ventas


def sincronizar_ventas_entregadas(pizzeria):
    # Completa ventas faltantes desde pedidos entregados antes de mostrar o guardar reportes.
    return pizzeria.sincronizar_ventas_entregadas()


def generar_archivos_reportes_actualizados(pizzeria):
    sincronizar_ventas_entregadas(pizzeria)
    ruta_ventas = generar_reporte_ventas(pizzeria.obtener_ventas())
    ruta_stock = generar_reporte_stock(pizzeria.inventario.obtener_stock_detallado())
    return ruta_ventas, ruta_stock
