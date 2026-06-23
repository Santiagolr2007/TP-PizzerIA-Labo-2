from datetime import datetime

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

    def calcular_total(self):
        total = 0
        for producto, cantidad in self.productos:
            total += producto.calcular_precio() * cantidad
        return total

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

    def _normalizar_estado(self, estado):
        texto = validar_texto(estado, "estado").strip().lower()
        equivalencias = {
            "en preparacion": "en preparacion",
            "en preparaciÃ³n": "en preparacion",
            "en preparación": "en preparacion",
        }
        return equivalencias.get(texto, texto)

    def generar_items_venta(self):
        items_venta = []
        for producto, cantidad in self.productos:
            precio_unitario = producto.calcular_precio()
            subtotal = precio_unitario * cantidad
            items_venta.append(
                {
                    "pedido_id": self.pedido_id,
                    "fecha": self.fecha.isoformat(),
                    "cliente": self.cliente,
                    "tipo_entrega": self.tipo_entrega,
                    "direccion": self.direccion,
                    "producto": producto.nombre,
                    "cantidad": cantidad,
                    "precio_unitario": precio_unitario,
                    "subtotal": subtotal,
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
            "total": self.calcular_total(),
            "productos": productos_convertidos,
        }
