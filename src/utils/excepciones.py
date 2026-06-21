#Podemos buscar cualquier tipo de error buscando solo esta clase
class PizzeriaError(Exception):
    #Excepción base del proyecto.
    pass

class StockInsuficienteError(PizzeriaError):
    pass

class PedidoInvalidoError(PizzeriaError):
    pass

class ProductoNoEncontradoError(PizzeriaError):
    pass

class EstadoPedidoError(PizzeriaError):
    pass

class ProveedorNoDisponibleError(PizzeriaError):
    pass