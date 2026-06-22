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

    dataframe = dataframe.drop_duplicates(subset=["pedido_id", "producto", "cantidad"]) #elimina ventas duplicadas, si hay dos ventas con el mismo pedido_id, producto y cantidad.
    dataframe["fecha"] = pd.to_datetime(dataframe["fecha"],errors="coerce",) #Tranforma en fecha y si da error=Nulo
    columnas_numericas = ["cantidad","precio_unitario","subtotal",] #define cuales columnas son numericas

    for columna in columnas_numericas:
        dataframe[columna] = pd.to_numeric(dataframe[columna],errors="coerce",)#tranforma las columnas definidas a tipo numerico y si da error=nulo

    dataframe = dataframe.dropna(subset=["pedido_id", "fecha", "producto", "subtotal"]) #elimina filas con valores nulos
    return dataframe


def transformar_stock(stock):
    # Si el stock ya viene detallado, lo convierte directo en DataFrame.
    if isinstance(stock, list): #isinstance verifica si stock es una list
        dataframe = pd.DataFrame(stock)
    # Si el stock viene como diccionario simple, lo arma sin precios.
    else:
        filas = []

        for ingrediente, cantidad in stock.items():
            fila = {"ingrediente": ingrediente,"cantidad": cantidad,"precio_unitario": 0,"valor_total_stock": 0}
            filas.append(fila)

        dataframe = pd.DataFrame(filas)

    columnas = ["ingrediente","cantidad","precio_unitario","valor_total_stock"]

    # Asegura que existan todas las columnas.
    for columna in columnas:
        if columna not in dataframe.columns:
            dataframe[columna] = 0

    dataframe["cantidad"] = pd.to_numeric(dataframe["cantidad"],errors="coerce").fillna(0) # Remplaza nulos por 0
    dataframe["precio_unitario"] = pd.to_numeric(dataframe["precio_unitario"],errors="coerce").fillna(0) # Remplaza nulos por 0
    dataframe["valor_total_stock"] = (dataframe["cantidad"] * dataframe["precio_unitario"])
    dataframe["estado"] = "Disponible" 
    dataframe.loc[dataframe["cantidad"] <= 5,"estado"] = "Reponer"
    return dataframe
