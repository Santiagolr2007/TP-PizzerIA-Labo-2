import threading
import tkinter as tk
from tkinter import messagebox, ttk

from src.modelos.producto import Bebida, Empanada, Pizza
from src.servicios.cocina_threads import (
    calcular_tiempo_estimado,
    determinar_estaciones_pedido,
    procesar_pedidos_con_hilos,
)
from src.servicios.inicializacion import crear_sistema, obtener_dolar_referencia
from src.servicios.persistencia import cargar_respaldo_pizzeria, guardar_json
from src.servicios.promociones import calcular_descuentos_por_linea, calcular_promociones_pedido
from src.servicios.reportes_excel import (generar_reporte_stock,generar_reporte_ventas,leer_reporte_excel,)
from src.servicios.tickets_pdf import generar_ticket_pdf
from src.servicios.usuarios import cambiar_contrasenia, validar_usuario
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


def nombre_ingrediente_visible(nombre):
    ingredientes = {
        "jamon": "jamón",
        "morron": "morrón",
        "jamon_queso": "jamón y queso",
        "tapas_empanada": "tapas de empanada",
    }
    texto = str(nombre).strip()
    return ingredientes.get(texto.lower(), texto.replace("_", " "))


def capitalizar_visible(texto):
    texto_visible = nombre_ingrediente_visible(texto)
    if not texto_visible:
        return ""
    return texto_visible[0].upper() + texto_visible[1:]


def normalizar_ingrediente_ingresado(nombre):
    ingredientes = {
        "jamón": "jamon",
        "morrón": "morron",
        "jamón y queso": "jamon_queso",
        "tapas de empanada": "tapas_empanada",
    }
    texto = str(nombre).strip().lower()
    return ingredientes.get(texto, texto)


