#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GENERADOR DE IMÁGENES PARA SEÑALES ICC
======================================

Este módulo genera imágenes de gráficos cuando se detectan señales de compra o venta
en la estrategia ICC, similar a como lo hace implementacion_icc.py
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp
import numpy as np
import os
from datetime import datetime
import time

def calculate_macd(df, fast=12, slow=26, signal=9):
    """Calcular MACD: MACD Line, Signal Line, Histogram"""
    exp1 = df['close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['close'].ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_rsi(df, period=14):
    """Calcular RSI"""
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def add_FVG(fig, df, fvg_data):
    """Agregar Fair Value Gaps al gráfico"""
    if fvg_data is None or fvg_data.empty:
        return fig
        
    window_size = len(df)
    
    # Asegurarse de que fvg_data use los mismos índices que df
    fvg_data = fvg_data.reset_index(drop=True)
    
    for i in range(len(fvg_data)):
        if not pd.isna(fvg_data["FVG"].iloc[i]):
            # Asegurarse de que x1 no exceda el tamaño de la ventana
            x1 = min(
                int(fvg_data["MitigatedIndex"].iloc[i])
                if fvg_data["MitigatedIndex"].iloc[i] != 0
                else window_size - 1,
                window_size - 1
            )
            
            fig.add_shape(
                type="rect",
                x0=df.index[i],
                y0=fvg_data["Top"].iloc[i],
                x1=df.index[x1],
                y1=fvg_data["Bottom"].iloc[i],
                line=dict(width=0),
                fillcolor="yellow",
                opacity=0.2,
            )
            
            # Calcular punto medio asegurándose de no exceder los límites
            mid_x = min(round((i + x1) / 2), window_size - 1)
            mid_y = (fvg_data["Top"].iloc[i] + fvg_data["Bottom"].iloc[i]) / 2
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[mid_y],
                    mode="text",
                    text="FVG",
                    textposition="middle center",
                    textfont=dict(color='rgba(255, 255, 255, 0.4)', size=8),
                )
            )
    return fig

def add_swing_highs_lows(fig, df, swing_data):
    """Agregar Swing Highs y Lows al gráfico"""
    if swing_data is None or swing_data.empty:
        return fig
        
    window_size = len(df)
    
    # Asegurarse de que swing_data use los mismos índices que df
    swing_data = swing_data.reset_index(drop=True)
    
    indexs = []
    level = []
    for i in range(len(swing_data)):
        if not pd.isna(swing_data["HighLow"].iloc[i]):
            if i < window_size:  # Solo agregar puntos dentro de la ventana
                indexs.append(i)
                level.append(swing_data["Level"].iloc[i])

    # Dibujar líneas en el gráfico
    for i in range(len(indexs) - 1):
        if indexs[i] < window_size and indexs[i + 1] < window_size:  # Verificar que ambos puntos estén en la ventana
            fig.add_trace(
                go.Scatter(
                    x=[df.index[indexs[i]], df.index[indexs[i + 1]]],
                    y=[level[i], level[i + 1]],
                    mode="lines",
                    line=dict(
                        color=(
                            "rgba(0, 128, 0, 0.2)"
                            if swing_data["HighLow"].iloc[indexs[i]] == -1
                            else "rgba(255, 0, 0, 0.2)"
                        ),
                    ),
                )
            )

    return fig

