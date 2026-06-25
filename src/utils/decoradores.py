import os
import time
from pathlib import Path
from functools import wraps
from datetime import datetime
from zoneinfo import ZoneInfo

# Solo se usa para el request del precio del dolar.
def reintentar(intentos=3, espera=1, excepciones=(Exception,)): #define el decorador con sus parámetros por defecto

    # Decorador generico para operaciones externas que pueden fallar temporalmente.
    if intentos < 1:
        raise ValueError("La cantidad de intentos debe ser mayor que cero.")

    def decorador(funcion):
        @wraps(funcion) #wraps para que la funcion decorada mantenga el nombre y data de la funcion original.
        def funcion_decorada(*args, **kwargs):

            # Ejecuta la funcion varias veces. Si el error pertenece a las
            # excepciones esperadas, espera y vuelve a intentar.
            for numero_intento in range(1, intentos + 1):
                
                try:
                    return funcion(*args, **kwargs)
                except excepciones as error:
                    print(f"Intento {numero_intento} de {intentos} fallido: {error}")

                    # Si ya fue el último intento,vuelve a lanzar el error.
                    if numero_intento == intentos:
                        raise

                    # Espera antes de volver a intentar.
                    time.sleep(espera) #Por defecto un segundo
        return funcion_decorada
    return decorador

#Mide cuanto tarde en ejecutarse cualquier funcion clave del sistema
def medir_tiempo(funcion):
    # Decorador simple para conocer cuanto tarda una funcion importante.
    # Sirve para mostrar evidencia de uso de decoradores en el TP.
    @wraps(funcion) #wraps para que la funcion decorada mantenga el nombre y data de la funcion original.
    def funcion_decorada(*args, **kwargs):

        tiempo_inicio = time.perf_counter() #Contador
        resultado = funcion(*args, **kwargs)
        tiempo_final = time.perf_counter() #Contador 2
        duracion = tiempo_final - tiempo_inicio #Tiempo total que tardó en ejecutarse la funcion.

        print(f"La función {funcion.__name__} tardó {duracion:.4f} segundos.") # 4 decimales
        return resultado
    return funcion_decorada

#registra en el log cada accion importante, ya sea porque salio bien o el motivo exacto por el cual fallo
def registrar_log(funcion):
    # Decorador de auditoria: registra si una operacion termino bien o fallo.
    # El log queda en disco y se acumula entre ejecuciones del programa.
    @wraps(funcion) #wraps para que la funcion decorada mantenga el nombre y data de la funcion original.
    def envoltura(*args, **kwargs): #__file__ da la ruta del archivo actual
        ruta_proyecto = Path(__file__).resolve().parents[2] #sube desde decoradores_v2.py hasta la raíz del proyecto.
        # A partir de la raiz del proyecto se prepara la carpeta acumulativa de logs.
        carpeta_logs = ruta_proyecto / "logs" # Escribe la ruta de la carpeta log y agrega el "logs" final
        carpeta_logs.mkdir(exist_ok=True) # Si la carpeta ya existe no hagas nada.
        
        zona_argentina = ZoneInfo("America/Argentina/Buenos_Aires") #Zona de donde tomar la hora
        inicio = datetime.now(zona_argentina).strftime("%Y-%m-%d %H:%M:%S") #toma la fecha y hora actual de zona_argentina para incluirla en el mensaje del log
        try:
            # Si la funcion se ejecuta bien, se guarda una linea OK.
            resultado = funcion(*args, **kwargs)
            mensaje = f"[{inicio}] OK - {funcion.__name__}\n" # "[Hora]" OK - "Funcion ejecutada"
            return resultado
        except Exception as error:
            # Si falla, se guarda el error y se relanza para que la interfaz
            # pueda mostrar el mensaje correspondiente.
            mensaje = f"[{inicio}] ERROR - {funcion.__name__}: {error}\n" # [Hora] ERROR - "Funcion ejecutada": "ERROR"
            raise # Relanza la excepción para que el programa pueda seguir manejándola fuera del decorador.
        finally:
            with open(carpeta_logs / "sistema.log", "a", encoding="utf-8") as archivo:
                archivo.write(mensaje) # "a" de append, agrega el mensaje sin borrar los registros anteriores.
    return envoltura
