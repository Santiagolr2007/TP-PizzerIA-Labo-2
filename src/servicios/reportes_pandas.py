from src.servicios.etl import transformar_stock, transformar_ventas
from src.utils.decoradores import medir_tiempo, registrar_log
from pathlib import Path
import pandas as pd

def obtener_carpeta_reportes():
    # Obtiene la carpeta principal del proyecto.
    ruta_proyecto = Path(__file__).resolve().parents[2]
    # Define la carpeta donde se guardan los reportes.
    carpeta_reportes = ruta_proyecto / "reportes"
    # Crea la carpeta si todavía no existe.
    carpeta_reportes.mkdir(parents=True, exist_ok=True)
    return carpeta_reportes


def obtener_ruta_reporte(nombre_archivo):
    # Arma la ruta completa del reporte.
    carpeta_reportes = obtener_carpeta_reportes()
    return carpeta_reportes / nombre_archivo


@registrar_log
@medir_tiempo
def generar_reporte_ventas(ventas,nombre_archivo="reporte_ventas.xlsx"):
    dataframe = transformar_ventas(ventas)
    destino = obtener_ruta_reporte(nombre_archivo)
    if dataframe.empty:
        reporte_ventas = pd.DataFrame([{"mensaje": "Todavía no existen ventas registradas."}])
    else:
        dataframe = dataframe.sort_values(by=["fecha", "pedido_id"])
        pedidos = dataframe[["pedido_id","fecha","cliente"]].drop_duplicates(subset=["pedido_id"])
        filas_reporte = []

        for indice, pedido in pedidos.iterrows():
            pedido_id = pedido["pedido_id"]
            filas_pedido = dataframe[dataframe["pedido_id"] == pedido_id]
            productos_agrupados = filas_pedido.groupby("producto",as_index=False).agg(cantidad=("cantidad", "sum"),subtotal=("subtotal", "sum"))
            textos_productos = []

            for indice_producto, producto in productos_agrupados.iterrows():
                texto_producto = (
                    f"{producto['producto']} x{int(producto['cantidad'])} (${producto['subtotal']:.2f})")

                textos_productos.append(texto_producto)

            total_pedido = productos_agrupados["subtotal"].sum()
            cantidad_total = productos_agrupados["cantidad"].sum()

            fila = {
                "pedido_id": pedido_id,
                "fecha": pedido["fecha"],
                "cliente": pedido["cliente"],
                "productos": ", ".join(textos_productos),
                "cantidad_total_productos": cantidad_total,
                "total_vendido_pedido": total_pedido
            }

            filas_reporte.append(fila)

        reporte_ventas = pd.DataFrame(filas_reporte)
        reporte_ventas["total_vendido_hasta_el_momento"] = (reporte_ventas["total_vendido_pedido"].cumsum())

    with pd.ExcelWriter(destino,engine="openpyxl") as escritor:
        reporte_ventas.to_excel(escritor,sheet_name="Ventas",index=False)

    return str(destino)



@registrar_log
@medir_tiempo
def generar_reporte_stock(stock,nombre_archivo="reporte_stock.xlsx"):
    dataframe = transformar_stock(stock)
    destino = obtener_ruta_reporte(nombre_archivo)

    with pd.ExcelWriter(destino,engine="openpyxl") as escritor:
        dataframe.to_excel(escritor,sheet_name="Stock",index=False)

    return str(destino)


def leer_reporte_excel(nombre_archivo):
    # Busca el reporte dentro de la carpeta reportes.
    ruta_reporte = obtener_ruta_reporte(nombre_archivo)

    # Verifica que el archivo exista.
    if not ruta_reporte.exists():
        raise FileNotFoundError(f"No existe el reporte '{nombre_archivo}'. Primero debe generarlo.")

    # Lee la única hoja del archivo Excel.
    dataframe = pd.read_excel(ruta_reporte)
    return dataframe