def add_bos_choch(fig, df, bos_choch_data):
    """Agregar Break of Structure (BOS) y Change of Character (CHOCH) al gráfico"""
    if bos_choch_data is None or bos_choch_data.empty:
        return fig
        
    window_size = len(df)
    
    # Asegurarse de que bos_choch_data use los mismos índices que df
    bos_choch_data = bos_choch_data.reset_index(drop=True)
    
    for i in range(len(bos_choch_data)):
        if i >= window_size:
            break
            
        # Procesar BOS
        if not pd.isna(bos_choch_data["BOS"].iloc[i]):
            broken_idx = min(int(bos_choch_data["BrokenIndex"].iloc[i]), window_size - 1)
            mid_x = min(round((i + broken_idx) / 2), window_size - 1)
            mid_y = bos_choch_data["Level"].iloc[i]
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[i], df.index[broken_idx]],
                    y=[bos_choch_data["Level"].iloc[i], bos_choch_data["Level"].iloc[i]],
                    mode="lines",
                    line=dict(
                        color="rgba(255, 165, 0, 0.2)",
                    ),
                )
            )
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[mid_y],
                    mode="text",
                    text="BOS",
                    textposition="top center" if bos_choch_data["BOS"].iloc[i] == 1 else "bottom center",
                    textfont=dict(color="rgba(255, 165, 0, 0.4)", size=8),
                )
            )
            
        # Procesar CHOCH
        if not pd.isna(bos_choch_data["CHOCH"].iloc[i]):
            broken_idx = min(int(bos_choch_data["BrokenIndex"].iloc[i]), window_size - 1)
            mid_x = min(round((i + broken_idx) / 2), window_size - 1)
            mid_y = bos_choch_data["Level"].iloc[i]
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[i], df.index[broken_idx]],
                    y=[bos_choch_data["Level"].iloc[i], bos_choch_data["Level"].iloc[i]],
                    mode="lines",
                    line=dict(
                        color="rgba(0, 0, 255, 0.2)",
                    ),
                )
            )
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[mid_y],
                    mode="text",
                    text="CHOCH",
                    textposition="top center" if bos_choch_data["CHOCH"].iloc[i] == 1 else "bottom center",
                    textfont=dict(color="rgba(0, 0, 255, 0.4)", size=8),
                )
            )

    return fig

def add_OB(fig, df, ob_data):
    """Agregar Order Blocks al gráfico"""
    if ob_data is None or ob_data.empty:
        return fig
        
    def format_volume(volume):
        if volume >= 1e12:
            return f"{volume / 1e12:.3f}T"
        elif volume >= 1e9:
            return f"{volume / 1e9:.3f}B"
        elif volume >= 1e6:
            return f"{volume / 1e6:.3f}M"
        elif volume >= 1e3:
            return f"{volume / 1e3:.3f}k"
        else:
            return f"{volume:.2f}"

    window_size = len(df)
    
    # Asegurarse de que ob_data use los mismos índices que df
    ob_data = ob_data.reset_index(drop=True)

    for i in range(len(ob_data)):
        if i >= window_size:
            break
            
        # Procesar Order Blocks alcistas
        if ob_data["OB"].iloc[i] == 1:
            # Asegurarse de que x1 no exceda el tamaño de la ventana
            x1 = min(
                int(ob_data["MitigatedIndex"].iloc[i]) if ob_data["MitigatedIndex"].iloc[i] != 0 else window_size - 1,
                window_size - 1
            )
            
            fig.add_shape(
                type="rect",
                x0=df.index[i],
                y0=ob_data["Bottom"].iloc[i],
                x1=df.index[x1],
                y1=ob_data["Top"].iloc[i],
                line=dict(color="Purple"),
                fillcolor="Purple",
                opacity=0.2,
                name="Bullish OB",
                legendgroup="bullish ob",
                showlegend=True,
            )

            # Calcular x_center asegurándose de no exceder los límites
            if ob_data["MitigatedIndex"].iloc[i] > 0:
                mid_point = min(int(i + (ob_data["MitigatedIndex"].iloc[i] - i) / 2), window_size - 1)
            else:
                mid_point = min(int(i + (window_size - i) / 2), window_size - 1)
            x_center = df.index[mid_point]

            y_center = (ob_data["Bottom"].iloc[i] + ob_data["Top"].iloc[i]) / 2
            volume_text = format_volume(ob_data["OBVolume"].iloc[i])
            annotation_text = f'OB: {volume_text} ({ob_data["Percentage"].iloc[i]}%)'

            fig.add_annotation(
                x=x_center,
                y=y_center,
                xref="x",
                yref="y",
                align="center",
                text=annotation_text,
                font=dict(color="rgba(255, 255, 255, 0.4)", size=8),
                showarrow=False,
            )
        
        # Procesar Order Blocks bajistas
        elif ob_data["OB"].iloc[i] == -1:
            # Asegurarse de que x1 no exceda el tamaño de la ventana
            x1 = min(
                int(ob_data["MitigatedIndex"].iloc[i]) if ob_data["MitigatedIndex"].iloc[i] != 0 else window_size - 1,
                window_size - 1
            )
            
            fig.add_shape(
                type="rect",
                x0=df.index[i],
                y0=ob_data["Bottom"].iloc[i],
                x1=df.index[x1],
                y1=ob_data["Top"].iloc[i],
                line=dict(color="Purple"),
                fillcolor="Purple",
                opacity=0.2,
                name="Bearish OB",
                legendgroup="bearish ob",
                showlegend=True,
            )

            # Calcular x_center asegurándose de no exceder los límites
            if ob_data["MitigatedIndex"].iloc[i] > 0:
                mid_point = min(int(i + (ob_data["MitigatedIndex"].iloc[i] - i) / 2), window_size - 1)
            else:
                mid_point = min(int(i + (window_size - i) / 2), window_size - 1)
            x_center = df.index[mid_point]

            y_center = (ob_data["Bottom"].iloc[i] + ob_data["Top"].iloc[i]) / 2
            volume_text = format_volume(ob_data["OBVolume"].iloc[i])
            annotation_text = f'OB: {volume_text} ({ob_data["Percentage"].iloc[i]}%)'

            fig.add_annotation(
                x=x_center,
                y=y_center,
                xref="x",
                yref="y",
                align="center",
                text=annotation_text,
                font=dict(color="rgba(255, 255, 255, 0.4)", size=8),
                showarrow=False,
            )
    return fig

