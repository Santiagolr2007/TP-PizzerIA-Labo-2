import threading

from src.modelos.pedido import Pedido
from src.modelos.producto import Bebida, Empanada, Pizza
from src.utils.decoradores import registrar_log
from src.utils.excepciones import PedidoInvalidoError, ProductoNoEncontradoError


class Pizzeria:
    def __init__(self, inventario, dinero_inicial=0):
        # Pizzeria concentra el estado principal del negocio:
        # inventario, catalogo de productos, pedidos, ventas y dinero disponible.
        self.inventario = inventario
        self.__catalogo = {}
        self.__pedidos = []
        self.__ventas = []
        # Las ventas pueden registrarse desde acciones de interfaz o hilos,
        # por eso se protege la lista con un Lock.
        self.__candado_ventas = threading.Lock()
        self.__dinero = dinero_inicial

    def reponer_stock(self, ingrediente, cantidad):
        # Reponer stock tiene impacto en dos partes: baja dinero de caja
        # y aumenta la cantidad del ingrediente en el inventario.
        costo_total = self.inventario.calcular_costo_reposicion(ingrediente, cantidad)
        self.restar_dinero(costo_total)
        self.inventario.reponer(ingrediente, cantidad)
        return costo_total

    def restar_dinero(self, monto):
        if monto < 0:
            raise ValueError("No se puede restar un monto negativo.")

        if monto > self.__dinero:
            raise ValueError(f"No hay dinero suficiente. Disponible: ${self.__dinero:.2f}, costo: ${monto:.2f}")

        self.__dinero -= monto

    def sumar_dinero(self, monto):
        if monto < 0:
            raise ValueError("No se puede sumar un monto negativo.")
        self.__dinero += monto

    def obtener_dinero(self):
        return self.__dinero

    def registrar_producto(self, producto):
        # El nombre funciona como clave del catalogo.
        # Por eso no se permite repetirlo.
        if producto.nombre in self.__catalogo:
            raise ValueError(f"Ya existe un producto llamado '{producto.nombre}'.")
        self.__catalogo[producto.nombre] = producto

    def guardar_producto(self, producto, nombre_original=None):
        # Si nombre_original es None, se esta creando un producto nuevo.
        # Si trae valor, se esta editando un producto ya existente.
        nombre_producto = producto.nombre

        if nombre_original is None:
            if nombre_producto in self.__catalogo:
                raise ValueError(f"Ya existe un producto llamado '{nombre_producto}'.")
            self.__catalogo[nombre_producto] = producto
            return producto

        if nombre_original not in self.__catalogo:
            raise ProductoNoEncontradoError(f"No existe el producto '{nombre_original}'.")

        # Evita cambiar productos que ya aparecen en pedidos guardados.
        # Asi los tickets y ventas historicas no quedan inconsistentes.
        if self.producto_en_uso(nombre_original):
            raise ValueError("No se puede editar un producto que ya fue usado en pedidos.")

        if nombre_producto != nombre_original and nombre_producto in self.__catalogo:
            raise ValueError(f"Ya existe un producto llamado '{nombre_producto}'.")

        if nombre_producto != nombre_original:
            del self.__catalogo[nombre_original]

        self.__catalogo[nombre_producto] = producto
        return producto

    def eliminar_producto(self, nombre_producto):
        if nombre_producto not in self.__catalogo:
            raise ProductoNoEncontradoError(f"No existe el producto '{nombre_producto}'.")

        if self.producto_en_uso(nombre_producto):
            raise ValueError("No se puede eliminar un producto que ya fue usado en pedidos.")

        del self.__catalogo[nombre_producto]

    def producto_en_uso(self, nombre_producto):
        # Recorre todos los pedidos para saber si un producto ya fue vendido o cargado.
        for pedido in self.__pedidos:
            for producto, _cantidad in pedido.productos:
                if producto.nombre == nombre_producto:
                    return True
        return False

    def obtener_producto(self, nombre_producto):
        if nombre_producto not in self.__catalogo:
            raise ProductoNoEncontradoError(f"No existe el producto '{nombre_producto}'.")
        return self.__catalogo[nombre_producto]

    def obtener_catalogo(self):
        return list(self.__catalogo.values())

    def catalogo_to_dict(self):
        # Convierte objetos Pizza/Empanada/Bebida a diccionarios simples
        # para poder guardarlos en JSON.
        productos = []
        for producto in self.obtener_catalogo():
            productos.append(self._producto_to_dict(producto))
        return productos

    def _producto_to_dict(self, producto):
        # Todos los productos comparten nombre, precio y tipo.
        # Despues se agregan campos propios segun la subclase.
        datos = {
            "nombre": producto.nombre,
            "precio_base": producto.precio_base,
            "tipo": producto.__class__.__name__,
        }

        if isinstance(producto, Pizza):
            datos["tamanio"] = producto.tamanio
            datos["ingredientes_extra"] = dict(producto.ingredientes_extra)
        elif isinstance(producto, Empanada):
            datos["ingrediente_relleno"] = producto.ingrediente_relleno
        elif isinstance(producto, Bebida):
            datos["ingrediente_stock"] = producto.ingrediente_stock

        return datos

    def _producto_desde_dict(self, datos):
        # Reconstruye objetos reales del catalogo desde el JSON del respaldo.
        tipo = datos.get("tipo", "")
        nombre = datos["nombre"]
        precio_base = datos["precio_base"]

        if tipo == "Pizza":
            return Pizza(nombre, precio_base, datos.get("tamanio", "grande"), datos.get("ingredientes_extra", {}))

        if tipo == "Empanada":
            return Empanada(nombre, precio_base, datos.get("ingrediente_relleno", "carne"))

        if tipo == "Bebida":
            return Bebida(nombre, precio_base, datos.get("ingrediente_stock"))

        raise ValueError(f"Tipo de producto invalido: {tipo}")

    def reemplazar_catalogo(self, productos):
        # Se usa al cargar respaldo: arma un catalogo nuevo y recien al final
        # reemplaza el anterior, evitando dejar el sistema a medio cargar.
        catalogo = {}
        for datos_producto in productos:
            producto = self._producto_desde_dict(datos_producto)
            if producto.nombre in catalogo:
                raise ValueError(f"El catalogo contiene un producto repetido: {producto.nombre}.")
            catalogo[producto.nombre] = producto
        self.__catalogo = catalogo

    @registrar_log
    def crear_pedido(self, cliente, items, tipo_entrega="Retiro", direccion=""):
        # items llega como pares [nombre_producto, cantidad] desde la interfaz.
        # Aca se traduce cada nombre al objeto real del catalogo.
        if len(items) == 0:
            raise PedidoInvalidoError("Debe agregar al menos un producto.")

        pedido = Pedido(cliente, tipo_entrega, direccion)

        for nombre_producto, cantidad in items:
            if nombre_producto not in self.__catalogo:
                raise ProductoNoEncontradoError(f"No existe el producto '{nombre_producto}'.")

            pedido.agregar_producto(self.__catalogo[nombre_producto], cantidad)

        self.__pedidos.append(pedido)
        return pedido

    def obtener_pedidos(self):
        return list(self.__pedidos)

    def obtener_pedido_por_id(self, pedido_id):
        # Los Treeview muestran el ID del pedido; este metodo vuelve desde ese ID
        # al objeto Pedido para avanzar, cancelar o abrir ticket.
        for pedido in self.__pedidos:
            if pedido.pedido_id == int(pedido_id):
                return pedido
        raise PedidoInvalidoError(f"No existe el pedido #{pedido_id}.")

    def obtener_pedidos_pendientes(self):
        pedidos_pendientes = []
        for pedido in self.__pedidos:
            if pedido.estado == "pendiente":
                pedidos_pendientes.append(pedido)
        return pedidos_pendientes

    def avanzar_pedido(self, pedido_id):
        pedido = self.obtener_pedido_por_id(pedido_id)

        # Retiro se entrega al estar listo; delivery primero pasa a "en camino".
        # Solo cuando llega a "entregado" se registra la venta.
        if pedido.estado == "listo":
            nuevo_estado = "en camino" if pedido.tipo_entrega == "Delivery" else "entregado"
        elif pedido.estado == "en camino":
            nuevo_estado = "entregado"
        else:
            raise PedidoInvalidoError("Solo se pueden avanzar pedidos listos o en camino.")

        pedido.cambiar_estado(nuevo_estado)
        if pedido.estado == "entregado":
            self.registrar_venta(pedido)

        return pedido

    def cancelar_pedido(self, pedido_id):
        pedido = self.obtener_pedido_por_id(pedido_id)
        pedido.cambiar_estado("cancelado")
        return pedido

    @registrar_log
    def registrar_venta(self, pedido):
        # El candado evita duplicados si dos acciones intentan registrar el mismo pedido.
        with self.__candado_ventas:
            if self._venta_registrada(pedido.pedido_id):
                return False

            for item_venta in pedido.generar_items_venta():
                self.__ventas.append(item_venta)

        self.sumar_dinero(pedido.calcular_total())
        return True

    def sincronizar_ventas_entregadas(self):
        # Repara casos donde un pedido ya figura como entregado, pero aun no existe
        # en la lista de ventas que usan reportes, caja y respaldos.
        ventas_agregadas = 0

        for pedido in self.__pedidos:
            if pedido.estado != "entregado":
                continue
            if self.registrar_venta(pedido):
                ventas_agregadas += 1

        return ventas_agregadas

    def _venta_registrada(self, pedido_id):
        for venta in self.__ventas:
            if int(venta.get("pedido_id", 0)) == int(pedido_id):
                return True
        return False

    @registrar_log
    def cargar_datos(self, datos):
        # Restaura el estado completo desde un respaldo JSON:
        # dinero, catalogo, stock, pedidos y ventas.
        self.__dinero = datos.get("dinero", self.__dinero)

        if "catalogo" in datos:
            self.reemplazar_catalogo(datos["catalogo"])

        self.inventario.reemplazar_stock(datos["stock"])
        pedidos_cargados = []
        mayor_id = 0

        for datos_pedido in datos["pedidos"]:
            pedido = Pedido.desde_dict(datos_pedido, self.__catalogo)
            pedidos_cargados.append(pedido)
            if pedido.pedido_id > mayor_id:
                mayor_id = pedido.pedido_id

        # El contador global de Pedido debe continuar desde el mayor ID guardado
        # para que los nuevos pedidos no repitan numeros.
        self.__pedidos = pedidos_cargados
        Pedido._contador = mayor_id

        with self.__candado_ventas:
            self.__ventas = []
            for venta in datos["ventas"]:
                self.__ventas.append(venta)

    def obtener_ventas(self):
        with self.__candado_ventas:
            return list(self.__ventas)
