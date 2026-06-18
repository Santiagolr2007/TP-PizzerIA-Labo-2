import pandas as pd


def transformar_ventas(ventas): #ventas=lista de diccionarios
    columnas = [
        "pedido_id",
        "fecha",
        "cliente",
        "producto",
        "cantidad",
        "precio_unitario",
        "subtotal",
    ]

    dataframe = pd.DataFrame(ventas, columns=columnas) #crea el dataframe

    if dataframe.empty:
        return dataframe #si no hay ventas corta aca

    dataframe = dataframe.drop_duplicates(
        subset=["pedido_id", "producto", "cantidad"] #elimina ventas duplicadas, si hay dos ventas con el mismo pedido_id, producto y cantidad.
    )

    dataframe["fecha"] = pd.to_datetime( #transforma la columna fecha a tipo datetime, (formato de fecha real)
        dataframe["fecha"],
        errors="coerce", #si da error=Nulo
    )

    columnas_numericas = [ #define cuales columnas son numericas
        "cantidad",
        "precio_unitario",
        "subtotal",
    ]

    for columna in columnas_numericas:
        dataframe[columna] = pd.to_numeric( #tranforma las columnas definidas a tipo numerico
            dataframe[columna],
            errors="coerce", #si da error=nulo
        )

    dataframe = dataframe.dropna(
        subset=["pedido_id", "fecha", "producto", "subtotal"] #elimina filas con valores nulos
    )

    return dataframe


def transformar_stock(stock): #stock=diccionario de ingredientes y cantidades
    dataframe = pd.DataFrame(
        list(stock.items()),
        columns=["ingrediente", "cantidad"],
    ) # lo tranformo en un dataframe con las columnas ingrediente y cantidad

    dataframe["cantidad"] = pd.to_numeric(
        dataframe["cantidad"],
        errors="coerce",
    ).fillna(0) #pasa a tipo numerico y si hay error lo reemplaza por 0

    dataframe = dataframe.drop_duplicates(subset=["ingrediente"])
    dataframe["alerta_reposicion"] = dataframe["cantidad"] <= 5 #crea la columna alerta_reposicion booleana que depende de si es menor o igual a 5

    return dataframe
