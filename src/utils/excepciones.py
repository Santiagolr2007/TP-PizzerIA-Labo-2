#Podemos buscar cualquier tipo de error buscando solo esta clase
class PizzeriaError(Exception):
    #Excepción base del proyecto.
    pass

class StockInsuficienteError(PizzeriaError):
    # Se lanza cuando el inventario no alcanza para preparar un pedido.
    pass

class PedidoInvalidoError(PizzeriaError):
    # Se usa cuando un pedido tiene datos incompletos o cantidades incorrectas.
    pass

class ProductoNoEncontradoError(PizzeriaError):
    # Se usa cuando se intenta operar con un producto que no existe en catalogo.
    pass

class EstadoPedidoError(PizzeriaError):
    # Se lanza cuando se intenta pasar un pedido a un estado no permitido.
    pass

class ProveedorNoDisponibleError(PizzeriaError):
    # Representa fallas del proveedor externo, por ejemplo la API del dolar.
    pass
