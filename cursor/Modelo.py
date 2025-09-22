# -*- coding: utf-8 -*-
# Importar librerías
import numpy as np
import pandas as pd
import yfinance as yf
from hmmlearn import hmm
import matplotlib.pyplot as plt

# Obtener datos
start="2021-01-01"
end="2024-01-01"
ticker="SPY"
df = yf.download(ticker, start, end, interval="1d")

# Agregar los retornos logarítmicos y el rango diario de cada vela
df["log_r"] = np.log(df["Close"] / df["Close"].shift(periods=1))
df["rango"] = df["High"].div(df["Low"]) - 1

# Definir el modelo con 2 estados ocultos
modelo = hmm.GaussianHMM(n_components=2, covariance_type="full", random_state=1)

# Ajustar el modelo
datos = df[["log_r", "rango"]].dropna()
modelo.fit(datos)

# Predecir
hidden_states = modelo.predict(datos)

# Separar Estados Ocultos - usar el mismo índice que los datos
Close = df.loc[datos.index, "Close"]
# Convertir hidden_states a Serie de pandas con el mismo índice
hidden_states_series = pd.Series(hidden_states, index=datos.index)
estado0 = Close.where(hidden_states_series==0, np.nan)
estado1 = Close.where(hidden_states_series==1, np.nan)

n_continuidad = 25
estados = {"alcista": "", "bajista": ""}

# Iterar sobre las filas de cualquier estado (estado0 o estado1)
encontrado = False
for i in range(estado0.shape[0] - n_continuidad):
    sub_estado0 = estado0.iloc[i: i + n_continuidad].dropna()
    # Revisar si hay 25 datos continuos
    if sub_estado0.shape[0] == n_continuidad:
        # Ajustar Regresión para conocer la pendiente
        params = np.polyfit(x=sub_estado0.values.flatten(), y=range(0, n_continuidad), deg=1)
        pendiente = params[0]
        if pendiente > 0:
            estados["alcista"] = estado0
            estados["bajista"] = estado1
        else:
            estados["alcista"] = estado1
            estados["bajista"] = estado0
        encontrado = True
        # Cesar ejecución
        break

# Si no se encontraron 25 datos continuos, usar una lógica alternativa
if not encontrado:
    # Calcular la pendiente promedio de cada estado
    pendiente_estado0 = np.nanmean(np.diff(estado0.dropna()))
    pendiente_estado1 = np.nanmean(np.diff(estado1.dropna()))
    
    if pendiente_estado0 > pendiente_estado1:
        estados["alcista"] = estado0
        estados["bajista"] = estado1
    else:
        estados["alcista"] = estado1
        estados["bajista"] = estado0
    
# Visualizar
plt.figure(figsize=(22, 12))
plt.plot(estados["bajista"], color="red", label="Tendencia Bajista")
plt.plot(estados["alcista"], color="green", label="Tendencia Alcista")
plt.title("Estados Ocultos en el ETF (SPY) - Alcista/Bajista")
plt.xlabel("Tiempo")
plt.ylabel("Precio")
plt.legend()
plt.grid()
plt.show()

# Recordatorio:
#   - Se pueden detectar los estados internos de nuetro mode