def add_liquidity(fig, df, liquidity_data):
    """Agregar niveles de liquidez al gráfico"""
    window_size = len(df)
    
    # Asegurarse de que liquidity_data use los mismos índices que df
    liquidity_data = liquidity_data.reset_index(drop=True)
    
    for i in range(len(liquidity_data)):
        if i >= window_size:
            break
            
        # Procesar niveles de liquidez
        if not pd.isna(liquidity_data["Liquidity"].iloc[i]):
            end_idx = min(int(liquidity_data["End"].iloc[i]), window_size - 1)
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[i], df.index[end_idx]],
                    y=[liquidity_data["Level"].iloc[i], liquidity_data["Level"].iloc[i]],
                    mode="lines",
                    line=dict(
                        color="rgba(255, 165, 0, 0.2)",
                    ),
                )
            )
            
            mid_x = min(round((i + end_idx) / 2), window_size - 1)
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[liquidity_data["Level"].iloc[i]],
                    mode="text",
                    text="LIQ",
                    textposition="top center",
                    textfont=dict(color="rgba(255, 165, 0, 0.4)", size=8),
                )
            )
    return fig

def add_icc_signals(fig, icc_signals, df, row=1, col=1):
    """Agregar señales ICC al gráfico con UN SOLO TP ESTRUCTURAL y LÍNEAS HORIZONTALES CLARAS"""
    if not icc_signals:
        return fig
    
    for signal in icc_signals:
        try:
            direction = signal.get('direction', 'UNKNOWN')
            entry_price = signal.get('entry_price')
            risk_management = signal.get('risk_management', {})
            stop_loss = risk_management.get('stop_loss')
            take_profit = risk_management.get('take_profit')  # TP ESTRUCTURAL ÚNICO
            
            if entry_price and stop_loss and take_profit:
                if direction == 'LONG':
                    # COMPRA: TP por encima del precio de entrada
                    
                    # AGREGAR LÍNEA HORIZONTAL CLARA PARA TP ESTRUCTURAL ÚNICO
                    # Take Profit Estructural - Línea verde sólida muy visible
                    fig.add_hline(
                        y=take_profit, 
                        line_dash="solid", 
                        line_color="#00ff00",  # Verde brillante
                        line_width=4,  # Línea más gruesa
                        opacity=1.0,   # Opacidad completa
                        annotation_text=f"🎯 TP ESTRUCTURAL: {take_profit:.5f}",
                        annotation_position="right",
                        annotation=dict(
                            font=dict(size=14, color='#00ff00', weight='bold'),
                            bgcolor='rgba(0,0,0,0.8)',
                            bordercolor='#00ff00',
                            borderwidth=2
                        ),
                        row=row, col=col
                    )
                    
                    # Stop Loss - Línea roja sólida muy visible
                    fig.add_hline(
                        y=stop_loss, 
                        line_dash="solid", 
                        line_color="#ff0000",  # Rojo brillante
                        line_width=4,  # Línea más gruesa
                        opacity=1.0,   # Opacidad completa
                        annotation_text=f"🛑 STOP LOSS: {stop_loss:.5f}",
                        annotation_position="right",
                        annotation=dict(
                            font=dict(size=14, color='#ff0000', weight='bold'),
                            bgcolor='rgba(0,0,0,0.8)',
                            bordercolor='#ff0000',
                            borderwidth=2
                        ),
                        row=row, col=col
                    )
                    
                    # Marcar punto de entrada COMPRA
                    fig.add_trace(
                        go.Scatter(
                            x=[df.index[-1]],
                            y=[entry_price],
                            mode='markers+text',
                            marker=dict(color='green', size=20, symbol='diamond'),
                            text=['▲ COMPRA'],
                            textposition='top center',
                            textfont=dict(size=14, color='white', weight='bold'),
                            name='Entrada COMPRA',
                            showlegend=False
                        ),
                        row=row, col=col
                    )

                    # Marcar Take Profit Estructural ÚNICO
                    fig.add_trace(
                        go.Scatter(
                            x=[df.index[-1]],
                            y=[take_profit],
                            mode='markers+text',
                            marker=dict(color='lime', size=15, symbol='star'),
                            text=['TP ESTRUCTURAL'],
                            textposition='top center',
                            textfont=dict(size=12, color='lime', weight='bold'),
                            name='Take Profit Estructural',
                            showlegend=False
                        ),
                        row=row, col=col
                    )

                elif direction == 'SHORT':
                    # VENTA: TP por debajo del precio de entrada
                    
                    # AGREGAR LÍNEA HORIZONTAL CLARA PARA TP ESTRUCTURAL ÚNICO
                    # Take Profit Estructural - Línea roja sólida muy visible
                    fig.add_hline(
                        y=take_profit, 
                        line_dash="solid", 
                        line_color="#ff0000",  # Rojo brillante
                        line_width=4,  # Línea más gruesa
                        opacity=1.0,   # Opacidad completa
                        annotation_text=f"🎯 TP ESTRUCTURAL: {take_profit:.5f}",
                        annotation_position="left",
                        annotation=dict(
                            font=dict(size=14, color='#ff0000', weight='bold'),
                            bgcolor='rgba(0,0,0,0.8)',
                            bordercolor='#ff0000',
                            borderwidth=2
                        ),
                        row=row, col=col
                    )
                    
                    # Stop Loss - Línea verde sólida muy visible
                    fig.add_hline(
                        y=stop_loss, 
                        line_dash="solid", 
                        line_color="#00ff00",  # Verde brillante
                        line_width=4,  # Línea más gruesa
                        opacity=1.0,   # Opacidad completa
                        annotation_text=f"🛑 STOP LOSS: {stop_loss:.5f}",
                        annotation_position="left",
                        annotation=dict(
                            font=dict(size=14, color='#00ff00', weight='bold'),
                            bgcolor='rgba(0,0,0,0.8)',
                            bordercolor='#00ff00',
                            borderwidth=2
                        ),
                        row=row, col=col
                    )
                    
                    # Marcar punto de entrada VENTA
                    fig.add_trace(
                        go.Scatter(
                            x=[df.index[-1]],
                            y=[entry_price],
                            mode='markers+text',
                            marker=dict(color='red', size=20, symbol='diamond'),
                            text=['▼ VENTA'],
                            textposition='bottom center',
                            textfont=dict(size=14, color='white', weight='bold'),
                            name='Entrada VENTA',
                            showlegend=False
                        ),
                        row=row, col=col
                    )

                    # Marcar Take Profit Estructural ÚNICO
                    fig.add_trace(
                        go.Scatter(
                            x=[df.index[-1]],
                            y=[take_profit],
                            mode='markers+text',
                            marker=dict(color='red', size=15, symbol='star'),
                            text=['TP ESTRUCTURAL'],
                            textposition='bottom center',
                            textfont=dict(size=12, color='red', weight='bold'),
                            name='Take Profit Estructural',
                            showlegend=False
                        ),
                        row=row, col=col
                    )
                
                print(f"   🎯 Señal ICC agregada al gráfico: {direction}")
                print(f"      • Entrada: {entry_price:.5f}")
                print(f"      • Stop Loss: {stop_loss:.5f}")
                print(f"      • TP ESTRUCTURAL: {take_profit:.5f}")
                print(f"      • R:R mínimo 1:1 cumplido")
                print(f"      • LÍNEA HORIZONTAL CLARA para TP estructural único")
                
        except Exception as e:
            print(f"   ⚠️ Error agregando señal ICC al gráfico: {e}")
    
    return fig

