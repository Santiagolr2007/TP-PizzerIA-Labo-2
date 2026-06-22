from datetime import datetime
from src.utils.excepciones import (EstadoPedidoError,PedidoInvalidoError,ProductoNoEncontradoError)
from src.utils.validaciones import validar_entero_positivo, validar_texto


class Pedido:
    _contador = 0  # Contador compartido para asignar un ID único a cada pedido.
    def __init__(self, cliente):
        Pedido._contador += 1
        self.pedido_id = Pedido._contador
        self.cliente = validar_texto(cliente, "cliente")
        self.productos = []
        self.__estado = "pendiente"
        self.fecha = datetime.now()


    @property
    def estado(self):
        # Permite consultar el estado sin acceder directamente al atributo privado.
        return self.__estado


    def agregar_producto(self, producto, cantidad):
        # Valida que la cantidad sea un número entero mayor que cero.
        cantidad_validada = validar_entero_positivo(cantidad,"cantidad")
        # Guarda el producto y su cantidad dentro de una tupla.
        self.productos.append((producto, cantidad_validada))


    def calcular_total(self):
        total = 0
        # Recorre los productos del pedido y acumula cada subtotal.
        for producto, cantidad in self.productos:
            precio_unitario = producto.calcular_precio()
            subtotal = precio_unitario * cantidad
            total += subtotal

        return total


    def obtener_ingredientes_totales(self):
        # Evita calcular ingredientes si el pedido está vacío.
        if not self.productos:
            raise PedidoInvalidoError("El pedido no contiene productos.")

        ingredientes = {}

        # Recorre cada producto y obtiene los ingredientes necesarios.
        for producto, cantidad in self.productos:
            necesarios = producto.ingredientes_necesarios(cantidad)

            # Suma las cantidades de ingredientes que se repiten.
            for nombre, unidades in necesarios.items():
                cantidad_actual = ingredientes.get(nombre,0)
                ingredientes[nombre] = (cantidad_actual + unidades)

        return ingredientes


    def cambiar_estado(self, nuevo_estado):
        # Define los cambios de estado permitidos.
        transiciones = {
            "pendiente": {"en preparación","cancelado"}, #De pendiente se puede pasar a en preparación o cancelado.
            "en preparación": {"entregado","cancelado"}, #De en preparación se puede pasar a entregado o cancelado.
            "entregado": set(), #Simboliza la nada
            "cancelado": set()} #Simboliza la nada

        # Devuelve los estados permitidos para el estado actual del pedido. Si el estado actual no está en el diccionario, devuelve un conjunto vacío.
        estados_permitidos = transiciones.get(self.__estado,set())

        # Impide realizar una transición que no esté permitida.
        if nuevo_estado not in estados_permitidos:
            raise EstadoPedidoError(f"No se puede pasar de '{self.__estado}' a '{nuevo_estado}'.")
        self.__estado = nuevo_estado


    def generar_items_venta(self):
        items_venta = []
        # Genera un registro de venta por cada producto del pedido.
        for producto, cantidad in self.productos:
            precio_unitario = producto.calcular_precio()
            subtotal = precio_unitario * cantidad

            item_venta = {
                "pedido_id": self.pedido_id,
                "fecha": self.fecha.isoformat(),
                "cliente": self.cliente,
                "producto": producto.nombre,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "subtotal": subtotal
            }

            items_venta.append(item_venta)

        return items_venta

    @classmethod
    def desde_dict(cls, datos, catalogo):
        # Crea un pedido nuevo usando el cliente guardado.
        pedido = cls(datos["cliente"])
        # Recupera el ID original del pedido.
        pedido.pedido_id = int(datos["pedido_id"])
        # Recupera el estado guardado.
        estado_guardado = datos["estado"]
        estados_validos = ["pendiente","en preparación","entregado","cancelado"]

        # Verifica que el estado del archivo sea válido.
        if estado_guardado not in estados_validos:
            raise PedidoInvalidoError(f"El estado '{estado_guardado}' no es válido.")

        pedido.__estado = estado_guardado

        # Convierte la fecha guardada nuevamente en un objeto datetime.
        pedido.fecha = datetime.fromisoformat(datos["fecha"])

        # Vacía la lista porque los productos se reconstruyen desde el JSON.
        pedido.productos = []

        # Recorre los productos guardados.
        for producto_guardado in datos["productos"]:
            nombre_producto = producto_guardado["nombre"]
            cantidad = producto_guardado["cantidad"]

            # Verifica que el producto todavía exista en el catálogo.
            if nombre_producto not in catalogo:
                raise ProductoNoEncontradoError(f"No existe el producto guardado '{nombre_producto}'.")

            producto = catalogo[nombre_producto]

            # Vuelve a agregar el objeto Producto al pedido.
            pedido.agregar_producto(producto, cantidad)
        return pedido


    def to_dict(self):
        productos_convertidos = []

        # Convierte cada producto del pedido en un diccionario.
        for producto, cantidad in self.productos:
            producto_convertido = {"nombre": producto.nombre,"cantidad": cantidad}
            productos_convertidos.append(producto_convertido)

        pedido_convertido = {
            "pedido_id": self.pedido_id,
            "cliente": self.cliente,
            "estado": self.estado,
            "fecha": self.fecha.isoformat(),
            "total": self.calcular_total(),
            "productos": productos_convertidos
        }

        return pedido_convertido
