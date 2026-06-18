#Podemos buscar cualquier tipo de error buscando solo esta clase
class PizzerIAError(Exception):
    pass

#Avisa y almacena los datos exactos del ingrediente faltante y la cantidad
class StockInsuficienteError(PizzerIAError):
    def __init__(self, producto: str, ingrediente: str, cantidad_faltante: float):
        self.producto = producto
        self.ingrediente = ingrediente
        self.cantidad_faltante = cantidad_faltante
        self.mensaje = f"No hay stock suficiente para [{producto}]. Falta {cantidad_faltante} de '{ingrediente}'."
        super().__init__(self.mensaje)

#Frena el proceso en caso de que el pedido este mal estructurado o vacio
class ValidacionDatosError(PizzerIAError):
    pass
