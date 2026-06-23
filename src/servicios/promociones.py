from src.modelos.producto import Empanada


PROMOCIONES_EMPANADAS = (
    {
        "minimo": 12,
        "porcentaje": 0.15,
        "nombre": "Promo docena de empanadas",
        "descripcion": "15% de descuento en empanadas",
    },
    {
        "minimo": 6,
        "porcentaje": 0.10,
        "nombre": "Promo media docena de empanadas",
        "descripcion": "10% de descuento en empanadas",
    },
)


def calcular_promociones_pedido(productos):
    cantidad_empanadas = 0
    subtotal_empanadas = 0

    for producto, cantidad in productos:
        if isinstance(producto, Empanada):
            cantidad_empanadas += int(cantidad)
            subtotal_empanadas += producto.calcular_precio() * int(cantidad)

    if cantidad_empanadas < 6 or subtotal_empanadas <= 0:
        return []

    for promocion in PROMOCIONES_EMPANADAS:
        if cantidad_empanadas >= promocion["minimo"]:
            descuento = subtotal_empanadas * promocion["porcentaje"]
            return [
                {
                    "tipo": "empanadas",
                    "nombre": promocion["nombre"],
                    "descripcion": promocion["descripcion"],
                    "cantidad": cantidad_empanadas,
                    "porcentaje": promocion["porcentaje"],
                    "subtotal_base": subtotal_empanadas,
                    "descuento": descuento,
                }
            ]

    return []
