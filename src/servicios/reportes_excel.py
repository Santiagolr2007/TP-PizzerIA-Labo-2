from datetime import datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo

from src.utils.decoradores import medir_tiempo, registrar_log


VENTAS_COLUMNAS = [
    "pedido_id",
    "fecha",
    "cliente",
    "productos",
    "cantidad_total_productos",
    "total_vendido_pedido",
    "total_vendido_hasta_el_momento",
]

VENTAS_ENCABEZADOS = {
    "pedido_id": "ID",
    "fecha": "Fecha",
    "cliente": "Cliente",
    "productos": "Productos",
    "cantidad_total_productos": "Cant. total",
    "total_vendido_pedido": "Total pedido",
    "total_vendido_hasta_el_momento": "Total acumulado",
}

STOCK_COLUMNAS = [
    "ingrediente",
    "cantidad",
    "precio_unitario",
    "valor_total_stock",
    "estado",
]

STOCK_ENCABEZADOS = {
    "ingrediente": "Ingrediente",
    "cantidad": "Cantidad",
    "precio_unitario": "Precio unitario",
    "valor_total_stock": "Valor total",
    "estado": "Estado",
}


def _encabezado_visible(encabezado):
    encabezados = {}
    encabezados.update(VENTAS_ENCABEZADOS)
    encabezados.update(STOCK_ENCABEZADOS)
    return encabezados.get(encabezado, encabezado)


def obtener_carpeta_reportes():
    ruta_proyecto = Path(__file__).resolve().parents[2]
    carpeta_reportes = ruta_proyecto / "reportes"
    carpeta_reportes.mkdir(parents=True, exist_ok=True)
    return carpeta_reportes


def obtener_ruta_reporte(nombre_archivo):
    carpeta_reportes = obtener_carpeta_reportes()
    return carpeta_reportes / nombre_archivo


