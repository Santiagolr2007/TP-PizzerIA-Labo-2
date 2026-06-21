import threading
from src.utils.excepciones import StockInsuficienteError
from src.utils.validaciones import validar_entero_positivo


class Inventario:

    def __init__(self, stock_inicial=None, precios_stock=None):

        # Crea el stock inicial.
        if stock_inicial is None:
            self.__stock = {}
        else:
            self.__stock = dict(stock_inicial)

        # Crea la lista de precios del stock.
        if precios_stock is None:
            self.__precios_stock = {}
        else:
            self.__precios_stock = dict(precios_stock)

        # Si algún ingrediente no tiene precio, se guarda con precio cero.
        for ingrediente in self.__stock:
            if ingrediente not in self.__precios_stock:
                self.__precios_stock[ingrediente] = 0

        # Protege el stock cuando trabajan varios hilos.
        self.__candado = threading.Lock()

#########

    def reemplazar_stock(self, nuevo_stock):
        # Reemplaza todo el inventario de forma segura.
        with self.__candado:
            self.__stock = dict(nuevo_stock)

            # Mantiene los precios existentes y agrega precio cero si falta alguno.
            for ingrediente in self.__stock:
                if ingrediente not in self.__precios_stock:
                    self.__precios_stock[ingrediente] = 0

#########

    def reponer(self, ingrediente, cantidad):
        # Valida que la cantidad sea un número entero mayor que cero.
        cantidad_validada = validar_entero_positivo(cantidad, "cantidad")

        with self.__candado:
            # Verifica que el ingrediente exista en el inventario.
            if ingrediente not in self.__stock:
                raise ValueError(f"El ingrediente '{ingrediente}' no existe en el stock.")

            cantidad_actual = self.__stock[ingrediente]
            nueva_cantidad = cantidad_actual + cantidad_validada
            self.__stock[ingrediente] = nueva_cantidad

##########

    def obtener_stock_detallado(self):

        # Devuelve el stock con cantidad, precio unitario y valor total.
        with self.__candado:
            stock_detallado = []

            for ingrediente, cantidad in self.__stock.items():
                precio_unitario = self.__precios_stock.get(ingrediente, 0)
                valor_total = cantidad * precio_unitario

                fila = {"ingrediente": ingrediente,"cantidad": cantidad,"precio_unitario": precio_unitario,"valor_total_stock": valor_total}

                stock_detallado.append(fila)

        return stock_detallado
    
#########

    def obtener_stock(self):

        # Solo un hilo puede acceder a esta sección a la vez.
        with self.__candado:
            # Devuelve una copia para evitar que se modifique el diccionario original desde afuera de la clase.
            copia_stock = self.__stock.copy()
        return copia_stock

########

    def obtener_precio_unitario(self, ingrediente):
        # Devuelve el precio unitario de compra de un ingrediente.
        with self.__candado:
            if ingrediente not in self.__stock:
                raise ValueError(f"El ingrediente '{ingrediente}' no existe en el stock.")

            precio_unitario = self.__precios_stock.get(ingrediente, 0)

            if precio_unitario <= 0:
                raise ValueError(f"El ingrediente '{ingrediente}' no tiene precio unitario cargado.")
        return precio_unitario

########

    def calcular_costo_reposicion(self, ingrediente, cantidad):
        # Calcula cuánto cuesta comprar cierta cantidad de un ingrediente.
        cantidad_validada = validar_entero_positivo(cantidad,"cantidad")
        precio_unitario = self.obtener_precio_unitario(ingrediente)
        costo_total = precio_unitario * cantidad_validada
        return costo_total

########

    def descontar(self, ingredientes_necesarios):

        with self.__candado:
            faltantes = {}
            # Primero revisa si hay stock suficiente para todos los ingredientes.
            for ingrediente, cantidad_necesaria in ingredientes_necesarios.items():
                cantidad_disponible = self.__stock.get(ingrediente,0)

                if cantidad_disponible < cantidad_necesaria:
                    faltantes[ingrediente] = cantidad_necesaria


            # Si falta algún ingrediente, arma un mensaje y lanza una excepción.
            if len(faltantes) > 0:
                detalle = ""

                for ingrediente, cantidad_necesaria in faltantes.items():
                    detalle += (f"{ingrediente}: se necesitan {cantidad_necesaria};")

                raise StockInsuficienteError(f"Stock insuficiente: {detalle}")


            # Solo descuenta si hay stock suficiente para todos los ingredientes.
            for ingrediente, cantidad_necesaria in ingredientes_necesarios.items():
                cantidad_actual = self.__stock[ingrediente]
                self.__stock[ingrediente] = (cantidad_actual - cantidad_necesaria)