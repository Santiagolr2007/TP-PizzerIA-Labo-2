#Podemos buscar cualquier tipo de error buscando solo esta clase
class PizzerIAError(Exception): #Excepción base del proyecto.
    pass

class StockInsuficienteError(PizzerIAError):
    pass

class PedidoInvalidoError(PizzerIAError):
    pass

class ProductoNoEncontradoError(PizzerIAError):
    pass

class EstadoPedidoError(PizzerIAError):
    pass

class ProveedorNoDisponibleError(PizzerIAError):
    pass