def _convertir_entero(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _convertir_numero(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _convertir_fecha(valor):
    if isinstance(valor, datetime):
        return valor

    if not valor:
        return None

    try:
        return datetime.fromisoformat(str(valor))
    except ValueError:
        return None


def _formato_moneda(valor):
    texto = f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"${texto}"


def transformar_ventas(ventas):
    filas = []
    claves_vistas = set()

    for venta in ventas:
        pedido_id = _convertir_entero(venta.get("pedido_id"))
        fecha = _convertir_fecha(venta.get("fecha"))
        cliente = str(venta.get("cliente", "")).strip()
        producto = str(venta.get("producto", "")).strip()
        cantidad = _convertir_entero(venta.get("cantidad"))
        precio_unitario = _convertir_numero(venta.get("precio_unitario"))
        subtotal = _convertir_numero(venta.get("subtotal"))

        if None in (pedido_id, fecha, cantidad, precio_unitario, subtotal):
            continue

        if not producto:
            continue

        clave = (pedido_id, producto, cantidad)
        if clave in claves_vistas:
            continue

        claves_vistas.add(clave)
        filas.append(
            {
                "pedido_id": pedido_id,
                "fecha": fecha,
                "cliente": cliente,
                "producto": producto,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "subtotal": subtotal,
            }
        )

    filas.sort(key=lambda fila: (fila["fecha"], fila["pedido_id"]))
    return filas


def transformar_stock(stock):
    if isinstance(stock, list):
        filas_origen = stock
    else:
        filas_origen = []
        for ingrediente, cantidad in stock.items():
            filas_origen.append(
                {
                    "ingrediente": ingrediente,
                    "cantidad": cantidad,
                    "precio_unitario": 0,
                }
            )

    filas = []
    for fila_origen in filas_origen:
        ingrediente = str(fila_origen.get("ingrediente", "")).strip()
        cantidad = _convertir_numero(fila_origen.get("cantidad"))
        precio_unitario = _convertir_numero(fila_origen.get("precio_unitario"))

        if not ingrediente:
            continue

        if cantidad is None:
            cantidad = 0

        if precio_unitario is None:
            precio_unitario = 0

        valor_total = cantidad * precio_unitario
        estado = "Reponer" if cantidad <= 5 else "Disponible"
        filas.append(
            {
                "ingrediente": ingrediente,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "valor_total_stock": valor_total,
                "estado": estado,
            }
        )

    filas.sort(key=lambda fila: fila["ingrediente"])
    return filas


def _agrupar_ventas_por_pedido(filas_ventas):
    pedidos = {}

    for venta in filas_ventas:
        pedido_id = venta["pedido_id"]
        if pedido_id not in pedidos:
            pedidos[pedido_id] = {
                "pedido_id": pedido_id,
                "fecha": venta["fecha"],
                "cliente": venta["cliente"],
                "productos": {},
            }

        productos = pedidos[pedido_id]["productos"]
        nombre_producto = venta["producto"]
        if nombre_producto not in productos:
            productos[nombre_producto] = {"cantidad": 0, "subtotal": 0}

        productos[nombre_producto]["cantidad"] += venta["cantidad"]
        productos[nombre_producto]["subtotal"] += venta["subtotal"]

    return sorted(pedidos.values(), key=lambda pedido: (pedido["fecha"], pedido["pedido_id"]))


def armar_reporte_ventas(ventas):
    filas_ventas = transformar_ventas(ventas)

    if not filas_ventas:
        return [{"mensaje": "Todavia no existen ventas registradas."}]

    filas_reporte = []
    acumulado = 0

    for pedido in _agrupar_ventas_por_pedido(filas_ventas):
        textos_productos = []
        cantidad_total = 0
        total_pedido = 0

        for nombre_producto, datos in pedido["productos"].items():
            cantidad_total += datos["cantidad"]
            total_pedido += datos["subtotal"]
            textos_productos.append(
                f"{nombre_producto} x{datos['cantidad']} ({_formato_moneda(datos['subtotal'])})"
            )

        acumulado += total_pedido
        filas_reporte.append(
            {
                "pedido_id": pedido["pedido_id"],
                "fecha": pedido["fecha"],
                "cliente": pedido["cliente"],
                "productos": ", ".join(textos_productos),
                "cantidad_total_productos": cantidad_total,
                "total_vendido_pedido": total_pedido,
                "total_vendido_hasta_el_momento": acumulado,
            }
        )

    return filas_reporte


def _crear_libro(nombre_hoja, columnas, filas, encabezados):
    libro = Workbook()
    hoja = libro.active
    hoja.title = nombre_hoja

    columnas_internas = columnas
    encabezados_visibles = [encabezados.get(columna, columna) for columna in columnas]
    if filas and "mensaje" in filas[0]:
        columnas_internas = ["mensaje"]
        encabezados_visibles = ["Estado"]

    hoja.append(encabezados_visibles)
    for fila in filas:
        hoja.append([fila.get(columna, "") for columna in columnas_internas])

    _aplicar_estilos(hoja, nombre_hoja)
    return libro


def _aplicar_estilos(hoja, nombre_tabla):
    encabezado_fill = PatternFill("solid", fgColor="111827")
    encabezado_font = Font(color="FFFFFF", bold=True)

    for celda in hoja[1]:
        celda.fill = encabezado_fill
        celda.font = encabezado_font
        celda.alignment = Alignment(horizontal="center")

    for fila in hoja.iter_rows(min_row=2):
        for celda in fila:
            celda.alignment = Alignment(vertical="top", wrap_text=True)

    for columna in hoja.columns:
        ancho = 12
        letra = columna[0].column_letter
        for celda in columna:
            valor = "" if celda.value is None else str(celda.value)
            ancho = max(ancho, min(len(valor) + 2, 42))
        hoja.column_dimensions[letra].width = ancho

    hoja.freeze_panes = "A2"

    ultima_fila = hoja.max_row
    ultima_columna = hoja.max_column
    referencia = f"A1:{hoja.cell(row=ultima_fila, column=ultima_columna).coordinate}"
    tabla = Table(displayName=f"Tabla{nombre_tabla}", ref=referencia)
    estilo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    tabla.tableStyleInfo = estilo
    hoja.add_table(tabla)


@registrar_log
@medir_tiempo
def generar_reporte_ventas(ventas, nombre_archivo="reporte_ventas.xlsx"):
    filas_reporte = armar_reporte_ventas(ventas)
    destino = obtener_ruta_reporte(nombre_archivo)
    libro = _crear_libro("Ventas", VENTAS_COLUMNAS, filas_reporte, VENTAS_ENCABEZADOS)
    libro.save(destino)
    return str(destino)


@registrar_log
@medir_tiempo
def generar_reporte_stock(stock, nombre_archivo="reporte_stock.xlsx"):
    filas_reporte = transformar_stock(stock)
    destino = obtener_ruta_reporte(nombre_archivo)
    libro = _crear_libro("Stock", STOCK_COLUMNAS, filas_reporte, STOCK_ENCABEZADOS)
    libro.save(destino)
    return str(destino)


def leer_reporte_excel(nombre_archivo):
    ruta_reporte = obtener_ruta_reporte(nombre_archivo)

    if not ruta_reporte.exists():
        raise FileNotFoundError(f"No existe el reporte '{nombre_archivo}'. Primero debe generarlo.")

    libro = load_workbook(ruta_reporte, data_only=True)
    hoja = libro.active
    filas = list(hoja.iter_rows(values_only=True))

    if not filas:
        return []

    encabezados = [_encabezado_visible(str(valor)) if valor is not None else "" for valor in filas[0]]
    resultado = []

    for valores in filas[1:]:
        if all(valor is None for valor in valores):
            continue

        fila = {}
        for indice, encabezado in enumerate(encabezados):
            if not encabezado:
                continue

            valor = valores[indice] if indice < len(valores) else ""
            fila[encabezado] = valor

        resultado.append(fila)

    return resultado
