# -*- coding: utf-8 -*-
import os
import numpy as np
import pandas as pd
import yfinance as yf
from hmmlearn import hmm
import matplotlib.pyplot as plt

# (Opcional) silenciar warning de joblib/loky
os.environ["LOKY_MAX_CPU_COUNT"] = str(os.cpu_count() or 4)

# Obtener datos
start = "2021-01-01"
end   = "2024-01-01"
ticker = "SPY"

# Especifica auto_adjust para evitar el FutureWarning
df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=False, progress=False)

# Features
df["log_r"] = np.log(df["Close"] / df["Close"].shift(1))
df["rango"] = df["High"].div(df["Low"]) - 1

# Dataset para HMM (mismo índice sin NaN)
datos = df[["log_r", "rango"]].dropna()

# Modelo HMM
modelo = hmm.GaussianHMM(n_components=2, covariance_type="full", random_state=1, n_iter=200)
modelo.fit(datos.values)

# Predicción (mismo largo que 'datos')
hidden_states = modelo.predict(datos.values)

# Alinear por índice ANTES de graficar
# 1) Close alineado al índice de 'datos'
close_aligned = df.loc[datos.index, "Close"]

# (Opcional) identificar cuál estado es "alcista" según la media de log_r
state_means = pd.DataFrame(modelo.means_, columns=["log_r", "rango"])
bull_state = state_means["log_r"].idxmax()  # estado con mayor retorno esperado
bear_state = 1 - bull_state

# Convertir a Series con el mismo índice para usar where
states_series = pd.Series(hidden_states, index=datos.index)

# Separar por estados ya mapeados a bull/bear
precio_bull = close_aligned.where(states_series == bull_state, np.nan)
precio_bear = close_aligned.where(states_series == bear_state, np.nan)

# Visualizar
plt.figure(figsize=(22, 12))
plt.plot(precio_bull, label="Tendencia Alcista (HMM)", linewidth=1.5)
plt.plot(precio_bear, label="Tendencia Bajista (HMM)", linewidth=1.5)
plt.title(f"Estados Ocultos en {ticker} (HMM) - Alcista/Bajista")
plt.xlabel("Tiempo")
plt.ylabel("Precio de Cierre")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
