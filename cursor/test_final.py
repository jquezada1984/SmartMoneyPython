# -*- coding: utf-8 -*-
print("=== INICIANDO PRUEBA FINAL ===")

import pandas as pd
import numpy as np
import yfinance as yf
from hmmlearn import hmm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

print("Librerías importadas correctamente")

try:
    print("Descargando datos de SPY...")
    df = yf.download("SPY", start="2022-01-01", end="2023-12-31", interval="1d", progress=False)
    print("Datos descargados exitosamente. Forma:", df.shape)
    
    # Aplanar las columnas MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        print("Columnas MultiIndex aplanadas")
    
    # Crear columnas para el modelo
    df["log_r"] = np.log(df["Close"]/df["Close"].shift(periods=1))
    df["rango"] = df["High"] / df["Low"] - 1
    df = df.dropna()
    print("Columnas creadas. Forma después de dropna:", df.shape)
    
    # Separar datos (70% entrenamiento, 30% prueba)
    split_point = int(len(df) * 0.7)
    x_train = df[["log_r", "rango"]].iloc[:split_point]
    x_test = df[["log_r", "rango"]].iloc[split_point:]
    
    print(f"Datos de entrenamiento: {x_train.shape[0]}")
    print(f"Datos de prueba: {x_test.shape[0]}")
    
    # Modelo HMM
    print("Entrenando modelo HMM...")
    modelo = hmm.GaussianHMM(n_components=2, covariance_type="full", random_state=1)
    modelo.fit(x_train)
    print("Modelo entrenado exitosamente")
    
    # Predicciones
    hidden_states_prueba = modelo.predict(x_test)
    print("Predicciones completadas")
    
    # Datos de prueba
    df_prueba = df.iloc[split_point:].copy()
    print("DataFrame de prueba creado:", df_prueba.shape)
    
    # Estrategia 1: Comprar y Mantener
    df_prueba["rendimiento_estrategia1"] = (df_prueba["Close"].pct_change() + 1).cumprod()
    print("Estrategia 1 completada")
    
    # Estrategia 2: Cruce de Medias
    ma_9d = df_prueba["Close"].rolling(window=9).mean()
    ma_21d = df_prueba["Close"].rolling(window=21).mean()
    cruce = np.where(ma_9d > ma_21d, 1, -1)
    cruce = cruce.flatten()
    cruce = pd.Series(cruce, index=df_prueba.index).ffill()
    rendimientos_diarios = df_prueba["Close"].pct_change()
    cruce_shifted = cruce.shift(periods=1)
    rendimiento_estrategia2 = (1 + cruce_shifted * rendimientos_diarios).cumprod()
    df_prueba["rendimiento_estrategia2"] = rendimiento_estrategia2
    print("Estrategia 2 completada")
    
    # Estrategia 3: Modelo de Markov
    estado0 = df_prueba["Close"].where(hidden_states_prueba==0, np.nan)
    estado1 = df_prueba["Close"].where(hidden_states_prueba==1, np.nan)
    
    # Lógica de estados simplificada
    n_continuidad = min(25, len(estado0) // 4)  # Ajustar según datos disponibles
    estados = {"alcista": estado1, "bajista": estado0}  # Simplificado
    
    direccion = np.where(estados["alcista"].notnull(), 1, -1)
    direccion = pd.Series(direccion, index=df_prueba.index, name="Direccion")
    direccion_shifted = direccion.shift(periods=1)
    rendimiento_estrategia3 = (1 + direccion_shifted * rendimientos_diarios).cumprod()
    df_prueba["rendimiento_estrategia3"] = rendimiento_estrategia3
    print("Estrategia 3 completada")
    
    # Mostrar resultados
    print("\n=== RENDIMIENTOS FINALES ===")
    print(f"Estrategia 1 (Comprar y Mantener): {df_prueba['rendimiento_estrategia1'].iloc[-1]:.4f}")
    print(f"Estrategia 2 (Cruce de Medias): {df_prueba['rendimiento_estrategia2'].iloc[-1]:.4f}")
    print(f"Estrategia 3 (Modelo de Markov): {df_prueba['rendimiento_estrategia3'].iloc[-1]:.4f}")
    
    # Crear gráfico simple
    plt.figure(figsize=(12, 8))
    df_prueba[["rendimiento_estrategia1", "rendimiento_estrategia2", "rendimiento_estrategia3"]].plot()
    plt.title("Comparativa de Rendimientos para Estrategias")
    plt.xlabel("Tiempo")
    plt.ylabel("Comportamiento del Capital")
    plt.legend()
    plt.savefig("comparativa_rendimientos.png", dpi=300, bbox_inches='tight')
    print("Gráfico guardado como 'comparativa_rendimientos.png'")
    plt.close()
    
    print("\n=== SCRIPT COMPLETADO EXITOSAMENTE ===")
    
except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
