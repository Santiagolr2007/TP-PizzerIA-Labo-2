import random
from src.modelos.inventario import Inventario
from src.modelos.pizzeria import Pizzeria
from src.modelos.producto import Bebida, Empanada, Pizza

_DOLAR_RESPALDO = 1500
_DOLAR_REFERENCIA = None


def obtener_dolar_referencia():
    global _DOLAR_REFERENCIA

    if _DOLAR_REFERENCIA is not None:
        return _DOLAR_REFERENCIA

    try:
        from src.servicios.proveedores import consultar_dolar_oficial

        # Se consulta una sola vez al iniciar; despues se reutiliza para no repetir requests.
        _DOLAR_REFERENCIA = consultar_dolar_oficial()
    except Exception:
        # Si la API falla, el sistema sigue funcionando con un valor de respaldo.
        _DOLAR_REFERENCIA = _DOLAR_RESPALDO

    return _DOLAR_REFERENCIA


def convertir_dolares_a_pesos(precio_dolares):
    # Convierte un precio estimado en dólares a pesos argentinos.
    constante_dolar = obtener_dolar_referencia()
    precio_pesos = precio_dolares * constante_dolar
    return int(precio_pesos)


def crear_stock_aleatorio(ingredientes):
    # Crea un stock aleatorio entre 40 y 100 para cada ingrediente.
    stock = {}
    for ingrediente in ingredientes:
        stock[ingrediente] = random.randint(30, 70)

    return stock


def crear_sistema():
    # Lista de ingredientes que maneja el inventario.
    ingredientes = [
        "harina",
        "salsa",
        "mozzarella",
        "jamon",
        "morron",
        "cebolla",
        "tomate",
        "ajo",
        "roquefort",
        "aceitunas",
        "tapas_empanada",
        "carne",
        "jamon_queso",
        "pollo",
        "verdura",
        "humita",
        "gaseosa",
        "agua"
    ]

    # Crea cantidades aleatorias entre 15 y 40 para todos los ingredientes.
    stock_inicial = crear_stock_aleatorio(ingredientes)

    # Precio unitario estimado de cada ingrediente convertido desde dólares.
    precios_stock = {
        "harina": convertir_dolares_a_pesos(0.60),
        "salsa": convertir_dolares_a_pesos(0.45),
        "mozzarella": convertir_dolares_a_pesos(1.20),
        "jamon": convertir_dolares_a_pesos(1.10),
        "morron": convertir_dolares_a_pesos(0.50),
        "cebolla": convertir_dolares_a_pesos(0.35),
        "tomate": convertir_dolares_a_pesos(0.45),
        "ajo": convertir_dolares_a_pesos(0.25),
        "roquefort": convertir_dolares_a_pesos(1.50),
        "aceitunas": convertir_dolares_a_pesos(0.70),
        "tapas_empanada": convertir_dolares_a_pesos(0.20),
        "carne": convertir_dolares_a_pesos(1.00),
        "jamon_queso": convertir_dolares_a_pesos(0.95),
        "pollo": convertir_dolares_a_pesos(0.90),
        "verdura": convertir_dolares_a_pesos(0.60),
        "humita": convertir_dolares_a_pesos(0.55),
        "gaseosa": convertir_dolares_a_pesos(0.80),
        "agua": convertir_dolares_a_pesos(0.45)
    }

    # Crea el inventario con cantidades y precios.
    inventario = Inventario(stock_inicial,precios_stock)

    # Crea la pizzería.
    dinero_inicial = random.randint(5000,20000)
    pizzeria = Pizzeria(inventario,dinero_inicial)


    # Registra pizzas. llamando el metodo registrar_producto y pasandole nombre precio y tamaño y diccionario con ingredientes:cantidad
    pizzeria.registrar_producto(
        Pizza(
            "Pizza muzzarella",
            convertir_dolares_a_pesos(5.50), #Todas las pizzas ya llevan harina salsa y mozzarella.
            "grande"
        )
    )

    pizzeria.registrar_producto(
        Pizza(
            "Pizza jamón y morrón",
            convertir_dolares_a_pesos(6.50),
            "grande",
            {
                "jamon": 2,
                "morron": 1
            }
        )
    )

    pizzeria.registrar_producto(
        Pizza(
            "Pizza fugazzeta",
            convertir_dolares_a_pesos(6.00),
            "grande",
            {
                "cebolla": 2
            }
        )
    )

    pizzeria.registrar_producto(
        Pizza(
            "Pizza napolitana",
            convertir_dolares_a_pesos(6.20),
            "grande",
            {
                "tomate": 2,
                "ajo": 1
            }
        )
    )

    pizzeria.registrar_producto(
        Pizza(
            "Pizza roquefort",
            convertir_dolares_a_pesos(6.80),
            "grande",
            {
                "roquefort": 2
            }
        )
    )

    pizzeria.registrar_producto(
        Pizza(
            "Pizza con aceitunas",
            convertir_dolares_a_pesos(5.80),
            "grande",
            {
                "aceitunas": 1
            }
        )
    )

    # Registra empanadas.
    pizzeria.registrar_producto(
        Empanada(
            "Empanada de carne",
            convertir_dolares_a_pesos(0.80),
            "carne"
        )
    )

    pizzeria.registrar_producto(
        Empanada(
            "Empanada de jamón y queso",
            convertir_dolares_a_pesos(0.80),
            "jamon_queso"
        )
    )

    pizzeria.registrar_producto(
        Empanada(
            "Empanada de pollo",
            convertir_dolares_a_pesos(0.80),
            "pollo"
        )
    )

    pizzeria.registrar_producto(
        Empanada(
            "Empanada de verdura",
            convertir_dolares_a_pesos(0.75),
            "verdura"
        )
    )

    pizzeria.registrar_producto(
        Empanada(
            "Empanada de humita",
            convertir_dolares_a_pesos(0.75),
            "humita"
        )
    )

    # Registra bebidas.
    pizzeria.registrar_producto(
        Bebida(
            "Gaseosa",
            convertir_dolares_a_pesos(1.70),
            "gaseosa"
        )
    )

    pizzeria.registrar_producto(
        Bebida(
            "Agua",
            convertir_dolares_a_pesos(1.00),
            "agua"
        )
    )

    return pizzeria
