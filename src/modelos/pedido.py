from datetime import datetime

from src.servicios.promociones import calcular_descuentos_por_linea, calcular_promociones_pedido
from src.utils.excepciones import EstadoPedidoError, PedidoInvalidoError, ProductoNoEncontradoError
from src.utils.validaciones import validar_entero_positivo, validar_texto


class Pedido:
    _contador = 0

    def __init__(self, cliente, tipo_entrega="Retiro", direccion=""):
        Pedido._contador += 1
        self.pedido_id = Pedido._contador
        self.cliente = validar_texto(cliente, "cliente")
        self.tipo_entrega = self._validar_tipo_entrega(tipo_entrega)
        self.direccion = self._validar_direccion(direccion)
        self.productos = []
        self.__estado = "pendiente"
        self.fecha = datetime.now()
        self.cocinero_asignado = ""
        self.estacion_cocina = ""
        self.tiempo_estimado = 0
        self.tiempo_restante = 0
        self.inicio_preparacion = ""
        self.fin_preparacion = ""
        self.motivo_cancelacion = ""

    @property
    def estado(self):
        return self.__estado

    def _validar_tipo_entrega(self, tipo_entrega):
        texto = validar_texto(tipo_entrega, "tipo de entrega").strip().lower()
        if texto == "delivery":
            return "Delivery"
        if texto in {"retiro", "retiro en local"}:
            return "Retiro"
        raise ValueError("El tipo de entrega debe ser Retiro o Delivery.")

    def _validar_direccion(self, direccion):
        texto = str(direccion).strip()
        if self.tipo_entrega == "Delivery" and not texto:
            raise ValueError("La direccion es obligatoria para pedidos con delivery.")
        return texto

    def agregar_producto(self, producto, cantidad):
        cantidad_validada = validar_entero_positivo(cantidad, "cantidad")
        self.productos.append((producto, cantidad_validada))

    def calcular_subtotal(self):
        total = 0
        for producto, cantidad in self.productos:
            total += producto.calcular_precio() * cantidad
        return total

    def obtener_promociones(self):
        return calcular_promociones_pedido(self.productos)

    def calcular_descuento_total(self):
        descuento_total = 0
        for promocion in self.obtener_promociones():
            descuento_total += promocion["descuento"]
        return descuento_total

    def calcular_total(self):
        total = self.calcular_subtotal() - self.calcular_descuento_total()
        return max(0, total)

    def iterar_lineas_detalle(self):
        # El detalle se calcula linea por linea para que ventas, tickets y reportes
        # usen exactamente los mismos subtotales y descuentos.
        descuentos_por_linea = calcular_descuentos_por_linea(self.productos)

        for indice, (producto, cantidad) in enumerate(self.productos):
            precio_unitario = producto.calcular_precio()
            subtotal_bruto = precio_unitario * cantidad
            descuento = descuentos_por_linea.get(indice, 0)

            yield {
                "producto": producto,
                "nombre": producto.nombre,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "subtotal_bruto": subtotal_bruto,
                "descuento": descuento,
                "subtotal": subtotal_bruto - descuento,
            }

    def obtener_ingredientes_totales(self):
        if not self.productos:
            raise PedidoInvalidoError("El pedido no contiene productos.")

        ingredientes = {}
        for producto, cantidad in self.productos:
            necesarios = producto.ingredientes_necesarios(cantidad)
            for nombre, unidades in necesarios.items():
                ingredientes[nombre] = ingredientes.get(nombre, 0) + unidades

        return ingredientes

    def cambiar_estado(self, nuevo_estado):
        estado_normalizado = self._normalizar_estado(nuevo_estado)
        transiciones = {
            "pendiente": {"en preparacion", "cancelado"},
            "en preparacion": {"listo", "cancelado"},
            "listo": {"en camino", "entregado", "cancelado"},
            "en camino": {"entregado", "cancelado"},
            "entregado": set(),
            "cancelado": set(),
        }
        estados_permitidos = transiciones.get(self.__estado, set())

        if estado_normalizado not in estados_permitidos:
            raise EstadoPedidoError(f"No se puede pasar de '{self.__estado}' a '{estado_normalizado}'.")

        self.__estado = estado_normalizado

    def asignar_cocina(self, cocinero, estacion, tiempo_estimado):
        self.cocinero_asignado = validar_texto(cocinero, "cocinero")
        self.estacion_cocina = validar_texto(estacion, "estacion")
        self.tiempo_estimado = int(tiempo_estimado)
        self.tiempo_restante = int(tiempo_estimado)
        self.inicio_preparacion = datetime.now().isoformat()

    def actualizar_tiempo_restante(self, tiempo_restante):
        self.tiempo_restante = max(0, int(tiempo_restante))

    def finalizar_cocina(self):
        self.tiempo_restante = 0
        self.fin_preparacion = datetime.now().isoformat()

    def registrar_cancelacion(self, motivo):
        self.motivo_cancelacion = str(motivo)

    def _normalizar_estado(self, estado):
        texto = validar_texto(estado, "estado").strip().lower()
        equivalencias = {
            "en preparacion": "en preparacion",
            "en preparación": "en preparacion",
        }
        return equivalencias.get(texto, texto)

    def generar_items_venta(self):
        # Convierte un pedido entregado en filas de venta independientes.
        # Luego el reporte de Excel vuelve a agruparlas por pedido.
        items_venta = []
        for linea in self.iterar_lineas_detalle():
            items_venta.append(
                {
                    "pedido_id": self.pedido_id,
                    "fecha": self.fecha.isoformat(),
                    "cliente": self.cliente,
                    "tipo_entrega": self.tipo_entrega,
                    "direccion": self.direccion,
                    "producto": linea["nombre"],
                    "cantidad": linea["cantidad"],
                    "precio_unitario": linea["precio_unitario"],
                    "subtotal_bruto": linea["subtotal_bruto"],
                    "descuento": linea["descuento"],
                    "subtotal": linea["subtotal"],
                }
            )

        return items_venta

    @classmethod
    def desde_dict(cls, datos, catalogo):
        pedido = cls(
            datos["cliente"],
            datos.get("tipo_entrega", "Retiro"),
            datos.get("direccion", ""),
        )
        pedido.pedido_id = int(datos["pedido_id"])
        estado_guardado = pedido._normalizar_estado(datos["estado"])
        estados_validos = ["pendiente", "en preparacion", "listo", "en camino", "entregado", "cancelado"]

        if estado_guardado not in estados_validos:
            raise PedidoInvalidoError(f"El estado '{estado_guardado}' no es valido.")

        pedido.__estado = estado_guardado
        pedido.fecha = datetime.fromisoformat(datos["fecha"])
        pedido.productos = []
        pedido.cocinero_asignado = datos.get("cocinero_asignado", "")
        pedido.estacion_cocina = datos.get("estacion_cocina", "")
        pedido.tiempo_estimado = int(datos.get("tiempo_estimado", 0) or 0)
        pedido.tiempo_restante = int(datos.get("tiempo_restante", 0) or 0)
        pedido.inicio_preparacion = datos.get("inicio_preparacion", "")
        pedido.fin_preparacion = datos.get("fin_preparacion", "")
        pedido.motivo_cancelacion = datos.get("motivo_cancelacion", "")

        for producto_guardado in datos["productos"]:
            nombre_producto = producto_guardado["nombre"]
            cantidad = producto_guardado["cantidad"]

            if nombre_producto not in catalogo:
                raise ProductoNoEncontradoError(f"No existe el producto guardado '{nombre_producto}'.")

            pedido.agregar_producto(catalogo[nombre_producto], cantidad)

        return pedido

    def to_dict(self):
        productos_convertidos = []
        for producto, cantidad in self.productos:
            productos_convertidos.append({"nombre": producto.nombre, "cantidad": cantidad})

        return {
            "pedido_id": self.pedido_id,
            "cliente": self.cliente,
            "estado": self.estado,
            "tipo_entrega": self.tipo_entrega,
            "direccion": self.direccion,
            "fecha": self.fecha.isoformat(),
            "subtotal": self.calcular_subtotal(),
            "descuento": self.calcular_descuento_total(),
            "total": self.calcular_total(),
            "cocinero_asignado": self.cocinero_asignado,
            "estacion_cocina": self.estacion_cocina,
            "tiempo_estimado": self.tiempo_estimado,
            "tiempo_restante": self.tiempo_restante,
            "inicio_preparacion": self.inicio_preparacion,
            "fin_preparacion": self.fin_preparacion,
            "motivo_cancelacion": self.motivo_cancelacion,
            "productos": productos_convertidos,
        }
