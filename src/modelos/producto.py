from abc import ABC, abstractmethod
from src.utils.validaciones import validar_precio, validar_texto


# Producto es una clase abstracta. Sirve como clase padre para Pizza, Empanada y Bebida.
class Producto(ABC):

    def __init__(self, nombre, precio_base):
        # Validamos que el nombre no esté vacío.
        self.nombre = validar_texto(nombre, "nombre")
        # El precio debe consultarse mediante la propiedad precio_base. y _precio_base es un atributo protegido.
        self._precio_base = validar_precio(precio_base)


    @property
    def precio_base(self):
        
        # Permite consultar el precio base del producto sin acceder directamente al atributo protegido.
        
        return self._precio_base


    @abstractmethod #abstracto para que se aplique obligatoriamente en las subclases.
    def calcular_precio(self):
        pass


    @abstractmethod #abstracto para que se aplique obligatoriamente en las subclases.
    def ingredientes_necesarios(self, cantidad=1):
        pass


# Pizza hereda los atributos y métodos de Producto.
class Pizza(Producto):

    def __init__(self, nombre, precio_base, tamanio):

        # Llama al constructor de Producto para guardar y validar el nombre y el precio base.
        super().__init__(nombre, precio_base) #Repite las validaciones de nombre y precio base de la clase producto.

        # Validamos el tamaño y lo convertimos a minúsculas.
        self.tamanio = validar_texto(tamanio,"tamaño").lower()


    def calcular_precio(self):
        #Calcula el precio final según el tamaño de la pizza.

        if self.tamanio == "chica":
            factor_aumento = 1.0

        # La pizza mediana tiene un aumento del 20 %.
        elif self.tamanio == "mediana":
            factor_aumento = 1.2

        # La pizza grande tiene un aumento del 40 %.
        elif self.tamanio == "grande":
            factor_aumento = 1.4

        # Si se recibe otro tamaño, mantiene el precio base.
        else:
            factor_aumento = 1.0

        precio_final = self.precio_base * factor_aumento
        return precio_final


    def ingredientes_necesarios(self, cantidad=1):
        #Devuelve un diccionario con los ingredientes necesarios para preparar la cantidad solicitada de pizzas.

        # Una pizza grande utiliza el doble de ingredientes.
        if self.tamanio == "grande":
            factor_ingredientes = 2
        else:
            factor_ingredientes = 1

        cantidad_harina = 1 * cantidad * factor_ingredientes
        cantidad_salsa = 1 * cantidad * factor_ingredientes
        cantidad_mozzarella = 2 * cantidad * factor_ingredientes

        ingredientes = {"harina": cantidad_harina,"salsa": cantidad_salsa,"mozzarella": cantidad_mozzarella}
        return ingredientes


# Empanada también hereda de Producto.
class Empanada(Producto):

    def calcular_precio(self):
        # Las empanadas no tienen aumento según tamaño, por lo que se devuelve directamente el precio base.
        return self.precio_base


    def ingredientes_necesarios(self, cantidad=1):
        #Cada empanada necesita una tapa y una unidad de relleno.
        ingredientes = {"tapas_empanada": cantidad,"relleno_empanada": cantidad}
        return ingredientes


# Bebida también hereda de Producto.
class Bebida(Producto):

    def calcular_precio(self):
        #La bebida mantiene su precio base.
        return self.precio_base


    def ingredientes_necesarios(self, cantidad=1):
        #En el inventario, cada bebida se representacomo una unidad de gaseosa.
        ingredientes = {"gaseosa": cantidad}
        return ingredientes