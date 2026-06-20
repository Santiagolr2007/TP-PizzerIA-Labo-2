from pathlib import Path
import pandas as pd
from src.servicios.etl import transformar_stock, transformar_ventas
from src.utils.decoradores import medir_tiempo, registrar_log


def obtener_carpeta_reportes():
    # Obtiene la carpeta principal del proyecto.
    ruta_proyecto = Path(__file__).resolve().parents[2]
    # Define la carpeta donde se guardarán los reportes.
    carpeta_reportes = ruta_proyecto / "reportes"
    # Crea la carpeta si todavía no existe.
    carpeta_reportes.mkdir(exist_ok=True)
    return carpeta_reportes


@registrar_log
@medir_tiempo
def generar_reporte_ventas(ventas,nombre_archivo="reporte_ventas.xlsx"):

    dataframe = transformar_ventas(ventas)
    # Obtiene la carpeta reportes.
    carpeta_reportes = obtener_carpeta_reportes()
    # Une la carpeta con el nombre del archivo.
    destino = carpeta_reportes / nombre_archivo

    if dataframe.empty:
        resumen = pd.DataFrame([{"mensaje": "Todavía no existen ventas registradas."}])

    else:
        resumen = dataframe.groupby("producto",as_index=False).agg(cantidad_vendida=("cantidad", "sum"),total_recaudado=("subtotal", "sum"))
        resumen = resumen.sort_values("total_recaudado",ascending=False)

    with pd.ExcelWriter(destino,engine="openpyxl") as escritor:
        dataframe.to_excel(escritor,sheet_name="Ventas",index=False)
        resumen.to_excel(escritor,sheet_name="Resumen",index=False)
        
    return str(destino)


@registrar_log
@medir_tiempo
def generar_reporte_stock(stock,nombre_archivo="reporte_stock.xlsx"):

    dataframe = transformar_stock(stock)
    # Obtiene la carpeta reportes.
    carpeta_reportes = obtener_carpeta_reportes()
    # Une la carpeta con el nombre del archivo.
    destino = carpeta_reportes / nombre_archivo

    with pd.ExcelWriter(destino,engine="openpyxl") as escritor:
        dataframe.to_excel(escritor,sheet_name="Stock",index=False)

    return str(destino)