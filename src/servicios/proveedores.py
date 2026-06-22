import requests
from src.utils.decoradores import reintentar, registrar_log
from src.utils.excepciones import ProveedorNoDisponibleError


@registrar_log
@reintentar(intentos=3,espera=1,excepciones=(requests.RequestException, ProveedorNoDisponibleError),) #reintenta 3 veces usando el decorador
def consultar_dolar_oficial():
    url = "https://dolarapi.com/v1/dolares/oficial"
    respuesta = requests.get(url, timeout=3) #consulta la url

    if respuesta.status_code == 404:
        raise ProveedorNoDisponibleError("El recurso solicitado no existe.")

    if respuesta.status_code >= 500:
        raise ProveedorNoDisponibleError("El servidor externo no está disponible.")

    respuesta.raise_for_status()
    datos = respuesta.json()

    valor_venta = datos.get("venta") #Tomamos el precio del dolar oficial a la venta
    if valor_venta is None:
        raise ProveedorNoDisponibleError("La respuesta no contiene el valor de venta.")

    return float(valor_venta)
