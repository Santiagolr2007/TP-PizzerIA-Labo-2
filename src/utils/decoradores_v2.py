import os
import time
from pathlib import Path
from functools import wraps
from datetime import datetime
from zoneinfo import ZoneInfo


def registrar_log(funcion):
    @wraps(funcion) #wraps para que la funcion decorada mantenga el nombre y data de la funcion original.
    def envoltura(*args, **kwargs):
        ruta_proyecto = Path(__file__).resolve().parents[2] #sube desde decoradores_v2.py hasta la raíz del proyecto.
        carpeta_logs = ruta_proyecto / "logs"
        carpeta_logs.mkdir(exist_ok=True)
        
        zona_argentina = ZoneInfo("America/Argentina/Buenos_Aires")
        inicio = datetime.now(zona_argentina).strftime("%Y-%m-%d %H:%M:%S") #toma la fecha y hora actual de zona_argentina para incluirla en el mensaje del log
        try:
            resultado = funcion(*args, **kwargs)
            mensaje = f"[{inicio}] OK - {funcion.__name__}\n"
            return resultado
        except Exception as error:
            mensaje = f"[{inicio}] ERROR - {funcion.__name__}: {error}\n"
            raise # Relanza la excepción para que el programa pueda seguir manejándola fuera del decorador.
        finally:
            with open(carpeta_logs / "sistema.log", "a", encoding="utf-8") as archivo:
                archivo.write(mensaje) # "a" de append, agrega el mensaje sin borrar los registros anteriores.
    return envoltura


def medir_tiempo(funcion):
    @wraps(funcion) #wraps para que la funcion decorada mantenga el nombre y data de la funcion original.
    def funcion_decorada(*args, **kwargs):

        tiempo_inicio = time.perf_counter()

        resultado = funcion(*args, **kwargs)

        tiempo_final = time.perf_counter()
        duracion = tiempo_final - tiempo_inicio #Tiempo total que tardó en ejecutarse la funcion.

        print(f"La función {funcion.__name__} tardó {duracion:.4f} segundos.")
        return resultado
    return funcion_decorada


def reintentar(intentos=3, espera=1, excepciones=(Exception,)): #define el decorador con sus parámetros por defecto

    if intentos < 1:
        raise ValueError("La cantidad de intentos debe ser mayor que cero.")

    def decorador(funcion):
        @wraps(funcion) #wraps para que la funcion decorada mantenga el nombre y data de la funcion original.
        def funcion_decorada(*args, **kwargs):

            for numero_intento in range(1, intentos + 1):
                
                try:
                    return funcion(*args, **kwargs)
                except excepciones as error:
                    print(f"Intento {numero_intento} de {intentos} fallido: {error}")

                    # Si ya fue el último intento,
                    # vuelve a lanzar el error.
                    if numero_intento == intentos:
                        raise

                    # Espera antes de volver a intentar.
                    time.sleep(espera)
        return funcion_decorada
    return decorador