def obtener_resumen_productos(pedido):
    productos_agrupados = {}

    for linea in pedido.iterar_lineas_detalle():
        nombre = linea["nombre"]
        if nombre not in productos_agrupados:
            productos_agrupados[nombre] = {"cantidad": 0, "subtotal": 0, "descuento": 0}

        productos_agrupados[nombre]["cantidad"] += linea["cantidad"]
        productos_agrupados[nombre]["subtotal"] += linea["subtotal"]
        productos_agrupados[nombre]["descuento"] += linea["descuento"]

    textos = []
    for nombre_producto, datos in productos_agrupados.items():
        texto = f"{nombre_producto} x{datos['cantidad']} ({formato_moneda(datos['subtotal'])})"
        if datos["descuento"]:
            texto += " promo"
        textos.append(texto)

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
        self.admin_sidebar_buttons = []
        self.busy = False
        self.cocina_eventos = []
        self.cocina_tabla = None
        self.usuario_actual = None

        self.title("PizzerIA - Gestión de pizzería")
        self.configure(bg=self.colors["bg"])
        self._configurar_ventana_principal()

        self.pizzeria = crear_sistema()
        self.page_title = tk.StringVar(value="Panel")
        self.page_subtitle = tk.StringVar(value="Resumen general del negocio")
        self.money_label_text = tk.StringVar(value="Caja disponible")
        self.money_text = tk.StringVar()
        self.dolar_text = tk.StringVar(value="Consultando...")
        self.status_text = tk.StringVar(value="Sistema iniciado correctamente.")

        self._configurar_estilos()
        self._crear_layout()
        self._refrescar_dolar_referencia()
        self._mostrar_login()
        if self.usuario_actual is None:
            return
        self._actualizar_permisos_nav()
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

    def _calcular_geometria_adaptada(self, ancho, alto, min_ancho, min_alto, margen=80):
        pantalla_ancho = self.winfo_screenwidth()
        pantalla_alto = self.winfo_screenheight()
        max_ancho = max(360, pantalla_ancho - margen)
        max_alto = max(320, pantalla_alto - margen)
        ancho_final = min(ancho, max_ancho)
        alto_final = min(alto, max_alto)
        min_ancho_final = min(min_ancho, ancho_final)
        min_alto_final = min(min_alto, alto_final)
        x = max(0, (pantalla_ancho - ancho_final) // 2)
        y = max(0, (pantalla_alto - alto_final) // 2)
        return ancho_final, alto_final, min_ancho_final, min_alto_final, x, y

    def _configurar_ventana_principal(self):
        ancho, alto, min_ancho, min_alto, x, y = self._calcular_geometria_adaptada(
            1180,
            720,
            1020,
            640,
            margen=70,
        )
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.minsize(min_ancho, min_alto)

    def _configurar_dialogo(self, ventana, ancho, alto, min_ancho, min_alto):
        ancho, alto, min_ancho, min_alto, x, y = self._calcular_geometria_adaptada(
            ancho,
            alto,
            min_ancho,
            min_alto,
            margen=90,
        )
        ventana.geometry(f"{ancho}x{alto}+{x}+{y}")
        ventana.minsize(min_ancho, min_alto)
        ventana.resizable(True, True)

    def _crear_contenido_scrollable(self, ventana):
        # Tkinter no permite scrollear frames directamente, por eso se usa un Canvas
        # que contiene el frame real y ajusta su ancho al redimensionar la ventana.
        contenedor = tk.Frame(ventana, bg=self.colors["bg"])
        contenedor.pack(fill="both", expand=True)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(0, weight=1)

        canvas = tk.Canvas(contenedor, bg=self.colors["bg"], highlightthickness=0)
        scroll = ttk.Scrollbar(contenedor, orient="vertical", command=canvas.yview)
        interior = tk.Frame(canvas, bg=self.colors["bg"])
        ventana_canvas = canvas.create_window((0, 0), window=interior, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        def ajustar_scroll(_evento=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def ajustar_ancho(evento):
            canvas.itemconfigure(ventana_canvas, width=evento.width)

        def rueda(evento):
            canvas.yview_scroll(int(-1 * (evento.delta / 120)), "units")

        interior.bind("<Configure>", ajustar_scroll)
        canvas.bind("<Configure>", ajustar_ancho)
        canvas.bind("<Enter>", lambda _evento: canvas.bind_all("<MouseWheel>", rueda))
        canvas.bind("<Leave>", lambda _evento: canvas.unbind_all("<MouseWheel>"))
        return interior

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
            text="Gestión operativa",
            bg=self.colors["sidebar"],
            fg="#CBD5E1",
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        navegacion = [
            ("panel", "Panel", self.mostrar_panel),
            ("catalogo", "Catálogo", self.mostrar_catalogo),
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
        self._crear_boton_sidebar("Cambiar usuario", self.cambiar_usuario)
        self.admin_sidebar_buttons.append(self._crear_boton_sidebar("Guardar respaldo", self.guardar_respaldo))
        self.admin_sidebar_buttons.append(self._crear_boton_sidebar("Cargar respaldo", self.cargar_respaldo))

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
            textvariable=self.money_label_text,
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

        dolar = tk.Frame(barra, bg=self.colors["surface"], highlightthickness=1, highlightbackground=self.colors["line"])
        dolar.grid(row=0, column=2, rowspan=2, sticky="e", padx=(12, 0))
        tk.Label(
            dolar,
            text="Dólar oficial",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="e", padx=18, pady=(9, 0))
        tk.Label(
            dolar,
            textvariable=self.dolar_text,
            bg=self.colors["surface"],
            fg=self.colors["info"],
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
            if not self._puede_acceder(clave_boton):
                boton.configure(state="disabled", bg=self.colors["sidebar"], fg="#6B7280")
                continue
            activo = clave_boton == clave
            boton.configure(
                state="normal",
                bg=self.colors["accent"] if activo else self.colors["sidebar"],
                fg="#FFFFFF" if activo else "#D1D5DB",
            )

    def _limpiar_contenido(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def _refrescar_caja(self):
        if self._es_administrador():
            self.money_label_text.set("Caja disponible")
            self.money_text.set(formato_moneda(self.pizzeria.obtener_dinero()))
            return

        self.money_label_text.set("Usuario activo")
        rol = self.usuario_actual.get("rol", "Empleado") if self.usuario_actual else "Empleado"
        self.money_text.set(rol)

    def _refrescar_dolar_referencia(self):
        valor = obtener_dolar_referencia()
        self.dolar_text.set(formato_moneda(valor))

    def _set_status(self, texto):
        self.status_text.set(texto)

    def _es_administrador(self):
        return bool(self.usuario_actual and self.usuario_actual.get("rol") == "Administrador")

    def _puede_acceder(self, vista):
        if self._es_administrador():
            return True
        return vista in {"panel", "pedidos", "cocina", "stock"}

    def _requiere_admin(self, accion="realizar esta acción"):
        if self._es_administrador():
            return True
        messagebox.showwarning("Permiso requerido", f"Solo el administrador puede {accion}.")
        return False

    def _actualizar_permisos_nav(self):
        for clave, boton in self.nav_buttons.items():
            if self._puede_acceder(clave):
                boton.configure(state="normal")
            else:
                boton.configure(state="disabled", bg=self.colors["sidebar"], fg="#6B7280")
        for boton in self.admin_sidebar_buttons:
            if self._es_administrador():
                boton.configure(state="normal", fg="#D1D5DB")
            else:
                boton.configure(state="disabled", fg="#6B7280")

    def _mostrar_login(self):
        ventana = tk.Toplevel(self)
        ventana.title("Iniciar sesión")
        ventana.configure(bg=self.colors["bg"])
        ventana.transient(self)
        ventana.grab_set()
        self._configurar_dialogo(ventana, 500, 520, 400, 420)

        contenido = self._crear_contenido_scrollable(ventana)
        marco = tk.Frame(contenido, bg=self.colors["surface"], highlightthickness=1, highlightbackground=self.colors["line"])
        marco.pack(fill="both", expand=True, padx=24, pady=24)

        tk.Label(
            marco,
            text="PizzerIA",
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Segoe UI", 24, "bold"),
        ).pack(anchor="w", padx=22, pady=(24, 2))
        tk.Label(
            marco,
            text="Ingresa con tu usuario para continuar",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=22, pady=(0, 20))

        formulario = tk.Frame(marco, bg=self.colors["surface"])
        formulario.pack(fill="x", padx=22)
        formulario.grid_columnconfigure(0, weight=1)

        usuario = tk.StringVar(value="administrador")
        contrasenia = tk.StringVar()

        tk.Label(formulario, text="Usuario", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        entrada_usuario = ttk.Entry(formulario, textvariable=usuario)
        entrada_usuario.grid(row=1, column=0, sticky="ew", pady=(0, 14))

        tk.Label(formulario, text="Contraseña", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 6))
        entrada_clave = ttk.Entry(formulario, textvariable=contrasenia, show="*")
        entrada_clave.grid(row=3, column=0, sticky="ew", pady=(0, 14))

        def cerrar():
            self.usuario_actual = None
            ventana.destroy()
            self.destroy()

        def ingresar(_evento=None):
            try:
                self.usuario_actual = validar_usuario(usuario.get(), contrasenia.get())
            except ValueError as error:
                messagebox.showerror("Acceso denegado", str(error), parent=ventana)
                return

            self._set_status(
                f"Sesión iniciada: {self.usuario_actual['nombre']} ({self.usuario_actual['rol']})."
            )
            ventana.destroy()

        pie = tk.Frame(marco, bg=self.colors["surface"])
        pie.pack(fill="x", padx=22, pady=(24, 20))
        self._boton_accion(pie, "Ingresar", ingresar, "principal").pack(side="right")
        self._boton_accion(pie, "Salir", cerrar, "secundario").pack(side="right", padx=(0, 10))

        ventana.protocol("WM_DELETE_WINDOW", cerrar)
        entrada_clave.bind("<Return>", ingresar)
        entrada_usuario.focus_set()
        self.wait_window(ventana)

    def cambiar_usuario(self):
        self._mostrar_login()
        if self.usuario_actual is None:
            return
        self._actualizar_permisos_nav()
        if not self._puede_acceder(self.current_view):
            self.mostrar_panel()
        else:
            self._refrescar_vista_actual()

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
                extras.append(f"{nombre_ingrediente_visible(ingrediente)} x{cantidad}")
            detalle = f"Tamaño {producto.tamanio}"
            if extras:
                detalle += " | " + ", ".join(extras)
            return detalle

        if isinstance(producto, Empanada):
            return f"Relleno: {nombre_ingrediente_visible(producto.ingrediente_relleno)}"

        if isinstance(producto, Bebida):
            ingrediente = producto.ingrediente_stock or "sin control"
            return f"Stock asociado: {nombre_ingrediente_visible(ingrediente)}"

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
                    "descuento": formato_moneda(pedido.calcular_descuento_total()),
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
        # Cocina muestra pedidos activos: pendientes, en preparacion, listos y delivery en camino.
        # Se excluyen entregados/cancelados porque ya no necesitan trabajo operativo.
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
                    "direccion": pedido.direccion or "-",
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
                    "ingrediente": capitalizar_visible(fila["ingrediente"]),
                    "cantidad": formato_numero(cantidad),
                    "precio_unitario": formato_moneda(fila["precio_unitario"]),
                    "valor_total_stock": formato_moneda(fila["valor_total_stock"]),
                    "estado": "Reponer" if cantidad <= 5 else "Disponible",
                }
            )
        filas.sort(key=lambda fila: fila["ingrediente"])
        return filas

    def _total_ventas(self):
        self._sincronizar_ventas_entregadas()
        total = 0
        for venta in self.pizzeria.obtener_ventas():
            try:
                total += float(venta.get("subtotal", 0))
            except (TypeError, ValueError):
                pass
        return total

    def _sincronizar_ventas_entregadas(self, notificar=False):
        # Antes de reportar o respaldar, completa ventas faltantes desde pedidos entregados.
        ventas_agregadas = self.pizzeria.sincronizar_ventas_entregadas()
        if ventas_agregadas and notificar:
            self._set_status(f"Ventas sincronizadas: {ventas_agregadas} pedidos entregados agregados.")
        return ventas_agregadas

    def _generar_archivos_reportes(self):
        # Punto unico de generacion: mantiene Excel y vista de reportes con los mismos datos.
        self._sincronizar_ventas_entregadas()
        ruta_ventas = generar_reporte_ventas(self.pizzeria.obtener_ventas())
        ruta_stock = generar_reporte_stock(self.pizzeria.inventario.obtener_stock_detallado())
        return ruta_ventas, ruta_stock

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
        acciones_panel = [
            ("Nuevo pedido", self.abrir_dialogo_pedido, "principal"),
            ("Procesar cocina", self.procesar_cocina, "info"),
            ("Ver cocina", self.mostrar_cocina, "secundario"),
        ]
        if self._es_administrador():
            acciones_panel.extend(
                [
                    ("Nuevo producto", lambda: self.abrir_dialogo_producto(), "secundario"),
                    ("Reponer stock", self.abrir_dialogo_reponer_stock, "exito"),
                    ("Generar reportes", self.generar_reportes, "secundario"),
                ]
            )

        for texto, comando, variante in acciones_panel:
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
            ("Preparación", estados["en preparacion"], "Trabajando ahora", self.colors["info"]),
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
        columnas_cocina = ("pedido_id", "cliente", "estado", "estacion", "cocinero", "tiempo", "entrega", "direccion")
        frame_cocina, tabla_cocina = self._crear_tabla(
            body_cocina,
            columnas_cocina,
            {
                "pedido_id": "ID",
                "cliente": "Cliente",
                "estado": "Estado",
                "estacion": "Estación",
                "cocinero": "Cocinero",
                "tiempo": "Tiempo",
                "entrega": "Entrega",
                "direccion": "Dirección",
            },
            {"pedido_id": 55, "cliente": 120, "estado": 115, "estacion": 140, "cocinero": 110, "tiempo": 80, "entrega": 85, "direccion": 160},
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
            {"estacion": "Estación", "pendientes": "Pend.", "en_preparacion": "Prep.", "listos": "Listos"},
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
        if not self._requiere_admin("administrar el catálogo"):
            self.mostrar_panel()
            return

        self.current_view = "catalogo"
        self._seleccionar_nav("catalogo")
        self.page_title.set("Catálogo")
        self.page_subtitle.set("Productos disponibles para vender")
        self._limpiar_contenido()
        self._refrescar_caja()

        seccion, cuerpo = self._crear_seccion(self.content, "Productos", "Busca por nombre o categoría")
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
            {"numero": "#", "producto": "Producto", "categoria": "Categoría", "detalle": "Detalle", "precio": "Precio"},
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
            messagebox.showwarning("Producto requerido", "Selecciona un producto del catálogo.")
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

        if not messagebox.askyesno("Eliminar producto", f"¿Eliminar '{producto.nombre}' del catálogo?"):
            return

        try:
            self.pizzeria.eliminar_producto(producto.nombre)
        except (PizzeriaError, ValueError) as error:
            messagebox.showerror("No se pudo eliminar", str(error))
            return

        self._set_status(f"Producto eliminado: {producto.nombre}.")
        self.mostrar_catalogo()

    def abrir_dialogo_producto(self, producto=None):
        if not self._requiere_admin("gestionar productos"):
            return

        ventana = tk.Toplevel(self)
        ventana.title("Editar producto" if producto else "Nuevo producto")
        ventana.configure(bg=self.colors["bg"])
        ventana.transient(self)
        ventana.grab_set()
        self._configurar_dialogo(ventana, 620, 680, 500, 500)

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

        contenido = self._crear_contenido_scrollable(ventana)
        marco = tk.Frame(contenido, bg=self.colors["surface"], highlightthickness=1, highlightbackground=self.colors["line"])
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
            text="Los cambios se aplican al catálogo para nuevos pedidos.",
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

        etiqueta("Categoría", 0)
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

        tk.Label(frame_pizza, text="Tamaño", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))
        ttk.Combobox(frame_pizza, textvariable=tamanio, values=("chica", "mediana", "grande"), state="readonly").pack(fill="x", pady=(0, 12))
        tk.Label(frame_pizza, text="Ingredientes extra", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))
        ttk.Entry(frame_pizza, textvariable=extras).pack(fill="x")
        tk.Label(frame_pizza, text="Formato: jamón:2, morrón:1", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))

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
                ingrediente = normalizar_ingrediente_ingresado(ingrediente)
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
        self._boton_accion(barra, "Ticket PDF", lambda: self.exportar_ticket_desde_tabla(tabla), "secundario").pack(side="left", padx=(0, 10))
        self._boton_accion(barra, "Actualizar", self.mostrar_pedidos, "secundario").pack(side="left")

        columnas = ("pedido_id", "cliente", "entrega", "direccion", "estado", "productos", "descuento", "total")
        frame_tabla, tabla = self._crear_tabla(
            cuerpo,
            columnas,
            {
                "pedido_id": "ID",
                "cliente": "Cliente",
                "entrega": "Entrega",
                "direccion": "Dirección",
                "estado": "Estado",
                "productos": "Productos",
                "descuento": "Desc.",
                "total": "Total",
            },
            {
                "pedido_id": 70,
                "cliente": 140,
                "entrega": 95,
                "direccion": 170,
                "estado": 120,
                "productos": 300,
                "descuento": 100,
                "total": 120,
            },
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
        estado = {
            "en preparación": "en preparacion",
            "en preparaciÃ³n": "en preparacion",
        }.get(estado, estado)
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

        seccion_cola, body_cola = self._crear_seccion(contenedor, "Cola de cocina", "Pedidos pendientes, en preparación y listos")
        seccion_cola.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        columnas_cola = ("pedido_id", "cliente", "estado", "estacion", "cocinero", "tiempo", "entrega", "direccion")
        frame_cola, tabla_cola = self._crear_tabla(
            body_cola,
            columnas_cola,
            {
                "pedido_id": "ID",
                "cliente": "Cliente",
                "estado": "Estado",
                "estacion": "Estación",
                "cocinero": "Cocinero",
                "tiempo": "Tiempo",
                "entrega": "Entrega",
                "direccion": "Dirección",
            },
            {"pedido_id": 60, "cliente": 130, "estado": 115, "estacion": 150, "cocinero": 120, "tiempo": 90, "entrega": 95, "direccion": 190},
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
            {"estacion": "Estación", "pendientes": "Pend.", "en_preparacion": "Prep.", "listos": "Listos"},
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

        seccion, cuerpo = self._crear_seccion(self.content, "Inventario", "Ingredientes, costos y alertas de reposición")
        seccion.pack(fill="both", expand=True)

        barra = tk.Frame(cuerpo, bg=self.colors["surface"])
        barra.pack(fill="x", pady=(0, 12))
        if self._es_administrador():
            self._boton_accion(barra, "Reponer stock", self.abrir_dialogo_reponer_stock, "exito").pack(side="left", padx=(0, 10))
            self._boton_accion(barra, "Generar reporte", self.generar_reportes, "secundario").pack(side="left")
        else:
            tk.Label(
                barra,
                text="Modo empleado: consulta de stock disponible",
                bg=self.colors["surface"],
                fg=self.colors["muted"],
                font=("Segoe UI", 10, "bold"),
            ).pack(side="left")

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
        if not self._requiere_admin("ver reportes e historial de ventas"):
            self.mostrar_panel()
            return

        self.current_view = "reportes"
        self._seleccionar_nav("reportes")
        self.page_title.set("Reportes")
        self.page_subtitle.set("Gráficos simples, ventas y stock")
        self._limpiar_contenido()
        self._refrescar_caja()
        try:
            # La pestaña lee archivos Excel, por eso primero los regeneramos.
            self._generar_archivos_reportes()
        except Exception as error:
            self._set_status(f"No se pudieron actualizar los reportes: {error}")

        seccion, cuerpo = self._crear_seccion(self.content, "Reportes y gráficos", "Indicadores visuales, ventas y stock del negocio")
        seccion.pack(fill="both", expand=True)

        barra = tk.Frame(cuerpo, bg=self.colors["surface"])
        barra.pack(fill="x", pady=(0, 12))
        self._boton_accion(barra, "Generar reportes", self.generar_reportes, "principal").pack(side="left", padx=(0, 10))
        self._boton_accion(barra, "Actualizar vista", self.mostrar_reportes, "secundario").pack(side="left")

        notebook = ttk.Notebook(cuerpo)
        notebook.pack(fill="both", expand=True)
        self._agregar_tab_graficos(notebook)
        self._agregar_tab_reporte(notebook, "Ventas", "reporte_ventas.xlsx")
        self._agregar_tab_reporte(notebook, "Stock", "reporte_stock.xlsx")

    def _agregar_tab_graficos(self, notebook):
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="Gráficos")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        graficos = [
            ("Pedidos por estado", self._datos_grafico_estados(), self.colors["info"], 0, 0),
            ("Ventas por producto", self._datos_grafico_productos(), self.colors["accent"], 0, 1),
            ("Stock mas bajo", self._datos_grafico_stock_bajo(), self.colors["danger"], 1, 0),
            ("Descuentos por promocion", self._datos_grafico_descuentos(), self.colors["success"], 1, 1),
        ]

        for titulo, datos, color, fila, columna in graficos:
            seccion, cuerpo = self._crear_seccion(tab, titulo)
            seccion.grid(row=fila, column=columna, sticky="nsew", padx=(0 if columna == 0 else 10, 0), pady=(0 if fila == 0 else 10, 0))
            self._dibujar_grafico_barras(cuerpo, datos, color)

    def _datos_grafico_estados(self):
        estados = self._resumen_estados()
        return [
            ("Pend.", estados["pendiente"]),
            ("Prep.", estados["en preparacion"]),
            ("Listos", estados["listo"]),
            ("Camino", estados["en camino"]),
            ("Entreg.", estados["entregado"]),
            ("Cancel.", estados["cancelado"]),
        ]

    def _datos_grafico_productos(self):
        ventas_por_producto = {}
        for venta in self.pizzeria.obtener_ventas():
            producto = str(venta.get("producto", "")).strip()
            if not producto:
                continue
            ventas_por_producto[producto] = ventas_por_producto.get(producto, 0) + float(venta.get("subtotal", 0) or 0)

        datos = sorted(ventas_por_producto.items(), key=lambda item: item[1], reverse=True)
        return datos[:6]

    def _datos_grafico_stock_bajo(self):
        filas = []
        for item in self.pizzeria.inventario.obtener_stock_detallado():
            filas.append((capitalizar_visible(item["ingrediente"]), float(item["cantidad"])))
        filas.sort(key=lambda item: item[1])
        return filas[:6]

    def _datos_grafico_descuentos(self):
        total_descuento = 0
        for venta in self.pizzeria.obtener_ventas():
            total_descuento += float(venta.get("descuento", 0) or 0)
        return [("Promos", total_descuento)] if total_descuento else []

    def _dibujar_grafico_barras(self, parent, datos, color):
        canvas = tk.Canvas(parent, bg=self.colors["surface"], highlightthickness=0, height=210)
        canvas.pack(fill="both", expand=True)

        def dibujar(_evento=None):
            canvas.delete("all")
            ancho = max(canvas.winfo_width(), 260)
            alto = max(canvas.winfo_height(), 190)

            if not datos:
                canvas.create_text(
                    ancho / 2,
                    alto / 2,
                    text="Sin datos disponibles",
                    fill=self.colors["muted"],
                    font=("Segoe UI", 11, "bold"),
                )
                return

            margen_izq = 44
            margen_der = 20
            margen_arriba = 18
            margen_abajo = 48
            area_ancho = ancho - margen_izq - margen_der
            area_alto = alto - margen_arriba - margen_abajo
            maximo = max(valor for _etiqueta, valor in datos) or 1
            separacion = 10
            ancho_barra = max(24, (area_ancho - separacion * (len(datos) - 1)) / len(datos))

            canvas.create_line(
                margen_izq,
                margen_arriba + area_alto,
                ancho - margen_der,
                margen_arriba + area_alto,
                fill=self.colors["line"],
            )

            for indice, (etiqueta, valor) in enumerate(datos):
                x0 = margen_izq + indice * (ancho_barra + separacion)
                x1 = x0 + ancho_barra
                altura = 0 if maximo == 0 else (valor / maximo) * area_alto
                y0 = margen_arriba + area_alto - altura
                y1 = margen_arriba + area_alto
                canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")

                valor_visible = formato_moneda(valor) if valor >= 1000 else formato_numero(valor)
                canvas.create_text(
                    (x0 + x1) / 2,
                    max(y0 - 10, 10),
                    text=valor_visible,
                    fill=self.colors["text"],
                    font=("Segoe UI", 8, "bold"),
                )
                etiqueta_visible = str(etiqueta)
                if len(etiqueta_visible) > 13:
                    etiqueta_visible = etiqueta_visible[:12] + "."
                canvas.create_text(
                    (x0 + x1) / 2,
                    y1 + 18,
                    text=etiqueta_visible,
                    fill=self.colors["muted"],
                    font=("Segoe UI", 8),
                    width=ancho_barra + 18,
                )

        canvas.bind("<Configure>", dibujar)
        self.after(120, dibujar)

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
                text="El reporte está vacío.",
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
                if (
                    "total" in columna_normalizada
                    or "precio" in columna_normalizada
                    or "subtotal" in columna_normalizada
                    or "descuento" in columna_normalizada
                ):
                    fila_formateada[columna] = formato_moneda(valor)
                else:
                    fila_formateada[columna] = valor
            filas_formateadas.append(fila_formateada)
        self._llenar_tabla(tabla, columnas, filas_formateadas)

    def mostrar_herramientas(self):
        if not self._requiere_admin("abrir herramientas administrativas"):
            self.mostrar_panel()
            return

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

        seccion_proveedor, body_proveedor = self._crear_seccion(contenedor, "Proveedor externo", "Consulta de cotización")
        seccion_proveedor.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self._boton_accion(body_proveedor, "Consultar dólar oficial", self.consultar_proveedor, "info").pack(fill="x")

        seccion_usuarios, body_usuarios = self._crear_seccion(contenedor, "Usuarios", "Cambiar claves de administrador y empleado")
        seccion_usuarios.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(20, 0))
        self._boton_accion(body_usuarios, "Gestionar contraseñas", self.abrir_dialogo_contrasenias, "principal").pack(fill="x")

        seccion_estado, body_estado = self._crear_seccion(contenedor, "Estado actual", "Datos rápidos del sistema")
        seccion_estado.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(20, 0))
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

    def abrir_dialogo_contrasenias(self):
        if not self._requiere_admin("cambiar contraseñas"):
            return

        ventana = tk.Toplevel(self)
        ventana.title("Usuarios")
        ventana.configure(bg=self.colors["bg"])
        ventana.transient(self)
        ventana.grab_set()
        self._configurar_dialogo(ventana, 540, 500, 420, 380)

        contenido = self._crear_contenido_scrollable(ventana)
        marco = tk.Frame(contenido, bg=self.colors["surface"], highlightthickness=1, highlightbackground=self.colors["line"])
        marco.pack(fill="both", expand=True, padx=22, pady=22)
        tk.Label(
            marco,
            text="Gestionar contraseñas",
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w", padx=18, pady=(18, 4))
        tk.Label(
            marco,
            text="El cambio queda guardado para los próximos inicios de sesión.",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=18, pady=(0, 16))

        formulario = tk.Frame(marco, bg=self.colors["surface"])
        formulario.pack(fill="x", padx=18)
        formulario.grid_columnconfigure(0, weight=1)

        usuario = tk.StringVar(value="administrador")
        nueva = tk.StringVar()
        repetir = tk.StringVar()

        tk.Label(formulario, text="Usuario", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Combobox(formulario, textvariable=usuario, values=("administrador", "empleado"), state="readonly").grid(row=1, column=0, sticky="ew", pady=(0, 12))
        tk.Label(formulario, text="Nueva contraseña", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(formulario, textvariable=nueva, show="*").grid(row=3, column=0, sticky="ew", pady=(0, 12))
        tk.Label(formulario, text="Repetir contraseña", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(formulario, textvariable=repetir, show="*").grid(row=5, column=0, sticky="ew")

        pie = tk.Frame(marco, bg=self.colors["surface"])
        pie.pack(fill="x", padx=18, pady=(18, 18))
        self._boton_accion(pie, "Cancelar", ventana.destroy, "secundario").pack(side="right", padx=(10, 0))

        def guardar():
            if nueva.get() != repetir.get():
                messagebox.showerror("Contraseñas", "Las contraseñas no coinciden.", parent=ventana)
                return

            try:
                cambiar_contrasenia(usuario.get(), nueva.get())
            except ValueError as error:
                messagebox.showerror("Contraseñas", str(error), parent=ventana)
                return

            self._set_status(f"Contraseña actualizada para {usuario.get()}.")
            messagebox.showinfo("Contraseñas", "La contraseña fue actualizada correctamente.", parent=ventana)
            ventana.destroy()

        self._boton_accion(pie, "Guardar cambio", guardar, "principal").pack(side="right")

    def abrir_dialogo_pedido(self):
        ventana = tk.Toplevel(self)
        ventana.title("Nuevo pedido")
        ventana.configure(bg=self.colors["bg"])
        ventana.transient(self)
        ventana.grab_set()
        self._configurar_dialogo(ventana, 980, 720, 760, 540)

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
        tk.Label(datos_cliente, text="Dirección", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).grid(row=0, column=4, sticky="w", padx=(14, 8), pady=12)
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

        seccion_catalogo, body_catalogo = self._crear_seccion(cuerpo, "Catálogo", "Selecciona productos y cantidades")
        seccion_catalogo.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        columnas_catalogo = ("numero", "producto", "categoria", "precio")
        frame_catalogo, tabla_catalogo = self._crear_tabla(
            body_catalogo,
            columnas_catalogo,
            {"numero": "#", "producto": "Producto", "categoria": "Categoría", "precio": "Precio"},
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

        promo_text = tk.StringVar(value="Sin promociones aplicadas.")
        subtotal_text = tk.StringVar(value="Subtotal: $0.00")
        descuento_text = tk.StringVar(value="Descuento: $0.00")
        total_text = tk.StringVar(value="Total: $0.00")
        tk.Label(
            body_carrito,
            textvariable=promo_text,
            bg=self.colors["surface"],
            fg=self.colors["success"],
            font=("Segoe UI", 9, "bold"),
            anchor="e",
        ).pack(fill="x", pady=(12, 0))
        tk.Label(
            body_carrito,
            textvariable=subtotal_text,
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
            anchor="e",
        ).pack(fill="x", pady=(8, 0))
        tk.Label(
            body_carrito,
            textvariable=descuento_text,
            bg=self.colors["surface"],
            fg=self.colors["warning"],
            font=("Segoe UI", 10, "bold"),
            anchor="e",
        ).pack(fill="x")
        tk.Label(
            body_carrito,
            textvariable=total_text,
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Segoe UI", 15, "bold"),
            anchor="e",
        ).pack(fill="x", pady=(12, 0))

        def renderizar_carrito():
            # Recalcula tabla, promociones y totales cada vez que cambia el carrito.
            # Usa el mismo motor de promociones que despues usan Pedido, ticket y Excel.
            filas = []
            lineas_carrito = list(carrito.items())
            productos_carrito = []
            for _nombre, datos in lineas_carrito:
                productos_carrito.append((datos["producto"], datos["cantidad"]))

            promociones = calcular_promociones_pedido(productos_carrito)
            descuentos_por_linea = calcular_descuentos_por_linea(productos_carrito)

            subtotal_bruto = 0
            descuento_total = 0
            for indice, (nombre, datos) in enumerate(lineas_carrito):
                producto = datos["producto"]
                subtotal_linea = producto.calcular_precio() * datos["cantidad"]
                descuento_linea = descuentos_por_linea.get(indice, 0)
                subtotal_bruto += subtotal_linea
                descuento_total += descuento_linea
                filas.append(
                    {
                        "producto": nombre,
                        "cantidad": datos["cantidad"],
                        "subtotal": formato_moneda(subtotal_linea - descuento_linea),
                    }
                )
            self._llenar_tabla(tabla_carrito, columnas_carrito, filas)
            total = subtotal_bruto - descuento_total
            if promociones:
                textos_promos = []
                for promocion in promociones:
                    textos_promos.append(f"{promocion['nombre']} ({formato_moneda(promocion['descuento'])})")
                promo_text.set(" | ".join(textos_promos))
            else:
                promo_text.set("Sin promociones aplicadas.")
            subtotal_text.set(f"Subtotal: {formato_moneda(subtotal_bruto)}")
            descuento_text.set(f"Descuento: {formato_moneda(descuento_total)}")
            total_text.set(f"Total: {formato_moneda(total)}")

        def agregar_producto():
            seleccion = tabla_catalogo.selection()
            if not seleccion:
                messagebox.showwarning("Producto requerido", "Selecciona un producto del catálogo.", parent=ventana)
                return

            try:
                cantidad_numero = int(cantidad.get())
                if cantidad_numero <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Cantidad inválida", "La cantidad debe ser un entero mayor que cero.", parent=ventana)
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
                messagebox.showwarning("Pedido vacío", "Agrega al menos un producto.", parent=ventana)
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
        if not self._requiere_admin("reponer stock"):
            return

        stock = self.pizzeria.inventario.obtener_stock_detallado()
        ingredientes = [fila["ingrediente"] for fila in stock]
        if not ingredientes:
            messagebox.showinfo("Sin stock", "No hay ingredientes cargados.")
            return

        ventana = tk.Toplevel(self)
        ventana.title("Reponer stock")
        ventana.configure(bg=self.colors["bg"])
        ventana.transient(self)
        ventana.grab_set()
        self._configurar_dialogo(ventana, 460, 340, 360, 280)

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
        ventana.configure(bg=self.colors["bg"])
        ventana.transient(self)
        self._configurar_dialogo(ventana, 720, 680, 460, 420)

        contenido = self._crear_contenido_scrollable(ventana)
        marco = tk.Frame(contenido, bg=self.colors["surface"], highlightthickness=1, highlightbackground=self.colors["line"])
        marco.pack(fill="both", expand=True, padx=22, pady=22)
        tk.Label(marco, text=f"Pedido #{pedido.pedido_id}", bg=self.colors["surface"], fg=self.colors["text"], font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=16, pady=(16, 2))
        tk.Label(marco, text=f"Cliente: {pedido.cliente}", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10)).pack(anchor="w", padx=16)
        tk.Label(marco, text=f"Entrega: {pedido.tipo_entrega}", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10)).pack(anchor="w", padx=16)
        if pedido.direccion:
            tk.Label(marco, text=f"Dirección: {pedido.direccion}", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10)).pack(anchor="w", padx=16)
        tk.Label(marco, text=f"Estado: {estado_visible(pedido.estado)}", bg=self.colors["surface"], fg=self.colors["muted"], font=("Segoe UI", 10)).pack(anchor="w", padx=16, pady=(0, 12))

        columnas = ("producto", "cantidad", "unitario", "descuento", "subtotal")
        frame_tabla, tabla = self._crear_tabla(
            marco,
            columnas,
            {
                "producto": "Producto",
                "cantidad": "Cant.",
                "unitario": "Unit.",
                "descuento": "Desc.",
                "subtotal": "Total",
            },
            {"producto": 210, "cantidad": 60, "unitario": 95, "descuento": 95, "subtotal": 110},
            alto=7,
        )
        frame_tabla.pack(fill="both", expand=True, padx=16)

        filas = []
        for linea in pedido.iterar_lineas_detalle():
            filas.append(
                {
                    "producto": linea["nombre"],
                    "cantidad": linea["cantidad"],
                    "unitario": formato_moneda(linea["precio_unitario"]),
                    "descuento": formato_moneda(linea["descuento"]) if linea["descuento"] else "-",
                    "subtotal": formato_moneda(linea["subtotal"]),
                }
            )
        self._llenar_tabla(tabla, columnas, filas)

        promociones = pedido.obtener_promociones()
        if promociones:
            for promocion in promociones:
                tk.Label(
                    marco,
                    text=f"{promocion['nombre']}: {promocion['descripcion']}",
                    bg=self.colors["surface"],
                    fg=self.colors["success"],
                    font=("Segoe UI", 10, "bold"),
                    anchor="e",
                ).pack(fill="x", padx=16, pady=(10, 0))

        tk.Label(
            marco,
            text=f"Subtotal: {formato_moneda(pedido.calcular_subtotal())}",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
            anchor="e",
        ).pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(
            marco,
            text=f"Descuento: {formato_moneda(pedido.calcular_descuento_total())}",
            bg=self.colors["surface"],
            fg=self.colors["warning"],
            font=("Segoe UI", 10, "bold"),
            anchor="e",
        ).pack(fill="x", padx=16)
        tk.Label(
            marco,
            text=f"Total: {formato_moneda(pedido.calcular_total())}",
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Segoe UI", 15, "bold"),
            anchor="e",
        ).pack(fill="x", padx=16, pady=12)

        pie = tk.Frame(marco, bg=self.colors["surface"])
        pie.pack(fill="x", padx=16, pady=(0, 16))
        self._boton_accion(pie, "Cerrar", ventana.destroy, "secundario").pack(side="right", padx=(10, 0))
        self._boton_accion(pie, "Exportar PDF", lambda: self.exportar_ticket_pdf(pedido, ventana), "principal").pack(side="right")

    def exportar_ticket_pdf(self, pedido, parent=None):
        try:
            ruta = generar_ticket_pdf(pedido)
        except Exception as error:
            messagebox.showerror("Ticket PDF", f"No se pudo generar el ticket:\n{error}", parent=parent or self)
            return

        self._set_status(f"Ticket PDF generado: {ruta}.")
        messagebox.showinfo("Ticket PDF", f"Ticket generado en:\n{ruta}", parent=parent or self)

    def exportar_ticket_desde_tabla(self, tabla):
        pedido = self._pedido_desde_tabla(tabla)
        if pedido is not None:
            self.exportar_ticket_pdf(pedido)

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

        self._set_status(f"Pedido #{pedido.pedido_id} ahora está {estado_visible(pedido.estado)}.")
        self._refrescar_vista_actual()

    def cancelar_pedido_desde_tabla(self, tabla):
        pedido = self._pedido_desde_tabla(tabla)
        if pedido is None:
            return

        if not messagebox.askyesno("Cancelar pedido", f"¿Cancelar el pedido #{pedido.pedido_id}?"):
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
        if not self._requiere_admin("guardar respaldos"):
            return

        self._sincronizar_ventas_entregadas()
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
        if not self._requiere_admin("cargar respaldos"):
            return

        if not messagebox.askyesno("Cargar respaldo", "Esto reemplazará los datos actuales. ¿Deseas continuar?"):
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
        if not self._requiere_admin("consultar herramientas administrativas"):
            return

        self._set_status("Consultando proveedor externo...")

        def worker():
            # La consulta externa va en un hilo para que la interfaz no se congele.
            # self.after devuelve el resultado al hilo principal de Tkinter.
            try:
                from src.servicios.proveedores import consultar_dolar_oficial

                valor = consultar_dolar_oficial()
                self.after(0, lambda: self._mostrar_dolar(valor, None))
            except Exception as error:
                self.after(0, lambda: self._mostrar_dolar(None, error))

        threading.Thread(target=worker, daemon=True).start()

    def _mostrar_dolar(self, valor, error):
        if error:
            self._set_status(f"No se pudo consultar el dólar: {error}")
            messagebox.showerror("Proveedor externo", str(error))
            return

        self.dolar_text.set(formato_moneda(valor))
        self._set_status(f"Dólar oficial de venta: {formato_moneda(valor)}.")
        messagebox.showinfo("Proveedor externo", f"Dólar oficial de venta: {formato_moneda(valor)}")

    def generar_reportes(self):
        if not self._requiere_admin("generar reportes"):
            return

        try:
            ruta_ventas, ruta_stock = self._generar_archivos_reportes()
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
        if self._es_administrador() and messagebox.askyesno("Salir", "¿Deseas guardar un respaldo antes de salir?"):
            self.guardar_respaldo()
        self.destroy()


def ejecutar_menu():
    app = PizzeriaApp()
    if app.winfo_exists():
        app.mainloop()
