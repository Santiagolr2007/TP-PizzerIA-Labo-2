import time
import logging
import re
from functools import wraps

logging.basicConfig(
    filename='logs/sistema.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

#Mide cuanto tarde en ejecutarse cualquier funcion clave del sistema
def medir_tiempo(funcion_original):
    @wraps(funcion_original)
    def funcion_envoltura(*args, **kwargs):
        inicio = time.time()
        resultado = funcion_original(*args, **kwargs)
        fin = time.time()
        tiempo_total = fin - inicio
        logging.info(f"Funcion [{funcion_original.__name__}] - Tiempo de ejecucion: {tiempo_total:.4f} segundos.")
        return resultado
    return funcion_envoltura

#registra en el log cada accion importante, ya sea porque salio bien o el motivo exacto por el cual fallo
def registrar_auditoria(funcion_original):
    @wraps(funcion_original)
    def funcion_envoltura(*args, **kwargs):
        logging.info(f"AUDITORIA: Ejecutando '{funcion_original.__name__}' con argumentos: {args} {kwargs}")
        try:
            resultado = funcion_original(*args, **kwargs)
            logging.info(f"AUDITORIA: '{funcion_original.__name__}' finalizo con exito.")
            return resultado
        except Exception as e:
            logging.error(f"AUDITORIA ERROR: Fallo '{funcion_original.__name__}'. Motivo: {type(e).__name__}: {e}")
            raise e
    return funcion_envoltura
