from pathlib import Path

from src.utils.decoradores import medir_tiempo, registrar_log


def obtener_carpeta_tickets():
    ruta_proyecto = Path(__file__).resolve().parents[2]
    carpeta_tickets = ruta_proyecto / "output" / "pdf"
    carpeta_tickets.mkdir(parents=True, exist_ok=True)
    return carpeta_tickets


def obtener_ruta_ticket(pedido):
    nombre_archivo = f"ticket_pedido_{pedido.pedido_id}.pdf"
    return obtener_carpeta_tickets() / nombre_archivo


def _formato_moneda(valor):
    texto = f"{float(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"$ {texto}"


def _estado_visible(estado):
    return str(estado).replace("_", " ").capitalize()


@registrar_log
@medir_tiempo
def generar_ticket_pdf(pedido):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as error:
        raise RuntimeError("Para generar tickets PDF instala la dependencia 'reportlab'.") from error

    destino = obtener_ruta_ticket(pedido)
    estilos = getSampleStyleSheet()
    documento = SimpleDocTemplate(
        str(destino),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Ticket pedido {pedido.pedido_id}",
    )

    elementos = []
    titulo = Paragraph("<b>PizzerIA</b>", estilos["Title"])
    subtitulo = Paragraph("Comprobante de pedido", estilos["Heading3"])
    elementos.extend([titulo, subtitulo, Spacer(1, 8)])

    fecha = pedido.fecha.strftime("%d/%m/%Y %H:%M")
    datos_pedido = [
        ["Pedido", f"#{pedido.pedido_id}", "Fecha", fecha],
        ["Cliente", pedido.cliente, "Estado", _estado_visible(pedido.estado)],
        ["Entrega", pedido.tipo_entrega, "Dirección", pedido.direccion or "-"],
    ]
    tabla_datos = Table(datos_pedido, colWidths=[30 * mm, 58 * mm, 30 * mm, 58 * mm])
    tabla_datos.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF7ED")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1F2937")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#FED7AA")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#FED7AA")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    elementos.extend([tabla_datos, Spacer(1, 14)])

    filas = [["Producto", "Cant.", "Unitario", "Desc.", "Total"]]
    for linea in pedido.iterar_lineas_detalle():
        filas.append(
            [
                linea["nombre"],
                linea["cantidad"],
                _formato_moneda(linea["precio_unitario"]),
                _formato_moneda(linea["descuento"]) if linea["descuento"] else "-",
                _formato_moneda(linea["subtotal"]),
            ]
        )

    tabla_items = Table(filas, colWidths=[72 * mm, 18 * mm, 30 * mm, 28 * mm, 30 * mm], repeatRows=1)
    tabla_items.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E5E7EB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF7ED")]),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    elementos.extend([tabla_items, Spacer(1, 12)])

    promociones = pedido.obtener_promociones()
    if promociones:
        for promocion in promociones:
            texto = (
                f"{promocion['nombre']}: {promocion['descripcion']} "
                f"({_formato_moneda(promocion['descuento'])})"
            )
            elementos.append(Paragraph(texto, estilos["BodyText"]))
        elementos.append(Spacer(1, 8))

    resumen = [
        ["Subtotal", _formato_moneda(pedido.calcular_subtotal())],
        ["Descuento", _formato_moneda(pedido.calcular_descuento_total())],
        ["Total", _formato_moneda(pedido.calcular_total())],
    ]
    tabla_totales = Table(resumen, colWidths=[132 * mm, 46 * mm], hAlign="RIGHT")
    tabla_totales.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEABOVE", (0, 2), (-1, 2), 1, colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 2), (-1, 2), colors.HexColor("#C2410C")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elementos.append(tabla_totales)
    documento.build(elementos)
    return str(destino)
