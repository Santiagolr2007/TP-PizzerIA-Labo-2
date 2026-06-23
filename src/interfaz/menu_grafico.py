import threading
import tkinter as tk
from tkinter import messagebox, ttk

from src.modelos.producto import Bebida, Empanada, Pizza
from src.servicios.cocina_threads import (
    calcular_tiempo_estimado,
    determinar_estaciones_pedido,
    procesar_pedidos_con_hilos,
)
from src.servicios.inicializacion import crear_sistema
from src.servicios.persistencia import cargar_respaldo_pizzeria, guardar_json
from src.servicios.reportes_excel import (generar_reporte_stock,generar_reporte_ventas,leer_reporte_excel,)
from src.utils.excepciones import PizzeriaError


def formato_moneda(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        numero = 0
    texto = f"{numero:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"${texto}"


def formato_numero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return str(valor)

    if numero.is_integer():
        return str(int(numero))

    return f"{numero:.2f}"


def leer_importe(texto):
    valor = str(texto).strip().replace("$", "").replace(" ", "")
    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")
    return float(valor)


def estado_visible(estado):
    return str(estado).replace("_", " ").capitalize()


def obtener_resumen_productos(pedido):
    productos_agrupados = {}

    for producto, cantidad in pedido.productos:
        if producto.nombre not in productos_agrupados:
            productos_agrupados[producto.nombre] = {"cantidad": 0, "subtotal": 0}

        productos_agrupados[producto.nombre]["cantidad"] += cantidad
        productos_agrupados[producto.nombre]["subtotal"] += producto.calcular_precio() * cantidad

    textos = []
    for nombre_producto, datos in productos_agrupados.items():
        textos.append(f"{nombre_producto} x{datos['cantidad']} ({formato_moneda(datos['subtotal'])})")

    return ", ".join(textos)


class PizzeriaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.colors = {
            "bg": "#FFF7ED",
            "bg_soft": "#FFEDD5",
            "surface": "#FFFFFF",
            "surface_soft": "#FFF7ED",
            "sidebar": "#2A120A",
            "sidebar_soft": "#3B1D10",
            "sidebar_hover": "#52250F",
            "text": "#1F2937",
            "muted": "#6B7280",
            "line": "#FED7AA",
            "shadow": "#E7C7A5",
            "accent": "#F97316",
            "accent_dark": "#C2410C",
            "accent_soft": "#FDBA74",
            "success": "#059669",
            "danger": "#DC2626",
            "info": "#2563EB",
            "warning": "#D97706",
        }
        self.current_view = "panel"
        self.nav_buttons = {}
        self.busy = False
        self.cocina_eventos = []
        self.cocina_tabla = None

        self.title("PizzerIA - Gestion de pizzeria")
        self.geometry("1180x720")
        self.minsize(1020, 640)
        self.configure(bg=self.colors["bg"])

        self.pizzeria = crear_sistema()
        self.page_title = tk.StringVar(value="Panel")
        self.page_subtitle = tk.StringVar(value="Resumen general del negocio")
        self.money_text = tk.StringVar()
        self.status_text = tk.StringVar(value="Sistema iniciado correctamente.")

        self._configurar_estilos()
        self._crear_layout()
        self.mostrar_panel()
        self.protocol("WM_DELETE_WINDOW", self._cerrar_aplicacion)

    def _configurar_estilos(self):
        estilo = ttk.Style(self)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass

        estilo.configure(
            "Treeview",
            background=self.colors["surface"],
            foreground=self.colors["text"],
            fieldbackground=self.colors["surface"],
            borderwidth=0,
            rowheight=32,
            font=("Segoe UI", 10),
        )
        estilo.configure(
            "Treeview.Heading",
            background="#FFF7ED",
            foreground=self.colors["text"],
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
            padding=(8, 8),
        )
        estilo.map(
            "Treeview",
            background=[("selected", self.colors["accent"])],
            foreground=[("selected", "#FFFFFF")],
        )
        estilo.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        estilo.configure(
            "TNotebook.Tab",
            padding=(16, 10),
            font=("Segoe UI", 10, "bold"),
        )
        estilo.configure("TCombobox", padding=8)
        estilo.configure("TEntry", padding=8)
        estilo.configure("TSpinbox", padding=8)

    def _crear_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(self, bg=self.colors["sidebar"], width=240)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        marca = tk.Frame(self.sidebar, bg=self.colors["sidebar"])
        marca.pack(fill="x", padx=22, pady=(24, 18))
        tk.Label(
            marca,
            text="PizzerIA",
            bg=self.colors["sidebar"],
            fg="#FFFFFF",
            font=("Segoe UI", 22, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            marca,
            text="Gestion operativa",
            bg=self.colors["sidebar"],
            fg="#CBD5E1",
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        navegacion = [
            ("panel", "Panel", self.mostrar_panel),
            ("catalogo", "Catalogo", self.mostrar_catalogo),
            ("pedidos", "Pedidos", self.mostrar_pedidos),
            ("cocina", "Cocina", self.mostrar_cocina),
            ("stock", "Stock", self.mostrar_stock),
            ("reportes", "Reportes", self.mostrar_reportes),
            ("herramientas", "Herramientas", self.mostrar_herramientas),
        ]

        for clave, texto, comando in navegacion:
            boton = tk.Button(
                self.sidebar,
                text=texto,
                command=comando,
                anchor="w",
                bd=0,
                padx=18,
                pady=13,
                fg="#D1D5DB",
                bg=self.colors["sidebar"],
                activeforeground="#FFFFFF",
                activebackground=self.colors["sidebar_soft"],
                font=("Segoe UI", 11, "bold"),
                cursor="hand2",
            )
            boton.pack(fill="x", padx=14, pady=3)
            self.nav_buttons[clave] = boton

        separador = tk.Frame(self.sidebar, height=1, bg="#374151")
        separador.pack(fill="x", padx=22, pady=18)
        self._crear_boton_sidebar("Guardar respaldo", self.guardar_respaldo)
        self._crear_boton_sidebar("Cargar respaldo", self.cargar_respaldo)

        self.main = tk.Frame(self, bg=self.colors["bg"])
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        barra = tk.Frame(self.main, bg=self.colors["bg"])
        barra.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 12))
        barra.grid_columnconfigure(0, weight=1)

        tk.Label(
            barra,
            textvariable=self.page_title,
            bg=self.colors["bg"],
            fg=self.colors["text"],
            font=("Segoe UI", 22, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            barra,
            textvariable=self.page_subtitle,
            bg=self.colors["bg"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        caja = tk.Frame(barra, bg=self.colors["surface"], highlightthickness=1, highlightbackground=self.colors["line"])
        caja.grid(row=0, column=1, rowspan=2, sticky="e", padx=(12, 0))
        tk.Label(
            caja,
            text="Caja disponible",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="e", padx=18, pady=(9, 0))
        tk.Label(
            caja,
            textvariable=self.money_text,
            bg=self.colors["surface"],
            fg=self.colors["success"],
            font=("Segoe UI", 15, "bold"),
        ).pack(anchor="e", padx=18, pady=(0, 9))

        self.content = tk.Frame(self.main, bg=self.colors["bg"])
        self.content.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 14))
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        estado = tk.Label(
            self.main,
            textvariable=self.status_text,
            bg=self.colors["bg"],
            fg=self.colors["muted"],
            anchor="w",
            font=("Segoe UI", 9),
        )
        estado.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 10))

    def _crear_boton_sidebar(self, texto, comando):
        boton = tk.Button(
            self.sidebar,
            text=texto,
            command=comando,
            anchor="w",
            bd=0,
            padx=18,
            pady=10,
            fg="#D1D5DB",
            bg=self.colors["sidebar"],
            activeforeground="#FFFFFF",
            activebackground=self.colors["sidebar_soft"],
            font=("Segoe UI", 10),
            cursor="hand2",
        )
        boton.pack(fill="x", padx=14, pady=2)
        return boton

    def _seleccionar_nav(self, clave):
        for clave_boton, boton in self.nav_buttons.items():
            activo = clave_boton == clave
            boton.configure(
                bg=self.colors["accent"] if activo else self.colors["sidebar"],
                fg="#FFFFFF" if activo else "#D1D5DB",
            )

    def _limpiar_contenido(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def _refrescar_caja(self):
        self.money_text.set(formato_moneda(self.pizzeria.obtener_dinero()))

    def _set_status(self, texto):
        self.status_text.set(texto)

    def _boton_accion(self, parent, texto, comando, variante="principal"):
        colores = {
            "principal": (self.colors["accent"], "#FFFFFF", self.colors["accent_dark"]),
            "secundario": (self.colors["surface"], self.colors["text"], "#F9FAFB"),
            "exito": (self.colors["success"], "#FFFFFF", "#047857"),
            "peligro": (self.colors["danger"], "#FFFFFF", "#B91C1C"),
            "info": (self.colors["info"], "#FFFFFF", "#1D4ED8"),
        }
        bg, fg, active = colores[variante]
        return tk.Button(
            parent,
            text=texto,
            command=comando,
            bd=0,
            padx=16,
            pady=10,
            bg=bg,
            fg=fg,
            activebackground=active,
            activeforeground=fg,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            highlightthickness=1 if variante == "secundario" else 0,
            highlightbackground=self.colors["line"],
        )

    def _crear_seccion(self, parent, titulo, subtitulo=None):
        marco = tk.Frame(
            parent,
            bg=self.colors["surface"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
        )
        encabezado = tk.Frame(marco, bg=self.colors["surface"])
        encabezado.pack(fill="x", padx=16, pady=(14, 8))
        tk.Label(
            encabezado,
            text=titulo,
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        ).pack(fill="x")
        if subtitulo:
            tk.Label(
                encabezado,
                text=subtitulo,
                bg=self.colors["surface"],
                fg=self.colors["muted"],
                font=("Segoe UI", 9),
                anchor="w",
            ).pack(fill="x", pady=(2, 0))
        cuerpo = tk.Frame(marco, bg=self.colors["surface"])
        cuerpo.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        return marco, cuerpo

    def _crear_tabla(self, parent, columnas, encabezados, anchos=None, alto=12):
        contenedor = tk.Frame(parent, bg=self.colors["surface"])
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(0, weight=1)
        tabla = ttk.Treeview(contenedor, columns=columnas, show="headings", height=alto)
        scroll_y = ttk.Scrollbar(contenedor, orient="vertical", command=tabla.yview)
        scroll_x = ttk.Scrollbar(contenedor, orient="horizontal", command=tabla.xview)
        tabla.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        for columna in columnas:
            tabla.heading(columna, text=encabezados.get(columna, columna))
            tabla.column(
                columna,
                width=(anchos or {}).get(columna, 130),
                minwidth=80,
                anchor="w",
                stretch=True,
            )

        tabla.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        return contenedor, tabla

    def _llenar_tabla(self, tabla, columnas, filas, tag_fn=None):
        for item in tabla.get_children():
            tabla.delete(item)

        for fila in filas:
            valores = [fila.get(columna, "") for columna in columnas]
            tags = ()
            if tag_fn:
                tag = tag_fn(fila)
                tags = (tag,) if tag else ()
            tabla.insert("", "end", values=valores, tags=tags)

    def _resumen_estados(self):
        resumen = {
            "pendiente": 0,
            "en preparacion": 0,
            "listo": 0,
            "en camino": 0,
            "entregado": 0,
            "cancelado": 0,
        }
        for pedido in self.pizzeria.obtener_pedidos():
            if pedido.estado in resumen:
                resumen[pedido.estado] += 1
        return resumen

    def _detalle_producto(self, producto):
        if isinstance(producto, Pizza):
            extras = []
            for ingrediente, cantidad in producto.ingredientes_extra.items():
                extras.append(f"{ingrediente} x{cantidad}")
            detalle = f"Tamanio {producto.tamanio}"
            if extras:
                detalle += " | " + ", ".join(extras)
            return detalle

        if isinstance(producto, Empanada):
            return f"Relleno: {producto.ingrediente_relleno}"

        if isinstance(producto, Bebida):
            return f"Stock asociado: {producto.ingrediente_stock or 'sin control'}"

        return ""

    def _filas_catalogo(self, filtro=""):
        filtro = filtro.lower().strip()
        filas = []
        for numero, producto in enumerate(self.pizzeria.obtener_catalogo(), start=1):
            fila = {
                "numero": numero,
                "producto": producto.nombre,
                "categoria": producto.__class__.__name__,
                "detalle": self._detalle_producto(producto),
                "precio": formato_moneda(producto.calcular_precio()),
            }
            texto_busqueda = f"{fila['producto']} {fila['categoria']} {fila['detalle']}".lower()
            if filtro and filtro not in texto_busqueda:
                continue
            filas.append(fila)
        return filas

    def _filas_pedidos(self):
        filas = []
        for pedido in self.pizzeria.obtener_pedidos():
            filas.append(
                {
                    "pedido_id": pedido.pedido_id,
                    "cliente": pedido.cliente,
                    "entrega": pedido.tipo_entrega,
                    "direccion": pedido.direccion or "-",
                    "estado": estado_visible(pedido.estado),
                    "productos": obtener_resumen_productos(pedido),
                    "total": formato_moneda(pedido.calcular_total()),
                }
            )
        return filas

    def _tiempo_pedido_visible(self, pedido):
        if pedido.estado == "en preparacion":
            return f"{pedido.tiempo_restante or pedido.tiempo_estimado} min"

        if pedido.estado == "pendiente":
            return f"{calcular_tiempo_estimado(pedido)} min est."

        if pedido.estado == "listo":
            return "Listo"

        return "-"

    def _filas_cocina(self):
        filas = []
        estados_cocina = {"pendiente", "en preparacion", "listo", "en camino"}

        for pedido in self.pizzeria.obtener_pedidos():
            if pedido.estado not in estados_cocina:
                continue

            filas.append(
                {
                    "pedido_id": pedido.pedido_id,
                    "cliente": pedido.cliente,
                    "estado": estado_visible(pedido.estado),
                    "estacion": pedido.estacion_cocina or determinar_estaciones_pedido(pedido),
                    "cocinero": pedido.cocinero_asignado or "-",
                    "tiempo": self._tiempo_pedido_visible(pedido),
                    "entrega": pedido.tipo_entrega,
                }
            )

        return filas

    def _filas_estaciones(self):
        resumen = {}

        for pedido in self.pizzeria.obtener_pedidos():
            if pedido.estado in {"entregado", "cancelado"}:
                continue

            estacion = pedido.estacion_cocina or determinar_estaciones_pedido(pedido)
            if estacion not in resumen:
                resumen[estacion] = {"estacion": estacion, "pendientes": 0, "en_preparacion": 0, "listos": 0}

            if pedido.estado == "pendiente":
                resumen[estacion]["pendientes"] += 1
            elif pedido.estado == "en preparacion":
                resumen[estacion]["en_preparacion"] += 1
            elif pedido.estado == "listo":
                resumen[estacion]["listos"] += 1

        return list(resumen.values())

    def _filas_eventos_cocina(self):
        filas = []
        for evento in self.cocina_eventos[:10]:
            filas.append(
                {
                    "pedido_id": evento.get("pedido_id", "-"),
                    "evento": estado_visible(evento.get("tipo", "")),
                    "cocinero": evento.get("cocinero", "-"),
                    "estacion": evento.get("estacion", "-"),
                    "tiempo": f"{evento.get('tiempo_restante', 0)} min",
                    "mensaje": evento.get("mensaje", ""),
                }
            )
        return filas

    def _filas_stock(self):
        filas = []
        for fila in self.pizzeria.inventario.obtener_stock_detallado():
            cantidad = fila["cantidad"]
            filas.append(
                {
                    "ingrediente": fila["ingrediente"],
                    "cantidad": formato_numero(cantidad),
                    "precio_unitario": formato_moneda(fila["precio_unitario"]),
                    "valor_total_stock": formato_moneda(fila["valor_total_stock"]),
                    "estado": "Reponer" if cantidad <= 5 else "Disponible",
                }
            )
        filas.sort(key=lambda fila: fila["ingrediente"])
        return filas

    def _total_ventas(self):
        total = 0
        for venta in self.pizzeria.obtener_ventas():
            try:
                total += float(venta.get("subtotal", 0))
            except (TypeError, ValueError):
                pass
        return total

    def _stock_bajo(self):
        cantidad = 0
        for fila in self.pizzeria.inventario.obtener_stock_detallado():
            if fila["cantidad"] <= 5:
                cantidad += 1
        return cantidad

    def mostrar_panel(self):
        self.current_view = "panel"
        self._seleccionar_nav("panel")
        self.page_title.set("Panel")
        self.page_subtitle.set("Resumen operativo y cocina en vivo")
        self._limpiar_contenido()
        self._refrescar_caja()

        contenedor = tk.Frame(self.content, bg=self.colors["bg"])
        contenedor.pack(fill="both", expand=True)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(2, weight=1)

        acciones = tk.Frame(contenedor, bg=self.colors["bg"])
        acciones.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        for texto, comando, variante in [
            ("Nuevo pedido", self.abrir_dialogo_pedido, "principal"),
            ("Procesar cocina", self.procesar_cocina, "info"),
            ("Ver cocina", self.mostrar_cocina, "secundario"),
            ("Nuevo producto", lambda: self.abrir_dialogo_producto(), "secundario"),
            ("Reponer stock", self.abrir_dialogo_reponer_stock, "exito"),
            ("Generar reportes", self.generar_reportes, "secundario"),
        ]:
            self._boton_accion(acciones, texto, comando, variante).pack(side="left", padx=(0, 10))

        metricas = tk.Frame(contenedor, bg=self.colors["bg"])
        metricas.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        for columna in range(6):
            metricas.grid_columnconfigure(columna, weight=1, uniform="metricas")

        pedidos = self.pizzeria.obtener_pedidos()
        estados = self._resumen_estados()
        datos_metricas = [
            ("Pedidos", len(pedidos), "Total cargado", self.colors["info"]),
            ("Pendientes", estados["pendiente"], "Para cocina", self.colors["accent"]),
            ("Preparacion", estados["en preparacion"], "Trabajando ahora", self.colors["info"]),
            ("Listos", estados["listo"], "Para entregar", self.colors["success"]),
            ("Delivery", estados["en camino"], "En camino", self.colors["warning"]),
            ("Stock bajo", self._stock_bajo(), "Ingredientes criticos", self.colors["danger"]),
        ]

        for columna, (titulo, valor, detalle, color) in enumerate(datos_metricas):
            tarjeta = self._tarjeta_metrica(metricas, titulo, valor, detalle, color)
            tarjeta.grid(row=0, column=columna, sticky="nsew", padx=(0 if columna == 0 else 8, 0))

        cuerpo = tk.Frame(contenedor, bg=self.colors["bg"])
        cuerpo.grid(row=2, column=0, sticky="nsew")
        cuerpo.grid_columnconfigure(0, weight=2)
        cuerpo.grid_columnconfigure(1, weight=1)
        cuerpo.grid_rowconfigure(0, weight=1)
        cuerpo.grid_rowconfigure(1, weight=1)

        seccion_cocina, body_cocina = self._crear_seccion(cuerpo, "Cocina en vivo", "Cocineros, estaciones y tiempo estimado")
        seccion_cocina.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        columnas_cocina = ("pedido_id", "cliente", "estado", "estacion", "cocinero", "tiempo", "entrega")
        frame_cocina, tabla_cocina = self._crear_tabla(
            body_cocina,
            columnas_cocina,
            {
                "pedido_id": "ID",
                "cliente": "Cliente",
                "estado": "Estado",
                "estacion": "Estacion",
                "cocinero": "Cocinero",
                "tiempo": "Tiempo",
                "entrega": "Entrega",
            },
            {"pedido_id": 55, "cliente": 130, "estado": 120, "estacion": 160, "cocinero": 120, "tiempo": 95, "entrega": 90},
            alto=7,
        )
        frame_cocina.pack(fill="both", expand=True)
        self._configurar_tags_pedidos(tabla_cocina)
        self._llenar_tabla(tabla_cocina, columnas_cocina, self._filas_cocina(), self._tag_pedido)

        seccion_estaciones, body_estaciones = self._crear_seccion(cuerpo, "Estaciones", "Carga actual por sector")
        seccion_estaciones.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=(0, 10))
        columnas_estaciones = ("estacion", "pendientes", "en_preparacion", "listos")
        frame_estaciones, tabla_estaciones = self._crear_tabla(
            body_estaciones,
            columnas_estaciones,
            {"estacion": "Estacion", "pendientes": "Pend.", "en_preparacion": "Prep.", "listos": "Listos"},
            {"estacion": 170, "pendientes": 70, "en_preparacion": 70, "listos": 70},
            alto=7,
        )
        frame_estaciones.pack(fill="both", expand=True)
        self._llenar_tabla(tabla_estaciones, columnas_estaciones, self._filas_estaciones())

        seccion_pedidos, body_pedidos = self._crear_seccion(cuerpo, "Pedidos recientes", "Ultimos movimientos del mostrador")
        seccion_pedidos.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(10, 0))
        columnas_pedidos = ("pedido_id", "cliente", "entrega", "estado", "total")
        frame_tabla, tabla = self._crear_tabla(
            body_pedidos,
            columnas_pedidos,
            {"pedido_id": "ID", "cliente": "Cliente", "entrega": "Entrega", "estado": "Estado", "total": "Total"},
            {"pedido_id": 70, "cliente": 150, "entrega": 100, "estado": 120, "total": 120},
            alto=9,
        )
        frame_tabla.pack(fill="both", expand=True)
        self._configurar_tags_pedidos(tabla)
        self._llenar_tabla(tabla, columnas_pedidos, self._filas_pedidos()[-12:], self._tag_pedido)
        tabla.bind("<Double-1>", lambda _evento: self._abrir_ticket_desde_tabla(tabla))

        seccion_stock, body_stock = self._crear_seccion(cuerpo, "Stock critico", "Ingredientes con poca disponibilidad")
        seccion_stock.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(10, 0))
        columnas_stock = ("ingrediente", "cantidad", "estado")
        frame_stock, tabla_stock = self._crear_tabla(
            body_stock,
            columnas_stock,
            {"ingrediente": "Ingrediente", "cantidad": "Stock", "estado": "Estado"},
            {"ingrediente": 150, "cantidad": 80, "estado": 100},
            alto=9,
        )
        frame_stock.pack(fill="both", expand=True)
        tabla_stock.tag_configure("bajo", foreground=self.colors["danger"])
        filas_stock = [fila for fila in self._filas_stock() if fila["estado"] == "Reponer"]
        self._llenar_tabla(tabla_stock, columnas_stock, filas_stock, lambda _fila: "bajo")

    def _tarjeta_metrica(self, parent, titulo, valor, detalle, color):
        marco = tk.Frame(
            parent,
            bg=self.colors["surface"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
        )
        tk.Frame(marco, bg=color, height=4).pack(fill="x")
        tk.Label(
            marco,
            text=titulo,
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(
            marco,
            text=str(valor),
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Segoe UI", 21, "bold"),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(2, 0))
        tk.Label(
            marco,
            text=detalle,
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 14))
        return marco

    def mostrar_catalogo(self):
        self.current_view = "catalogo"
        self._seleccionar_nav("catalogo")
        self.page_title.set("Catalogo")
        self.page_subtitle.set("Productos disponibles para vender")
        self._limpiar_contenido()
        self._refrescar_caja()

        seccion, cuerpo = self._crear_seccion(self.content, "Productos", "Busca por nombre o categoria")
        seccion.pack(fill="both", expand=True)

        barra = tk.Frame(cuerpo, bg=self.colors["surface"])
        barra.pack(fill="x", pady=(0, 12))
        busqueda = tk.StringVar()
        entrada = ttk.Entry(barra, textvariable=busqueda)
        entrada.pack(side="left", fill="x", expand=True)
        self._boton_accion(barra, "Nuevo producto", lambda: self.abrir_dialogo_producto(), "principal").pack(side="left", padx=(10, 0))
        self._boton_accion(barra, "Editar", lambda: self.editar_producto_desde_tabla(tabla), "secundario").pack(side="left", padx=(10, 0))
        self._boton_accion(barra, "Eliminar", lambda: self.eliminar_producto_desde_tabla(tabla), "peligro").pack(side="left", padx=(10, 0))
        self._boton_accion(barra, "Nuevo pedido", self.abrir_dialogo_pedido, "info").pack(side="left", padx=(10, 0))

        columnas = ("numero", "producto", "categoria", "detalle", "precio")
        frame_tabla, tabla = self._crear_tabla(
            cuerpo,
            columnas,
            {"numero": "#", "producto": "Producto", "categoria": "Categoria", "detalle": "Detalle", "precio": "Precio"},
            {"numero": 60, "producto": 240, "categoria": 130, "detalle": 280, "precio": 120},
            alto=16,
        )
        frame_tabla.pack(fill="both", expand=True)
        tabla.bind("<Double-1>", lambda _evento: self.editar_producto_desde_tabla(tabla))

        def renderizar(_evento=None):
            self._llenar_tabla(tabla, columnas, self._filas_catalogo(busqueda.get()))

        entrada.bind("<KeyRelease>", renderizar)
        renderizar()

    def _producto_desde_tabla_catalogo(self, tabla):
        seleccion = tabla.selection()
        if not seleccion:
            messagebox.showwarning("Producto requerido", "Selecciona un producto del catalogo.")
            return None

        valores = tabla.item(seleccion[0], "values")
        if len(valores) < 2:
            return None

        try:
            return self.pizzeria.obtener_producto(valores[1])
        except (PizzeriaError, ValueError) as error:
            messagebox.showerror("Producto", str(error))
            return None

    def editar_producto_desde_tabla(self, tabla):
        producto = self._producto_desde_tabla_catalogo(tabla)
        if producto is not None:
            self.abrir_dialogo_producto(producto)

    def eliminar_producto_desde_tabla(self, tabla):
        producto = self._producto_desde_tabla_catalogo(tabla)
        if producto is None:
            return

        if not messagebox.askyesno("Eliminar producto", f"Eliminar '{producto.nombre}' del catalogo?"):
            return

        try:
            self.pizzeria.eliminar_producto(producto.nombre)
        except (PizzeriaError, ValueError) as error:
            messagebox.showerror("No se pudo eliminar", str(error))
            return

        self._set_status(f"Producto eliminado: {producto.nombre}.")
        self.mostrar_catalogo()

    def abrir_dialogo_producto(self, producto=None):
        ventana = tk.Toplevel(self)
        ventana.title("Editar producto" if producto else "Nuevo producto")
        ventana.geometry("560x560")
        ventana.minsize(520, 520)
        ventana.configure(bg=self.colors["bg"])
        ventana.transient(self)
        ventana.grab_set()

        categoria_inicial = producto.__class__.__name__ if producto else "Pizza"
        categoria = tk.StringVar(value=categoria_inicial)
        nombre = tk.StringVar(value=producto.nombre if producto else "")
        precio = tk.StringVar(value=str(producto.precio_base) if producto else "")
        tamanio = tk.StringVar(value=getattr(producto, "tamanio", "grande"))
        extras = tk.StringVar()
        relleno = tk.StringVar(value=getattr(producto, "ingrediente_relleno", ""))
        ingrediente_bebida = tk.StringVar(value=getattr(producto, "ingrediente_stock", "") or "")
        nombre_original = producto.nombre if producto else None

        if isinstance(producto, Pizza):
            extras.set(", ".join(f"{ingrediente}:{cantidad}" for ingrediente, cantidad in producto.ingredientes_extra.items()))

        marco = tk.Frame(ventana, bg=self.colors["surface"], highlightthickness=1, highlightbackground=self.colors["line"])
        marco.pack(fill="both", expand=True, padx=22, pady=22)

        tk.Label(
            marco,
            text="Editar producto" if producto else "Nuevo producto",
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w", padx=18, pady=(18, 4))
        tk.Label(
            marco,
            text="Los cambios se aplican al catalogo para nuevos pedidos.",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=18, pady=(0, 14))

        formulario = tk.Frame(marco, bg=self.colors["surface"])
        formulario.pack(fill="x", padx=18)
        formulario.grid_columnconfigure(0, weight=1)

        def etiqueta(texto, fila):
            tk.Label(
                formulario,
                text=texto,
                bg=self.colors["surface"],
                fg=self.colors["muted"],
                font=("Segoe UI", 10, "bold"),
            ).grid(row=fila, column=0, sticky="w", pady=(0, 6))

        etiqueta("Categoria", 0)
        combo_categoria = ttk.Combobox(formulario, textvariable=categoria, values=("Pizza", "Empanada", "Bebida"), state="readonly")
        combo_categoria.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        etiqueta("Nombre", 2)
        ttk.Entry(formulario, textvariable=nombre).grid(row=3, column=0, sticky="ew", pady=(0, 12))

        etiqueta("Precio base", 4)
        ttk.Entry(formulario, textvariable=precio).grid(row=5, column=0, sticky="ew", pady=(0, 12))

        campos_tipo = tk.Frame(formulario, bg=self.colors["surface"])
        campos_tipo.grid(row=6, column=0, sticky="ew")
        campos_tipo.grid_columnconfigure(0, weight=1)

        frame_pizza = tk.Frame(campos_tipo, bg=self.colors["surface"])
        frame_empanada = tk.Frame(campos_tipo, bg=self.colors["surface"])
        frame_bebida = tk.Frame(campos_tipo, bg=self.colors["surface"])

        tk.Label(frame_pizza, text="Tamanio", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))
        ttk.Combobox(frame_pizza, textvariable=tamanio, values=("chica", "mediana", "grande"), state="readonly").pack(fill="x", pady=(0, 12))
        tk.Label(frame_pizza, text="Ingredientes extra", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))
        ttk.Entry(frame_pizza, textvariable=extras).pack(fill="x")
        tk.Label(frame_pizza, text="Formato: jamon:2, morron:1", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))

        tk.Label(frame_empanada, text="Ingrediente de relleno", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))
        ttk.Entry(frame_empanada, textvariable=relleno).pack(fill="x")

        tk.Label(frame_bebida, text="Ingrediente de stock asociado", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))
        ttk.Entry(frame_bebida, textvariable=ingrediente_bebida).pack(fill="x")

        def mostrar_campos_tipo(_evento=None):
            for frame in (frame_pizza, frame_empanada, frame_bebida):
                frame.pack_forget()

            if categoria.get() == "Pizza":
                frame_pizza.pack(fill="x")
            elif categoria.get() == "Empanada":
                frame_empanada.pack(fill="x")
            else:
                frame_bebida.pack(fill="x")

        def parsear_extras():
            resultado = {}
            texto = extras.get().strip()
            if not texto:
                return resultado

            for parte in texto.split(","):
                if ":" not in parte:
                    raise ValueError("Los extras deben tener formato ingrediente:cantidad.")
                ingrediente, cantidad_texto = parte.split(":", 1)
                ingrediente = ingrediente.strip().lower()
                cantidad = int(cantidad_texto.strip())
                if not ingrediente or cantidad <= 0:
                    raise ValueError("Cada ingrediente extra debe tener una cantidad mayor que cero.")
                resultado[ingrediente] = cantidad

            return resultado

        def construir_producto():
            precio_base = leer_importe(precio.get())
            tipo = categoria.get()

            if tipo == "Pizza":
                return Pizza(nombre.get(), precio_base, tamanio.get(), parsear_extras())

            if tipo == "Empanada":
                return Empanada(nombre.get(), precio_base, relleno.get())

            ingrediente = ingrediente_bebida.get().strip() or None
            return Bebida(nombre.get(), precio_base, ingrediente)

        combo_categoria.bind("<<ComboboxSelected>>", mostrar_campos_tipo)
        mostrar_campos_tipo()

        pie = tk.Frame(marco, bg=self.colors["surface"])
        pie.pack(fill="x", padx=18, pady=(18, 18))
        self._boton_accion(pie, "Cancelar", ventana.destroy, "secundario").pack(side="right", padx=(10, 0))

        def guardar():
            try:
                nuevo_producto = construir_producto()
                self.pizzeria.guardar_producto(nuevo_producto, nombre_original)
            except (PizzeriaError, ValueError) as error:
                messagebox.showerror("No se pudo guardar", str(error), parent=ventana)
                return

            ventana.destroy()
            self._set_status(f"Producto guardado: {nuevo_producto.nombre}.")
            self.mostrar_catalogo()

        self._boton_accion(pie, "Guardar", guardar, "principal").pack(side="right")

    def mostrar_pedidos(self):
        self.current_view = "pedidos"
        self._seleccionar_nav("pedidos")
        self.page_title.set("Pedidos")
        self.page_subtitle.set("Seguimiento de pedidos y estados")
        self._limpiar_contenido()
        self._refrescar_caja()

        seccion, cuerpo = self._crear_seccion(self.content, "Pedidos", "Seguimiento operativo de la jornada")
        seccion.pack(fill="both", expand=True)

        barra = tk.Frame(cuerpo, bg=self.colors["surface"])
        barra.pack(fill="x", pady=(0, 12))
        self._boton_accion(barra, "Nuevo pedido", self.abrir_dialogo_pedido, "principal").pack(side="left", padx=(0, 10))
        self._boton_accion(barra, "Procesar cocina", self.procesar_cocina, "info").pack(side="left", padx=(0, 10))
        self._boton_accion(barra, "Avanzar estado", lambda: self.avanzar_pedido_desde_tabla(tabla), "exito").pack(side="left", padx=(0, 10))
        self._boton_accion(barra, "Cancelar pedido", lambda: self.cancelar_pedido_desde_tabla(tabla), "peligro").pack(side="left", padx=(0, 10))
        self._boton_accion(barra, "Actualizar", self.mostrar_pedidos, "secundario").pack(side="left")

        columnas = ("pedido_id", "cliente", "entrega", "direccion", "estado", "productos", "total")
        frame_tabla, tabla = self._crear_tabla(
            cuerpo,
            columnas,
            {
                "pedido_id": "ID",
                "cliente": "Cliente",
                "entrega": "Entrega",
                "direccion": "Direccion",
                "estado": "Estado",
                "productos": "Productos",
                "total": "Total",
            },
            {"pedido_id": 70, "cliente": 140, "entrega": 95, "direccion": 180, "estado": 120, "productos": 330, "total": 120},
            alto=16,
        )
        frame_tabla.pack(fill="both", expand=True)
        self._configurar_tags_pedidos(tabla)
        self._llenar_tabla(tabla, columnas, self._filas_pedidos(), self._tag_pedido)
        tabla.bind("<Double-1>", lambda _evento: self._abrir_ticket_desde_tabla(tabla))

    def _configurar_tags_pedidos(self, tabla):
        tabla.tag_configure("pendiente", foreground=self.colors["accent"])
        tabla.tag_configure("en preparacion", foreground=self.colors["info"])
        tabla.tag_configure("listo", foreground=self.colors["success"])
        tabla.tag_configure("en camino", foreground=self.colors["warning"])
        tabla.tag_configure("entregado", foreground=self.colors["success"])
        tabla.tag_configure("cancelado", foreground=self.colors["danger"])

    def _tag_pedido(self, fila):
        estado = str(fila.get("estado", "")).lower()
        if estado in {"pendiente", "en preparacion", "listo", "en camino", "entregado", "cancelado"}:
            return estado
        return ""

    def mostrar_cocina(self):
        self.current_view = "cocina"
        self._seleccionar_nav("cocina")
        self.page_title.set("Cocina")
        self.page_subtitle.set("Cocineros, estaciones, tiempos estimados y cola activa")
        self._limpiar_contenido()
        self._refrescar_caja()

        contenedor = tk.Frame(self.content, bg=self.colors["bg"])
        contenedor.pack(fill="both", expand=True)
        contenedor.grid_columnconfigure(0, weight=2)
        contenedor.grid_columnconfigure(1, weight=1)
        contenedor.grid_rowconfigure(1, weight=1)

        acciones = tk.Frame(contenedor, bg=self.colors["bg"])
        acciones.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self._boton_accion(acciones, "Procesar pendientes", self.procesar_cocina, "principal").pack(side="left", padx=(0, 10))
        self._boton_accion(acciones, "Nuevo pedido", self.abrir_dialogo_pedido, "secundario").pack(side="left", padx=(0, 10))
        self._boton_accion(acciones, "Actualizar", self.mostrar_cocina, "secundario").pack(side="left")

        seccion_cola, body_cola = self._crear_seccion(contenedor, "Cola de cocina", "Pedidos pendientes, en preparacion y listos")
        seccion_cola.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        columnas_cola = ("pedido_id", "cliente", "estado", "estacion", "cocinero", "tiempo", "entrega")
        frame_cola, tabla_cola = self._crear_tabla(
            body_cola,
            columnas_cola,
            {
                "pedido_id": "ID",
                "cliente": "Cliente",
                "estado": "Estado",
                "estacion": "Estacion",
                "cocinero": "Cocinero",
                "tiempo": "Tiempo",
                "entrega": "Entrega",
            },
            {"pedido_id": 60, "cliente": 140, "estado": 120, "estacion": 170, "cocinero": 130, "tiempo": 100, "entrega": 100},
            alto=15,
        )
        frame_cola.pack(fill="both", expand=True)
        self._configurar_tags_pedidos(tabla_cola)
        self._llenar_tabla(tabla_cola, columnas_cola, self._filas_cocina(), self._tag_pedido)
        tabla_cola.bind("<Double-1>", lambda _evento: self._abrir_ticket_desde_tabla(tabla_cola))

        lateral = tk.Frame(contenedor, bg=self.colors["bg"])
        lateral.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        lateral.grid_columnconfigure(0, weight=1)
        lateral.grid_rowconfigure(0, weight=1)
        lateral.grid_rowconfigure(1, weight=1)

        seccion_estaciones, body_estaciones = self._crear_seccion(lateral, "Estaciones", "Carga por sector")
        seccion_estaciones.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        columnas_estaciones = ("estacion", "pendientes", "en_preparacion", "listos")
        frame_estaciones, tabla_estaciones = self._crear_tabla(
            body_estaciones,
            columnas_estaciones,
            {"estacion": "Estacion", "pendientes": "Pend.", "en_preparacion": "Prep.", "listos": "Listos"},
            {"estacion": 170, "pendientes": 70, "en_preparacion": 70, "listos": 70},
            alto=6,
        )
        frame_estaciones.pack(fill="both", expand=True)
        self._llenar_tabla(tabla_estaciones, columnas_estaciones, self._filas_estaciones())

        seccion_eventos, body_eventos = self._crear_seccion(lateral, "Eventos recientes", "Actividad de hilos")
        seccion_eventos.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        columnas_eventos = ("pedido_id", "evento", "cocinero", "tiempo", "mensaje")
        frame_eventos, tabla_eventos = self._crear_tabla(
            body_eventos,
            columnas_eventos,
            {"pedido_id": "ID", "evento": "Evento", "cocinero": "Cocinero", "tiempo": "Tiempo", "mensaje": "Mensaje"},
            {"pedido_id": 55, "evento": 90, "cocinero": 110, "tiempo": 80, "mensaje": 280},
            alto=6,
        )
        frame_eventos.pack(fill="both", expand=True)
        self._llenar_tabla(tabla_eventos, columnas_eventos, self._filas_eventos_cocina())

    def mostrar_stock(self):
        self.current_view = "stock"
        self._seleccionar_nav("stock")
        self.page_title.set("Stock")
        self.page_subtitle.set("Inventario valorizado")
        self._limpiar_contenido()
        self._refrescar_caja()

        seccion, cuerpo = self._crear_seccion(self.content, "Inventario", "Ingredientes, costos y alertas de reposicion")
        seccion.pack(fill="both", expand=True)

        barra = tk.Frame(cuerpo, bg=self.colors["surface"])
        barra.pack(fill="x", pady=(0, 12))
        self._boton_accion(barra, "Reponer stock", self.abrir_dialogo_reponer_stock, "exito").pack(side="left", padx=(0, 10))
        self._boton_accion(barra, "Generar reporte", self.generar_reportes, "secundario").pack(side="left")

        columnas = ("ingrediente", "cantidad", "precio_unitario", "valor_total_stock", "estado")
        frame_tabla, tabla = self._crear_tabla(
            cuerpo,
            columnas,
            {
                "ingrediente": "Ingrediente",
                "cantidad": "Cantidad",
                "precio_unitario": "Precio unitario",
                "valor_total_stock": "Valor total",
                "estado": "Estado",
            },
            {
                "ingrediente": 180,
                "cantidad": 90,
                "precio_unitario": 140,
                "valor_total_stock": 140,
                "estado": 110,
            },
            alto=16,
        )
        frame_tabla.pack(fill="both", expand=True)
        tabla.tag_configure("bajo", foreground=self.colors["danger"])
        self._llenar_tabla(tabla, columnas, self._filas_stock(), lambda fila: "bajo" if fila["estado"] == "Reponer" else "")

    def mostrar_reportes(self):
        self.current_view = "reportes"
        self._seleccionar_nav("reportes")
        self.page_title.set("Reportes")
        self.page_subtitle.set("Exportacion y lectura de archivos Excel")
        self._limpiar_contenido()
        self._refrescar_caja()

        seccion, cuerpo = self._crear_seccion(self.content, "Reportes Excel", "Ventas y stock del negocio")
        seccion.pack(fill="both", expand=True)

        barra = tk.Frame(cuerpo, bg=self.colors["surface"])
        barra.pack(fill="x", pady=(0, 12))
        self._boton_accion(barra, "Generar reportes", self.generar_reportes, "principal").pack(side="left", padx=(0, 10))
        self._boton_accion(barra, "Actualizar vista", self.mostrar_reportes, "secundario").pack(side="left")

        notebook = ttk.Notebook(cuerpo)
        notebook.pack(fill="both", expand=True)
        self._agregar_tab_reporte(notebook, "Ventas", "reporte_ventas.xlsx")
        self._agregar_tab_reporte(notebook, "Stock", "reporte_stock.xlsx")

    def _agregar_tab_reporte(self, notebook, titulo, archivo):
        tab = tk.Frame(notebook, bg=self.colors["surface"])
        notebook.add(tab, text=titulo)
        try:
            filas = leer_reporte_excel(archivo)
        except FileNotFoundError as error:
            tk.Label(
                tab,
                text=str(error),
                bg=self.colors["surface"],
                fg=self.colors["muted"],
                font=("Segoe UI", 11),
            ).pack(padx=20, pady=20, anchor="w")
            return

        if not filas:
            tk.Label(
                tab,
                text="El reporte esta vacio.",
                bg=self.colors["surface"],
                fg=self.colors["muted"],
                font=("Segoe UI", 11),
            ).pack(padx=20, pady=20, anchor="w")
            return

        columnas = tuple(filas[0].keys())
        encabezados = {columna: columna for columna in columnas}
        frame_tabla, tabla = self._crear_tabla(tab, columnas, encabezados, alto=14)
        frame_tabla.pack(fill="both", expand=True, padx=4, pady=4)
        filas_formateadas = []
        for fila in filas:
            fila_formateada = {}
            for columna, valor in fila.items():
                columna_normalizada = columna.lower()
                if "total" in columna_normalizada or "precio" in columna_normalizada:
                    fila_formateada[columna] = formato_moneda(valor)
                else:
                    fila_formateada[columna] = valor
            filas_formateadas.append(fila_formateada)
        self._llenar_tabla(tabla, columnas, filas_formateadas)

    def mostrar_herramientas(self):
        self.current_view = "herramientas"
        self._seleccionar_nav("herramientas")
        self.page_title.set("Herramientas")
        self.page_subtitle.set("Respaldos, proveedor externo y mantenimiento")
        self._limpiar_contenido()
        self._refrescar_caja()

        contenedor = tk.Frame(self.content, bg=self.colors["bg"])
        contenedor.pack(fill="both", expand=True)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_columnconfigure(1, weight=1)

        seccion_respaldos, body_respaldos = self._crear_seccion(contenedor, "Respaldos", "Guardar y recuperar el estado del sistema")
        seccion_respaldos.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._boton_accion(body_respaldos, "Guardar respaldo", self.guardar_respaldo, "principal").pack(fill="x", pady=(0, 10))
        self._boton_accion(body_respaldos, "Cargar respaldo", self.cargar_respaldo, "secundario").pack(fill="x")

        seccion_proveedor, body_proveedor = self._crear_seccion(contenedor, "Proveedor externo", "Consulta de cotizacion")
        seccion_proveedor.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self._boton_accion(body_proveedor, "Consultar dolar oficial", self.consultar_proveedor, "info").pack(fill="x")

        seccion_estado, body_estado = self._crear_seccion(contenedor, "Estado actual", "Datos rapidos del sistema")
        seccion_estado.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(20, 0))
        estados = self._resumen_estados()
        datos = [
            ("Pedidos pendientes", estados["pendiente"]),
            ("Pedidos listos", estados["listo"]),
            ("Delivery en camino", estados["en camino"]),
            ("Pedidos entregados", estados["entregado"]),
            ("Pedidos cancelados", estados["cancelado"]),
            ("Ventas registradas", len(self.pizzeria.obtener_ventas())),
            ("Ingredientes en stock", len(self.pizzeria.inventario.obtener_stock())),
        ]
        for texto, valor in datos:
            fila = tk.Frame(body_estado, bg=self.colors["surface"])
            fila.pack(fill="x", pady=4)
            tk.Label(fila, text=texto, bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10)).pack(side="left")
            tk.Label(fila, text=str(valor), bg=self.colors["surface"], fg=self.colors["text"], font=("Segoe UI", 10, "bold")).pack(side="right")

    def abrir_dialogo_pedido(self):
        ventana = tk.Toplevel(self)
        ventana.title("Nuevo pedido")
        ventana.geometry("940x680")
        ventana.minsize(860, 620)
        ventana.configure(bg=self.colors["bg"])
        ventana.transient(self)
        ventana.grab_set()

        carrito = {}
        cliente = tk.StringVar()
        cantidad = tk.StringVar(value="1")
        tipo_entrega = tk.StringVar(value="Retiro")
        direccion = tk.StringVar()

        encabezado = tk.Frame(ventana, bg=self.colors["bg"])
        encabezado.pack(fill="x", padx=22, pady=(18, 10))
        tk.Label(
            encabezado,
            text="Nuevo pedido",
            bg=self.colors["bg"],
            fg=self.colors["text"],
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")

        datos_cliente = tk.Frame(ventana, bg=self.colors["surface"], highlightthickness=1, highlightbackground=self.colors["line"])
        datos_cliente.pack(fill="x", padx=22, pady=(0, 12))
        datos_cliente.grid_columnconfigure(1, weight=2)
        datos_cliente.grid_columnconfigure(3, weight=1)
        datos_cliente.grid_columnconfigure(5, weight=2)
        tk.Label(datos_cliente, text="Cliente", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", padx=(14, 8), pady=12)
        ttk.Entry(datos_cliente, textvariable=cliente).grid(row=0, column=1, sticky="ew", pady=12)
        tk.Label(datos_cliente, text="Entrega", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).grid(row=0, column=2, sticky="w", padx=(14, 8), pady=12)
        ttk.Combobox(datos_cliente, textvariable=tipo_entrega, values=("Retiro", "Delivery"), state="readonly", width=12).grid(row=0, column=3, sticky="ew", pady=12)
        tk.Label(datos_cliente, text="Direccion", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).grid(row=0, column=4, sticky="w", padx=(14, 8), pady=12)
        entrada_direccion = ttk.Entry(datos_cliente, textvariable=direccion)
        entrada_direccion.grid(row=0, column=5, sticky="ew", padx=(0, 14), pady=12)

        def actualizar_direccion(*_args):
            estado = "normal" if tipo_entrega.get() == "Delivery" else "disabled"
            entrada_direccion.configure(state=estado)
            if estado == "disabled":
                direccion.set("")

        tipo_entrega.trace_add("write", actualizar_direccion)
        actualizar_direccion()

        cuerpo = tk.Frame(ventana, bg=self.colors["bg"])
        cuerpo.pack(fill="both", expand=True, padx=22, pady=(0, 12))
        cuerpo.grid_columnconfigure(0, weight=3)
        cuerpo.grid_columnconfigure(1, weight=2)
        cuerpo.grid_rowconfigure(0, weight=1)

        seccion_catalogo, body_catalogo = self._crear_seccion(cuerpo, "Catalogo", "Selecciona productos y cantidades")
        seccion_catalogo.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        columnas_catalogo = ("numero", "producto", "categoria", "precio")
        frame_catalogo, tabla_catalogo = self._crear_tabla(
            body_catalogo,
            columnas_catalogo,
            {"numero": "#", "producto": "Producto", "categoria": "Categoria", "precio": "Precio"},
            {"numero": 60, "producto": 240, "categoria": 120, "precio": 110},
            alto=11,
        )
        frame_catalogo.pack(fill="both", expand=True)
        self._llenar_tabla(tabla_catalogo, columnas_catalogo, self._filas_catalogo())

        controles = tk.Frame(body_catalogo, bg=self.colors["surface"])
        controles.pack(fill="x", pady=(12, 0))
        tk.Label(controles, text="Cantidad", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Spinbox(controles, from_=1, to=99, textvariable=cantidad, width=6).pack(side="left", padx=8)
        self._boton_accion(controles, "Agregar", lambda: agregar_producto(), "principal").pack(side="left")

        seccion_carrito, body_carrito = self._crear_seccion(cuerpo, "Pedido", "Resumen antes de confirmar")
        seccion_carrito.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        columnas_carrito = ("producto", "cantidad", "subtotal")
        frame_carrito, tabla_carrito = self._crear_tabla(
            body_carrito,
            columnas_carrito,
            {"producto": "Producto", "cantidad": "Cant.", "subtotal": "Subtotal"},
            {"producto": 190, "cantidad": 70, "subtotal": 110},
            alto=11,
        )
        frame_carrito.pack(fill="both", expand=True)

        total_text = tk.StringVar(value="Total: $0.00")
        tk.Label(
            body_carrito,
            textvariable=total_text,
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Segoe UI", 15, "bold"),
            anchor="e",
        ).pack(fill="x", pady=(12, 0))

        def renderizar_carrito():
            filas = []
            total = 0
            for nombre, datos in carrito.items():
                subtotal = datos["producto"].calcular_precio() * datos["cantidad"]
                total += subtotal
                filas.append(
                    {
                        "producto": nombre,
                        "cantidad": datos["cantidad"],
                        "subtotal": formato_moneda(subtotal),
                    }
                )
            self._llenar_tabla(tabla_carrito, columnas_carrito, filas)
            total_text.set(f"Total: {formato_moneda(total)}")

        def agregar_producto():
            seleccion = tabla_catalogo.selection()
            if not seleccion:
                messagebox.showwarning("Producto requerido", "Selecciona un producto del catalogo.", parent=ventana)
                return

            try:
                cantidad_numero = int(cantidad.get())
                if cantidad_numero <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Cantidad invalida", "La cantidad debe ser un entero mayor que cero.", parent=ventana)
                return

            valores = tabla_catalogo.item(seleccion[0], "values")
            try:
                producto = self.pizzeria.obtener_producto(valores[1])
            except (PizzeriaError, ValueError) as error:
                messagebox.showerror("Producto", str(error), parent=ventana)
                return
            if producto.nombre not in carrito:
                carrito[producto.nombre] = {"producto": producto, "cantidad": 0}
            carrito[producto.nombre]["cantidad"] += cantidad_numero
            renderizar_carrito()

        def quitar_producto():
            seleccion = tabla_carrito.selection()
            if not seleccion:
                return
            nombre = tabla_carrito.item(seleccion[0], "values")[0]
            carrito.pop(nombre, None)
            renderizar_carrito()

        pie = tk.Frame(ventana, bg=self.colors["bg"])
        pie.pack(fill="x", padx=22, pady=(0, 18))
        self._boton_accion(pie, "Cancelar", ventana.destroy, "secundario").pack(side="right", padx=(10, 0))
        self._boton_accion(pie, "Quitar seleccionado", quitar_producto, "peligro").pack(side="left")

        def confirmar():
            if not carrito:
                messagebox.showwarning("Pedido vacio", "Agrega al menos un producto.", parent=ventana)
                return

            try:
                items = [[nombre, datos["cantidad"]] for nombre, datos in carrito.items()]
                pedido = self.pizzeria.crear_pedido(cliente.get(), items, tipo_entrega.get(), direccion.get())
            except (PizzeriaError, ValueError) as error:
                messagebox.showerror("No se pudo crear el pedido", str(error), parent=ventana)
                return

            ventana.destroy()
            self._set_status(f"Pedido #{pedido.pedido_id} creado correctamente.")
            self._refrescar_vista_actual()
            self._mostrar_ticket(pedido)

        self._boton_accion(pie, "Confirmar pedido", confirmar, "principal").pack(side="right")

    def abrir_dialogo_reponer_stock(self):
        stock = self.pizzeria.inventario.obtener_stock_detallado()
        ingredientes = [fila["ingrediente"] for fila in stock]
        if not ingredientes:
            messagebox.showinfo("Sin stock", "No hay ingredientes cargados.")
            return

        ventana = tk.Toplevel(self)
        ventana.title("Reponer stock")
        ventana.geometry("430x260")
        ventana.configure(bg=self.colors["bg"])
        ventana.transient(self)
        ventana.grab_set()

        ingrediente = tk.StringVar(value=ingredientes[0])
        cantidad = tk.StringVar(value="1")
        costo = tk.StringVar(value="")

        marco = tk.Frame(ventana, bg=self.colors["surface"], highlightthickness=1, highlightbackground=self.colors["line"])
        marco.pack(fill="both", expand=True, padx=22, pady=22)
        tk.Label(marco, text="Reponer stock", bg=self.colors["surface"], fg=self.colors["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=(16, 12))

        formulario = tk.Frame(marco, bg=self.colors["surface"])
        formulario.pack(fill="x", padx=16)
        tk.Label(formulario, text="Ingrediente", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        combo = ttk.Combobox(formulario, textvariable=ingrediente, values=ingredientes, state="readonly")
        combo.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        tk.Label(formulario, text="Cantidad", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 6))
        spin = ttk.Spinbox(formulario, from_=1, to=999, textvariable=cantidad)
        spin.grid(row=3, column=0, sticky="ew")
        formulario.grid_columnconfigure(0, weight=1)

        tk.Label(marco, textvariable=costo, bg=self.colors["surface"], fg=self.colors["success"], font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 0))

        def actualizar_costo(_evento=None):
            try:
                costo_total = self.pizzeria.inventario.calcular_costo_reposicion(ingrediente.get(), int(cantidad.get()))
                costo.set(f"Costo estimado: {formato_moneda(costo_total)}")
            except Exception:
                costo.set("Costo estimado: -")

        combo.bind("<<ComboboxSelected>>", actualizar_costo)
        spin.bind("<KeyRelease>", actualizar_costo)
        actualizar_costo()

        pie = tk.Frame(marco, bg=self.colors["surface"])
        pie.pack(fill="x", padx=16, pady=(14, 16))
        self._boton_accion(pie, "Cancelar", ventana.destroy, "secundario").pack(side="right", padx=(10, 0))

        def confirmar():
            try:
                costo_total = self.pizzeria.reponer_stock(ingrediente.get(), int(cantidad.get()))
            except (PizzeriaError, ValueError) as error:
                messagebox.showerror("No se pudo reponer", str(error), parent=ventana)
                return

            ventana.destroy()
            self._set_status(f"Stock actualizado. Costo: {formato_moneda(costo_total)}.")
            self._refrescar_vista_actual()

        self._boton_accion(pie, "Confirmar", confirmar, "principal").pack(side="right")

    def _mostrar_ticket(self, pedido):
        ventana = tk.Toplevel(self)
        ventana.title(f"Ticket pedido #{pedido.pedido_id}")
        ventana.geometry("460x420")
        ventana.configure(bg=self.colors["bg"])
        ventana.transient(self)

        marco = tk.Frame(ventana, bg=self.colors["surface"], highlightthickness=1, highlightbackground=self.colors["line"])
        marco.pack(fill="both", expand=True, padx=22, pady=22)
        tk.Label(marco, text=f"Pedido #{pedido.pedido_id}", bg=self.colors["surface"], fg=self.colors["text"], font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=16, pady=(16, 2))
        tk.Label(marco, text=f"Cliente: {pedido.cliente}", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10)).pack(anchor="w", padx=16)
        tk.Label(marco, text=f"Entrega: {pedido.tipo_entrega}", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10)).pack(anchor="w", padx=16)
        if pedido.direccion:
            tk.Label(marco, text=f"Direccion: {pedido.direccion}", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10)).pack(anchor="w", padx=16)
        tk.Label(marco, text=f"Estado: {estado_visible(pedido.estado)}", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10)).pack(anchor="w", padx=16, pady=(0, 12))

        columnas = ("producto", "cantidad", "subtotal")
        frame_tabla, tabla = self._crear_tabla(
            marco,
            columnas,
            {"producto": "Producto", "cantidad": "Cant.", "subtotal": "Subtotal"},
            {"producto": 220, "cantidad": 70, "subtotal": 120},
            alto=7,
        )
        frame_tabla.pack(fill="both", expand=True, padx=16)

        productos = {}
        for producto, cantidad in pedido.productos:
            productos.setdefault(producto.nombre, {"cantidad": 0, "subtotal": 0})
            productos[producto.nombre]["cantidad"] += cantidad
            productos[producto.nombre]["subtotal"] += producto.calcular_precio() * cantidad

        filas = []
        for nombre, datos in productos.items():
            filas.append({"producto": nombre, "cantidad": datos["cantidad"], "subtotal": formato_moneda(datos["subtotal"])})
        self._llenar_tabla(tabla, columnas, filas)

        tk.Label(
            marco,
            text=f"Total: {formato_moneda(pedido.calcular_total())}",
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Segoe UI", 15, "bold"),
            anchor="e",
        ).pack(fill="x", padx=16, pady=12)

    def _abrir_ticket_desde_tabla(self, tabla):
        pedido = self._pedido_desde_tabla(tabla, mostrar_error=False)
        if pedido is not None:
            self._mostrar_ticket(pedido)

    def _pedido_desde_tabla(self, tabla, mostrar_error=True):
        seleccion = tabla.selection()
        if not seleccion:
            if mostrar_error:
                messagebox.showwarning("Pedido requerido", "Selecciona un pedido.")
            return None

        valores = tabla.item(seleccion[0], "values")
        if not valores:
            return None

        try:
            return self.pizzeria.obtener_pedido_por_id(int(valores[0]))
        except (PizzeriaError, ValueError) as error:
            if mostrar_error:
                messagebox.showerror("Pedido", str(error))
            return None

    def avanzar_pedido_desde_tabla(self, tabla):
        pedido = self._pedido_desde_tabla(tabla)
        if pedido is None:
            return

        try:
            pedido = self.pizzeria.avanzar_pedido(pedido.pedido_id)
        except (PizzeriaError, ValueError) as error:
            messagebox.showerror("No se pudo avanzar", str(error))
            return

        self._set_status(f"Pedido #{pedido.pedido_id} ahora esta {estado_visible(pedido.estado)}.")
        self._refrescar_vista_actual()

    def cancelar_pedido_desde_tabla(self, tabla):
        pedido = self._pedido_desde_tabla(tabla)
        if pedido is None:
            return

        if not messagebox.askyesno("Cancelar pedido", f"Cancelar el pedido #{pedido.pedido_id}?"):
            return

        try:
            pedido = self.pizzeria.cancelar_pedido(pedido.pedido_id)
        except (PizzeriaError, ValueError) as error:
            messagebox.showerror("No se pudo cancelar", str(error))
            return

        self._set_status(f"Pedido #{pedido.pedido_id} cancelado.")
        self._refrescar_vista_actual()

    def _registrar_evento_cocina(self, evento):
        if evento.get("tipo") == "progreso":
            return

        self.cocina_eventos.insert(0, evento)
        self.cocina_eventos = self.cocina_eventos[:30]
        self._set_status(evento.get("mensaje", "Cocina actualizada."))

        if self.current_view in {"panel", "cocina", "pedidos"}:
            self._refrescar_vista_actual()

    def procesar_cocina(self):
        if self.busy:
            return

        resumen_antes = self._resumen_estados()
        if resumen_antes["pendiente"] == 0:
            messagebox.showinfo("Cocina", "No hay pedidos pendientes para procesar.")
            return

        self.busy = True
        self._set_status("Procesando pedidos en cocina...")

        def worker():
            error = None
            try:
                def callback(evento):
                    self.after(0, lambda evento=evento: self._registrar_evento_cocina(evento))

                procesar_pedidos_con_hilos(
                    self.pizzeria,
                    cantidad_cocineros=2,
                    callback=callback,
                    velocidad=0.12,
                )
            except Exception as exc:
                error = exc
            resumen_despues = self._resumen_estados()
            self.after(0, lambda: self._finalizar_cocina(resumen_antes, resumen_despues, error))

        threading.Thread(target=worker, daemon=True).start()

    def _finalizar_cocina(self, antes, despues, error):
        self.busy = False
        if error:
            self._set_status(f"Error al procesar cocina: {error}")
            messagebox.showerror("Cocina", str(error))
            return

        listos = despues["listo"] - antes["listo"]
        cancelados = despues["cancelado"] - antes["cancelado"]
        self._set_status(f"Cocina procesada: {listos} listos, {cancelados} cancelados.")
        self._refrescar_vista_actual()
        messagebox.showinfo(
            "Cocina procesada",
            f"Pedidos procesados: {antes['pendiente']}\nListos: {listos}\nCancelados: {cancelados}",
        )

    def guardar_respaldo(self):
        datos = {
            "dinero": self.pizzeria.obtener_dinero(),
            "catalogo": self.pizzeria.catalogo_to_dict(),
            "stock": self.pizzeria.inventario.obtener_stock(),
            "ventas": self.pizzeria.obtener_ventas(),
            "pedidos": [pedido.to_dict() for pedido in self.pizzeria.obtener_pedidos()],
        }
        ruta = guardar_json(datos, "respaldo_pizzeria.json")
        self._set_status(f"Respaldo guardado en {ruta}.")
        messagebox.showinfo("Respaldo", f"Respaldo guardado en:\n{ruta}")

    def cargar_respaldo(self):
        if not messagebox.askyesno("Cargar respaldo", "Esto reemplazara los datos actuales. Deseas continuar?"):
            return

        try:
            cargar_respaldo_pizzeria(self.pizzeria, "respaldo_pizzeria.json")
        except (FileNotFoundError, ValueError, KeyError) as error:
            messagebox.showerror("Respaldo", str(error))
            return

        self._set_status("Respaldo cargado correctamente.")
        self._refrescar_vista_actual()
        messagebox.showinfo("Respaldo", "Guardado cargado correctamente.")

    def consultar_proveedor(self):
        self._set_status("Consultando proveedor externo...")

        def worker():
            try:
                from src.servicios.proveedores import consultar_dolar_oficial

                valor = consultar_dolar_oficial()
                self.after(0, lambda: self._mostrar_dolar(valor, None))
            except Exception as error:
                self.after(0, lambda: self._mostrar_dolar(None, error))

        threading.Thread(target=worker, daemon=True).start()

    def _mostrar_dolar(self, valor, error):
        if error:
            self._set_status(f"No se pudo consultar el dolar: {error}")
            messagebox.showerror("Proveedor externo", str(error))
            return

        self._set_status(f"Dolar oficial de venta: {formato_moneda(valor)}.")
        messagebox.showinfo("Proveedor externo", f"Dolar oficial de venta: {formato_moneda(valor)}")

    def generar_reportes(self):
        try:
            ruta_ventas = generar_reporte_ventas(self.pizzeria.obtener_ventas())
            ruta_stock = generar_reporte_stock(self.pizzeria.inventario.obtener_stock_detallado())
        except Exception as error:
            messagebox.showerror("Reportes", f"No se pudieron generar los reportes:\n{error}")
            return

        self._set_status("Reportes generados correctamente.")
        if self.current_view == "reportes":
            self.mostrar_reportes()
        messagebox.showinfo("Reportes", f"Reportes generados:\n{ruta_ventas}\n{ruta_stock}")

    def _refrescar_vista_actual(self):
        vistas = {
            "panel": self.mostrar_panel,
            "catalogo": self.mostrar_catalogo,
            "pedidos": self.mostrar_pedidos,
            "cocina": self.mostrar_cocina,
            "stock": self.mostrar_stock,
            "reportes": self.mostrar_reportes,
            "herramientas": self.mostrar_herramientas,
        }
        vistas.get(self.current_view, self.mostrar_panel)()

    def _cerrar_aplicacion(self):
        if messagebox.askyesno("Salir", "Deseas guardar un respaldo antes de salir?"):
            self.guardar_respaldo()
        self.destroy()


def ejecutar_menu():
    app = PizzeriaApp()
    app.mainloop()
