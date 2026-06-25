import re
from pathlib import Path
from src.utils.decoradores import medir_tiempo, registrar_log

PATRON_TICKET = re.compile(r"ticket_(\d+)_pedido_\d+\.pdf$") 

"""ticket_        tiene que empezar con "ticket_"
(\d+)          busca uno o más números y los guarda
_pedido_       después tiene que venir "_pedido_"
\d+            busca uno o más números del pedido
\.pdf          termina en ".pdf"
$              asegura que ahí termine el nombre del archivo"""
#ticket_0007_pedido_15.pdf

def obtener_carpeta_tickets():
    # Los tickets se guardan fuera del codigo fuente, dentro de output/pdf.
    # Si la carpeta se borra, se vuelve a crear automaticamente.
    ruta_proyecto = Path(__file__).resolve().parents[2]
    carpeta_tickets = ruta_proyecto / "output" / "pdf"
    carpeta_tickets.mkdir(parents=True, exist_ok=True)
    return carpeta_tickets


def obtener_siguiente_numero_ticket():
    # Busca el numero mas alto de ticket existente y propone el siguiente.
    # Esto evita pisar comprobantes anteriores aunque el programa se cierre.
    carpeta_tickets = obtener_carpeta_tickets()
    ultimo_numero = 0
    for ruta in carpeta_tickets.glob("ticket_*_pedido_*.pdf"): #.glob busca arhivos que coincidan con esas palabras
        coincidencia = PATRON_TICKET.match(ruta.name) #Se fija si los nombres son iguales
        if coincidencia:
            ultimo_numero = max(ultimo_numero, int(coincidencia.group(1))) # busca el numero de ticket maximo
    return ultimo_numero + 1 #le suma 1


def obtener_ruta_ticket(pedido):
    # Construye un nombre unico combinando numero de ticket y numero de pedido.
    # El while protege contra choques si justo existe un archivo con ese nombre.
    carpeta_tickets = obtener_carpeta_tickets()
    numero_ticket = obtener_siguiente_numero_ticket()
    while True:
        nombre_archivo = f"ticket_{numero_ticket:04d}_pedido_{pedido.pedido_id}.pdf"
        ruta_ticket = carpeta_tickets / nombre_archivo
        if not ruta_ticket.exists():
            return ruta_ticket, numero_ticket #Compara la ruta creada con las existentes, si existe le suma 1 al numero de ticket para que no se repita
        numero_ticket += 1


def _formato_moneda(valor):
    # Formatea importes con estilo local para que el PDF sea consistente con la app.
    texto = f"{float(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"$ {texto}"


def _estado_visible(estado):
    # Convierte estados internos a texto presentable en el comprobante.
    estados = {
        "pendiente": "Pendiente",
        "en preparacion": "En preparación",
        "listo": "Listo",
        "en camino": "En camino",
        "entregado": "Entregado",
        "cancelado": "Cancelado",
    }
    texto = str(estado).strip().lower()
    return estados.get(texto, str(estado).replace("_", " ").capitalize())


def _registrar_fuentes_pdf():
    # ReportLab necesita fuentes registradas para mostrar bien caracteres latinos.
    # Se intenta usar Arial en Windows o DejaVu en Linux; si no existen, usa Helvetica.
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        return "Helvetica", "Helvetica-Bold"

    fuentes = ((Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),(Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),)

    for fuente_regular, fuente_negrita in fuentes:
        if not fuente_regular.exists():
            continue

        if not fuente_negrita.exists():
            fuente_negrita = fuente_regular

        try:
            if "PizzeriaRegular" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("PizzeriaRegular", str(fuente_regular)))
            if "PizzeriaBold" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("PizzeriaBold", str(fuente_negrita)))
            return "PizzeriaRegular", "PizzeriaBold"
        except Exception:
            continue

    return "Helvetica", "Helvetica-Bold"


@registrar_log
@medir_tiempo
def generar_ticket_pdf(pedido):
    # Arma un comprobante PDF completo: encabezado, datos del pedido, productos,
    # promociones aplicadas y total final. Los decoradores registran log y tiempo.
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as error:
        raise RuntimeError("Para generar tickets PDF instala la dependencia 'reportlab'.") from error

    destino, numero_ticket = obtener_ruta_ticket(pedido)
    fuente_regular, fuente_negrita = _registrar_fuentes_pdf()
    estilos = getSampleStyleSheet()
    estilos["Title"].fontName = fuente_negrita
    estilos["Heading3"].fontName = fuente_negrita
    estilos["BodyText"].fontName = fuente_regular
    documento = SimpleDocTemplate(
        str(destino),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Ticket {numero_ticket:04d} pedido {pedido.pedido_id}",)

    elementos = []
    # Encabezado principal del ticket.
    titulo = Paragraph("<b>PizzerIA</b>", estilos["Title"])
    subtitulo = Paragraph("Comprobante de pedido", estilos["Heading3"])
    elementos.extend([titulo, subtitulo, Spacer(1, 8)])

    fecha = pedido.fecha.strftime("%d/%m/%Y %H:%M")
    # Bloque de datos generales del pedido para identificar cliente, entrega y estado.
    datos_pedido = [
        ["Ticket", f"#{numero_ticket:04d}", "Pedido", f"#{pedido.pedido_id}"],
        ["Fecha", fecha, "Estado", _estado_visible(pedido.estado)],
        ["Cliente", pedido.cliente, "Entrega", pedido.tipo_entrega],
        ["Dirección", pedido.direccion or "-", "", ""],]
    
    tabla_datos = Table(datos_pedido, colWidths=[30 * mm, 58 * mm, 30 * mm, 58 * mm])
    tabla_datos.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF7ED")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1F2937")),
                ("FONTNAME", (0, 0), (-1, -1), fuente_regular),
                ("FONTNAME", (0, 0), (0, -1), fuente_negrita),
                ("FONTNAME", (2, 0), (2, -1), fuente_negrita),
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
    # Detalle producto por producto, ya con promociones distribuidas por linea.
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
                ("FONTNAME", (0, 0), (-1, 0), fuente_negrita),
                ("FONTNAME", (0, 1), (-1, -1), fuente_regular),
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
        # Si hubo descuentos, se agregan como texto aparte para que el cliente vea
        # que promocion se aplico y cuanto ahorro.
        for promocion in promociones:
            texto = (
                f"{promocion['nombre']}: {promocion['descripcion']} "
                f"({_formato_moneda(promocion['descuento'])})"
            )
            elementos.append(Paragraph(texto, estilos["BodyText"]))
        elementos.append(Spacer(1, 8))

    resumen = [
        # Resumen final usado como cierre del comprobante.
        ["Subtotal", _formato_moneda(pedido.calcular_subtotal())],
        ["Descuento", _formato_moneda(pedido.calcular_descuento_total())],
        ["Total", _formato_moneda(pedido.calcular_total())],
    ]
    tabla_totales = Table(resumen, colWidths=[132 * mm, 46 * mm], hAlign="RIGHT")
    tabla_totales.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), fuente_negrita),
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
