import threading
from src.utils.excepciones import StockInsuficienteError
from src.utils.validaciones import validar_entero_positivo


class Inventario:

    def __init__(self, stock_inicial=None):

        # Si no se recibe un stock inicial, crea un diccionario vacío.
        if stock_inicial is None:
            self.__stock = {}
        else:
            self.__stock = dict(stock_inicial)

        # El candado evita que dos hilos modifiquen el stock exactamente al mismo tiempo.
        self.__candado = threading.Lock()

#########

    def obtener_stock(self):

        # Solo un hilo puede acceder a esta sección a la vez.
        with self.__candado:
            # Devuelve una copia para evitar que se modifique el diccionario original desde afuera de la clase.
            copia_stock = self.__stock.copy()
        return copia_stock
    
#########

    def reemplazar_stock(self, nuevo_stock):

        # Bloquea el inventario mientras reemplaza todos sus datos.
        with self.__candado:
            self.__stock = dict(nuevo_stock)


########

    def reponer(self, ingrediente, cantidad):

        # Valida que la cantidad sea un número entero mayor que cero.
        cantidad_validada = validar_entero_positivo(cantidad,"cantidad")

        with self.__candado:

            # Si el ingrediente ya existe, obtiene su cantidad. Si no existe, comienza desde cero.
            cantidad_actual = self.__stock.get(ingrediente, 0)
            nueva_cantidad = cantidad_actual + cantidad_validada
            self.__stock[ingrediente] = nueva_cantidad

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