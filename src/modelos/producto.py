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

    def __init__(self, nombre, precio_base, tamanio, ingredientes_extra=None):
        # Llama al constructor de Producto para guardar y validar el nombre y el precio base.
        super().__init__(nombre, precio_base) #Repite las validaciones de nombre y precio base de la clase producto.
        # Validamos el tamaño y lo convertimos a minúsculas.
        self.tamanio = validar_texto(tamanio,"tamaño").lower()

        # Guarda los ingredientes extra de cada tipo de pizza.
        if ingredientes_extra is None:
            self.ingredientes_extra = {}
        else:
            self.ingredientes_extra = dict(ingredientes_extra)


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

        # Todas las pizzas tienen estos ingredientes base.
        ingredientes = {"harina": cantidad_harina,"salsa": cantidad_salsa,"mozzarella": cantidad_mozzarella}

        # Agrega los ingredientes extra de cada variedad de pizza.
        for ingrediente, unidades in self.ingredientes_extra.items():
            cantidad_actual = ingredientes.get(ingrediente, 0)
            ingredientes[ingrediente] = cantidad_actual + unidades * cantidad * factor_ingredientes

        return ingredientes


# Empanada también hereda de Producto.
class Empanada(Producto):

    def __init__(self, nombre, precio_base, ingrediente_relleno):
        # Llama al constructor de Producto para guardar y validar el nombre y el precio base.
        super().__init__(nombre, precio_base)
        # Guarda el ingrediente principal del relleno.
        self.ingrediente_relleno = validar_texto(ingrediente_relleno, "ingrediente_relleno").lower()


    def calcular_precio(self):
        # Las empanadas no tienen aumento según tamaño, por lo que se devuelve directamente el precio base.
        return self.precio_base


    def ingredientes_necesarios(self, cantidad=1):
        #Cada empanada necesita una tapa y una unidad de relleno.
        ingredientes = {"tapas_empanada": cantidad,self.ingrediente_relleno: cantidad}
        return ingredientes


# Bebida también hereda de Producto.
class Bebida(Producto):

    def __init__(self, nombre, precio_base, ingrediente_stock=None):
        # Llama al constructor de Producto para guardar y validar el nombre y el precio base.
        super().__init__(nombre, precio_base)
        # Se guarda el dato por si se quiere controlar stock de bebidas más adelante.
        self.ingrediente_stock = ingrediente_stock


    def calcular_precio(self):
        #La bebida mantiene su precio base.
        return self.precio_base


    def ingredientes_necesarios(self, cantidad=1):
        #Las bebidas no tienen ingredientes de preparación.
        ingredientes = {}
        return ingredientes