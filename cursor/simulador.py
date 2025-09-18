# -*- coding: utf-8 -*-
"""
simulador.py
Comparación de 3 estrategias (Buy&Hold, cruces MAs, HMM) sobre SPY.
"""

import os
# (Opcional) silenciar warning de joblib/loky
os.environ["LOKY_MAX_CPU_COUNT"] = str(os.cpu_count() or 4)

import pandas as pd
import numpy as np
import yfinance as yf
from hmmlearn import hmm
import matplotlib.pyplot as plt


def descargar_datos(ticker="SPY", start="2019-01-01", end="2024-01-01"):
    # Evita FutureWarning de yfinance
    df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=False, progress=False)
    # Features
    df["log_r"] = np.log(df["Close"] / df["Close"].shift(1))
    df["rango"] = df["High"] / df["Low"] - 1
    df = df.dropna()
    return df


def split_train_test(df, fecha_corte="2021-12-31"):
    x_train = df[["log_r", "rango"]].loc[:fecha_corte]
    x_test  = df[["log_r", "rango"]].loc[pd.to_datetime(fecha_corte) + pd.offsets.Day(1):]
    print(f"Longitud de datos de entrenamiento: {x_train.shape[0]} - de {x_train.index[0]} a {x_train.index[-1]}")
    print(f"Longitud de datos de prueba: {x_test.shape[0]} - de {x_test.index[0]} a {x_test.index[-1]}")
    return x_train, x_test


def entrenar_hmm(x_train, n_states=2, seed=1, max_iter=200):
    modelo = hmm.GaussianHMM(n_components=n_states, covariance_type="full", random_state=seed, n_iter=max_iter)
    modelo.fit(x_train.values)
    return modelo


def estrategia_buy_hold(df_test):
    curva = (df_test["Close"].pct_change().fillna(0) + 1.0).cumprod()
    curva.iloc[0] = 1.0
    return curva.rename("rendimiento_estrategia1")


def estrategia_ma_cross(df_test, w_fast=9, w_slow=21):
    ma_fast = df_test["Close"].rolling(window=w_fast, min_periods=1).mean()
    ma_slow = df_test["Close"].rolling(window=w_slow, min_periods=1).mean()
    # Señal en {1, -1} sin crear arrays 2D
    cruce = (ma_fast > ma_slow).astype(int).replace(0, -1)
    cruce = cruce.ffill()
    r = df_test["Close"].pct_change().fillna(0)
    curva = (1 + cruce.shift(1).fillna(0) * r).cumprod()
    curva.iloc[0] = 1.0
    return curva.rename("rendimiento_estrategia2")


def mapear_estados_hmm(df_test, modelo, hidden_states_test, n_cont=25):
    """
    Devuelve un diccionario {'alcista': Serie Close con NaN fuera del estado alcista,
                             'bajista': Serie Close con NaN fuera del estado bajista}
    Determina bull/bear por:
      1) Buscar un tramo continuo de n_cont en estado 0 y mirar su pendiente.
      2) Si no se encuentra, usa la media de log_r del modelo para decidir bull_state.
    """
    # Series por estado según predicción
    close = df_test["Close"]
    estado0 = close.where(hidden_states_test == 0, np.nan)
    estado1 = close.where(hidden_states_test == 1, np.nan)

    # Paso 1: intento por tramo continuo en estado 0
    for i in range(0, len(estado0) - n_cont):
        tramo = estado0.iloc[i:i + n_cont].dropna()
        if len(tramo) == n_cont:
            # pendiente de y(tramo) vs x=0..n-1
            pend = np.polyfit(np.arange(n_cont), tramo.values, 1)[0]
            if pend > 0:
                return {"alcista": estado0, "bajista": estado1}
            else:
                return {"alcista": estado1, "bajista": estado0}

    # Paso 2 (fallback): por medias del HMM
    state_means = pd.DataFrame(modelo.means_, columns=["log_r", "rango"])
    bull_state = state_means["log_r"].idxmax()
    bear_state = 1 - bull_state
    alcista = close.where(hidden_states_test == bull_state, np.nan)
    bajista = close.where(hidden_states_test == bear_state, np.nan)
    return {"alcista": alcista, "bajista": bajista}


def estrategia_hmm(df_test, estados):
    # Dirección: 1 si precio pertenece al estado alcista, -1 en caso contrario
    direccion = np.where(estados["alcista"].notna(), 1, -1)
    direccion = pd.Series(direccion, index=df_test.index, name="Direccion")
    r = df_test["Close"].pct_change().fillna(0)
    curva = (1 + direccion.shift(1).fillna(0) * r).cumprod()
    curva.iloc[0] = 1.0
    return curva.rename("rendimiento_estrategia3")


def main():
    # 1) Datos
    df = descargar_datos("SPY", "2019-01-01", "2024-01-01")

    # 2) Split
    x_train, x_test = split_train_test(df, "2021-12-31")
    df_prueba = df.loc[x_test.index].copy()

    # 3) HMM
    modelo = entrenar_hmm(x_train, n_states=2, seed=1, max_iter=200)
    hidden_states_train = modelo.predict(x_train.values)
    hidden_states_test = modelo.predict(x_test.values)

    # 4) Estados alcista/bajista mapeados
    estados = mapear_estados_hmm(df_prueba, modelo, hidden_states_test, n_cont=25)

    # 5) Visualizar estados (opcional)
    plt.figure(figsize=(22, 9))
    plt.plot(estados["bajista"], color="red", label="Tendencia Bajista (HMM)", linewidth=1.3)
    plt.plot(estados["alcista"], color="green", label="Tendencia Alcista (HMM)", linewidth=1.3)
    plt.title("Estados Ocultos en SPY (HMM) - Alcista/Bajista")
    plt.xlabel("Tiempo")
    plt.ylabel("Precio")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

    # 6) Estrategias
    curva1 = estrategia_buy_hold(df_prueba)
    curva2 = estrategia_ma_cross(df_prueba, w_fast=9, w_slow=21)
    curva3 = estrategia_hmm(df_prueba, estados)

    # 7) Comparativa de rendimientos
    curvas = pd.concat([curva1, curva2, curva3], axis=1)
    plt.figure(figsize=(22, 9))
    curvas.plot(ax=plt.gca(), linewidth=1.5)
    plt.title("Comparativa de Rendimientos (Buy&Hold vs MA Cross vs HMM)")
    plt.xlabel("Tiempo")
    plt.ylabel("Comportamiento del Capital (base=1)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