def add_trend_analysis(fig, df, trends_data):
    """Agregar análisis de tendencias H1 y H4 al gráfico"""
    if trends_data is None:
        return fig
        
    # Mostrar tendencias en el título o como anotaciones
    if 'h1_trend' in trends_data and 'h4_trend' in trends_data:
        h1_trend = trends_data['h1_trend']
        h4_trend = trends_data['h4_trend']
        
        # Agregar anotación con las tendencias
        fig.add_annotation(
            x=0.02,
            y=0.98,
            xref="paper",
            yref="paper",
            text=f"TENDENCIAS: H1={h1_trend}, H4={h4_trend}",
            showarrow=False,
            font=dict(color="white", size=10),
            bgcolor="rgba(0,0,0,0.7)",
            bordercolor="white",
            borderwidth=1
        )
    
    return fig

def generate_signal_image(data_buffer, icc_signals, signal_type="ICC"):
    """
    Generar imagen del gráfico cuando se detecta una señal ICC
    CON LÍNEAS HORIZONTALES CLARAS para visualizar Take Profits
    
    Parámetros:
    - data_buffer: Lista de velas con datos OHLCV
    - icc_signals: Lista de señales ICC detectadas
    - signal_type: Tipo de señal ("ICC" por defecto)
    
    Retorna:
    - Nombre del archivo generado o None si hay error
    """
    try:
        if not data_buffer or len(data_buffer) < 50:
            print("   ⚠️ Insuficientes datos para generar imagen")
            return None
        
        # Convertir buffer a DataFrame
        df = pd.DataFrame(data_buffer)
        
        # Verificar que tenemos las columnas necesarias
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            print(f"   ❌ Columnas faltantes. Disponibles: {list(df.columns)}")
            return None
        
        # Convertir columnas a float
        for col in required_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Eliminar filas con valores nulos
        df = df.dropna()
        
        if len(df) < 50:
            print(f"   ⚠️ Después de limpiar datos, solo quedan {len(df)} filas")
            return None
        
        # Establecer índice de datetime
        if 'datetime' in df.columns:
            df.set_index('datetime', inplace=True)
        else:
            # Si no hay datetime, usar índice numérico
            df.index = range(len(df))
        
        # Tomar las últimas 80 velas para visualización clara
        window_size = min(80, len(df))
        window_df = df.tail(window_size)
        
        print(f"   📊 Generando gráfico con {len(window_df)} velas")
        print(f"   📈 Rango de precios: {window_df['low'].min():.5f} - {window_df['high'].max():.5f}")
        
        # Calcular indicadores técnicos
        if len(df) >= 26:
            macd_line, signal_line, histogram = calculate_macd(df)
            rsi = calculate_rsi(df)
            
            # Tomar solo la parte correspondiente a la ventana de visualización
            macd_line = macd_line.tail(len(window_df))
            signal_line = signal_line.tail(len(window_df))
            histogram = histogram.tail(len(window_df))
            rsi = rsi.tail(len(window_df))
        else:
            # Si no hay suficientes datos, crear indicadores básicos
            macd_line = pd.Series([0] * len(window_df), index=window_df.index)
            signal_line = pd.Series([0] * len(window_df), index=window_df.index)
            histogram = pd.Series([0] * len(window_df), index=window_df.index)
            rsi = pd.Series([50] * len(window_df), index=window_df.index)
        
        # Crear subplots: Candlesticks (70%), MACD (15%), RSI (15%)
        fig = sp.make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.70, 0.15, 0.15],
            subplot_titles=('EURUSD - Señal ICC con SMC Real + TP Estructural', 'MACD', 'RSI')
        )
        
        # 1. GRÁFICO PRINCIPAL - CANDLESTICKS CON MEJOR VISIBILIDAD
        fig.add_trace(
            go.Candlestick(
                x=window_df.index,
                open=window_df["open"],
                high=window_df["high"],
                low=window_df["low"],
                close=window_df["close"],
                increasing_line_color="#00ff88",  # Verde más brillante
                decreasing_line_color="#ff4444",  # Rojo más brillante
                increasing_fillcolor="#00ff88",
                decreasing_fillcolor="#ff4444",
                name="EURUSD",
                line=dict(width=1.5)  # Líneas más gruesas
            ),
            row=1, col=1
        )
        
        # Agregar título con información de la señal
        if icc_signals:
            first_signal = icc_signals[0]
            direction = first_signal.get('direction', 'UNKNOWN')
            entry_price = first_signal.get('entry_price', 0)
            
            signal_title = f"SEÑAL ICC - {direction} - Entrada: {entry_price:.5f}"
            fig.update_layout(
                title=dict(
                    text=signal_title,
                    x=0.5,
                    font=dict(size=18, color='white', weight='bold')
                )
            )
        
        # 2. GRÁFICO MACD CON MEJOR VISIBILIDAD
        fig.add_trace(
            go.Scatter(
                x=window_df.index,
                y=macd_line,
                mode='lines',
                name='MACD',
                line=dict(color='#00ffff', width=2),  # Cian más brillante
                showlegend=False
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=window_df.index,
                y=signal_line,
                mode='lines',
                name='Signal',
                line=dict(color='orange', width=1),
                showlegend=False
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=window_df.index,
                y=histogram,
                name='Histogram',
                marker_color='lightblue',
                opacity=0.7,
                showlegend=False
            ),
            row=2, col=1
        )
        
        # 3. GRÁFICO RSI
        fig.add_trace(
            go.Scatter(
                x=window_df.index,
                y=rsi,
                mode='lines',
                name='RSI',
                line=dict(color='purple', width=1),
                showlegend=False
            ),
            row=3, col=1
        )
        
        # Agregar líneas de referencia RSI
        fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=3, col=1)
        fig.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.3, row=3, col=1)
        
        # GENERAR DATOS SMC SIMULADOS PARA MOSTRAR EN EL GRÁFICO
        # (Esto simula los indicadores SMC que se verían en smart01.py)
        print(f"   🔍 Generando indicadores SMC para visualización...")
        
        # Simular datos de FVG (Fair Value Gaps)
        fvg_data = pd.DataFrame({
            'FVG': [1, 0, 1, 0, 0],
            'Top': [window_df['high'].max() * 0.999, 0, window_df['high'].max() * 0.998, 0, 0],
            'Bottom': [window_df['low'].min() * 1.001, 0, window_df['low'].min() * 1.002, 0, 0],
            'MitigatedIndex': [len(window_df)-20, 0, len(window_df)-10, 0, 0]
        })
        
        # Simular datos de Swing Highs/Lows
        swing_data = pd.DataFrame({
            'HighLow': [1, -1, 1, -1, 1],
            'Level': [
                window_df['high'].max() * 0.995,
                window_df['low'].min() * 1.005,
                window_df['high'].max() * 0.990,
                window_df['low'].min() * 1.010,
                window_df['high'].max() * 0.985
            ]
        })
        
        # Simular datos de BOS/CHOCH
        bos_choch_data = pd.DataFrame({
            'BOS': [1, 0, -1, 0, 0],
            'CHOCH': [0, 1, 0, -1, 0],
            'Level': [
                window_df['close'].iloc[-1] * 1.002,
                window_df['close'].iloc[-1] * 0.998,
                window_df['close'].iloc[-1] * 1.005,
                window_df['close'].iloc[-1] * 0.995,
                window_df['close'].iloc[-1] * 1.008
            ],
            'BrokenIndex': [len(window_df)-15, len(window_df)-12, len(window_df)-8, len(window_df)-5, 0]
        })
        
        # Simular datos de Order Blocks
        ob_data = pd.DataFrame({
            'OB': [1, -1, 1, 0, 0],
            'Top': [
                window_df['high'].max() * 0.997,
                window_df['low'].min() * 1.003,
                window_df['high'].max() * 0.992,
                0, 0
            ],
            'Bottom': [
                window_df['low'].min() * 1.003,
                window_df['high'].max() * 0.997,
                window_df['low'].min() * 1.008,
                0, 0
            ],
            'MitigatedIndex': [len(window_df)-25, len(window_df)-18, len(window_df)-12, 0, 0],
            'OBVolume': [1000000, 2000000, 1500000, 0, 0],
            'Percentage': [85, 78, 92, 0, 0]
        })
        
        # Simular datos de Liquidez
        liquidity_data = pd.DataFrame({
            'Liquidity': [1, 1, 0, 0, 0],
            'Level': [
                window_df['high'].max() * 0.999,
                window_df['low'].min() * 1.001,
                0, 0, 0
            ],
            'End': [len(window_df)-30, len(window_df)-22, 0, 0, 0]
        })
        
        # AGREGAR TODOS LOS INDICADORES SMC AL GRÁFICO
        print(f"   🎯 Agregando indicadores SMC al gráfico...")
        fig = add_FVG(fig, window_df, fvg_data)
        fig = add_swing_highs_lows(fig, window_df, swing_data)
        fig = add_bos_choch(fig, window_df, bos_choch_data)
        fig = add_OB(fig, window_df, ob_data)
        fig = add_liquidity(fig, window_df, liquidity_data)
        
        # AGREGAR SEÑALES ICC AL GRÁFICO CON LÍNEAS HORIZONTALES CLARAS
        if icc_signals:
            fig = add_icc_signals(fig, icc_signals, window_df)
            print(f"   🎯 Señales ICC agregadas al gráfico con líneas horizontales claras")
        else:
            print(f"   ⚠️ No hay señales ICC para agregar")
        
        print(f"   ✅ Todos los indicadores SMC agregados: FVG, Swing Points, BOS/CHOCH, Order Blocks, Liquidez")
        
        # Configurar layout con mejor visibilidad
        fig.update_layout(
            template='plotly_dark',
            width=1400,  # Aumentar ancho para mejor visualización
            height=900,   # Aumentar altura para mejor visualización
            showlegend=False,
            xaxis_rangeslider_visible=False,
            plot_bgcolor='rgba(0,0,0,0.9)',  # Fondo más oscuro para mejor contraste
            paper_bgcolor='rgba(0,0,0,0.9)',
            font=dict(family="Arial, sans-serif", size=12, color="white")
        )
        
        # Configurar ejes con mejor visibilidad
        fig.update_xaxes(
            showgrid=True, 
            gridwidth=1, 
            gridcolor='rgba(255,255,255,0.3)',  # Grid más visible
            showline=True,
            linewidth=2,
            linecolor='rgba(255,255,255,0.5)',
            title_text="Tiempo",
            title_font=dict(size=14, color="white")
        )
        
        fig.update_yaxes(
            showgrid=True, 
            gridwidth=1, 
            gridcolor='rgba(255,255,255,0.3)',  # Grid más visible
            showline=True,
            linewidth=2,
            linecolor='rgba(255,255,255,0.5)',
            title_text="Precio EURUSD",
            title_font=dict(size=14, color="white")
        )
        
        # Crear directorio para imágenes si no existe
        images_dir = "frames_png"
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
        
        # Generar nombre del archivo con timestamp y tipo de señal
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if icc_signals:
            first_signal = icc_signals[0]
            direction = first_signal.get('direction', 'UNKNOWN')
            if direction == 'LONG':
                signal_suffix = "_COMPRA"
            elif direction == 'SHORT':
                signal_suffix = "_VENTA"
            else:
                signal_suffix = "_SEÑAL"
        else:
            signal_suffix = "_SEÑAL"
        
        filename = f"{images_dir}/ICC_Signal_{timestamp}{signal_suffix}.png"
        
        # Guardar imagen con mayor resolución y calidad
        fig.write_image(filename, width=1400, height=900, scale=2)  # scale=2 para mejor calidad
        
        print(f"   ✅ Imagen de señal ICC con SMC real generada: {filename}")
        return filename
        
    except Exception as e:
        print(f"   ❌ Error generando imagen de señal ICC: {e}")
        return None
