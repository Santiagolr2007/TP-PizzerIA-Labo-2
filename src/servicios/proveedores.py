import requests
from src.utils.decoradores_v2 import reintentar, registrar_log
"""from src.utils.excepciones import ProveedorNoDisponibleError"""


@registrar_log
@reintentar(intentos=3,espera=1,excepciones=(requests.RequestException, ProveedorNoDisponibleError),)
def consultar_dolar_oficial():
    url = "https://dolarapi.com/v1/dolares/oficial"
    respuesta = requests.get(url, timeout=3)

    if respuesta.status_code == 404:
        raise ProveedorNoDisponibleError("El recurso solicitado no existe.")

    if respuesta.status_code >= 500:
        raise ProveedorNoDisponibleError("El servidor externo no está disponible.")

    respuesta.raise_for_status()
    datos = respuesta.json()

    valor_venta = datos.get("venta")
    if valor_venta is None:
        raise ProveedorNoDisponibleError("La respuesta no contiene el valor de venta.")

    return float(valor_venta)
