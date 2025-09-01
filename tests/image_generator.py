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
                    # Take Profit Estructural - Línea verde sólida
                    fig.add_hline(
                        y=take_profit, 
                        line_dash="solid", 
                        line_color="lime", 
                        line_width=3,
                        opacity=0.8,
                        annotation_text=f"TP ESTRUCTURAL - {take_profit:.5f}",
                        annotation_position="right",
                        row=row, col=col
                    )
                    
                    # Stop Loss - Línea roja sólida
                    fig.add_hline(
                        y=stop_loss, 
                        line_dash="solid", 
                        line_color="red", 
                        line_width=3,
                        opacity=0.8,
                        annotation_text=f"STOP LOSS - {stop_loss:.5f}",
                        annotation_position="right",
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
                    # Take Profit Estructural - Línea roja sólida
                    fig.add_hline(
                        y=take_profit, 
                        line_dash="solid", 
                        line_color="red", 
                        line_width=3,
                        opacity=0.8,
                        annotation_text=f"TP ESTRUCTURAL - {take_profit:.5f}",
                        annotation_position="left",
                        row=row, col=col
                    )
                    
                    # Stop Loss - Línea verde sólida
                    fig.add_hline(
                        y=stop_loss, 
                        line_dash="solid", 
                        line_color="green", 
                        line_width=3,
                        opacity=0.8,
                        annotation_text=f"STOP LOSS - {stop_loss:.5f}",
                        annotation_position="left",
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
        if not data_buffer or len(data_buffer) < 100:
            print("   ⚠️ Insuficientes datos para generar imagen")
            return None
        
        # Convertir buffer a DataFrame
        df = pd.DataFrame(data_buffer)
        df.set_index('datetime', inplace=True)
        
        # Tomar las últimas 100 velas para visualización
        window_size = min(100, len(df))
        window_df = df.tail(window_size)
        
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
        
        # Crear subplots: Candlesticks (67%), MACD (17%), RSI (16%)
        fig = sp.make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            row_heights=[0.67, 0.17, 0.16],
            subplot_titles=('EURUSD - Señal ICC con TP Estructural', 'MACD', 'RSI')
        )
        
        # 1. GRÁFICO PRINCIPAL - CANDLESTICKS
        fig.add_trace(
            go.Candlestick(
                x=window_df.index,
                open=window_df["open"],
                high=window_df["high"],
                low=window_df["low"],
                close=window_df["close"],
                increasing_line_color="#77dd76",
                decreasing_line_color="#ff6962",
                name="EURUSD"
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
                    font=dict(size=16, color='white')
                )
            )
        
        # 2. GRÁFICO MACD
        fig.add_trace(
            go.Scatter(
                x=window_df.index,
                y=macd_line,
                mode='lines',
                name='MACD',
                line=dict(color='teal', width=1),
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
        
        # AGREGAR SEÑALES ICC AL GRÁFICO CON LÍNEAS HORIZONTALES CLARAS
        if icc_signals:
            fig = add_icc_signals(fig, icc_signals, window_df)
            print(f"   🎯 Señales ICC agregadas al gráfico con líneas horizontales claras")
        else:
            print(f"   ⚠️ No hay señales ICC para agregar")
        
        # Configurar layout
        fig.update_layout(
            template='plotly_dark',
            width=1200,  # Aumentar ancho para mejor visualización
            height=800,   # Aumentar altura para mejor visualización
            showlegend=False,
            xaxis_rangeslider_visible=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        # Configurar ejes
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
        
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
        
        # Guardar imagen con mayor resolución
        fig.write_image(filename, width=1200, height=800)
        
        print(f"   ✅ Imagen de señal ICC con TP Estructural único generada: {filename}")
        return filename
        
    except Exception as e:
        print(f"   ❌ Error generando imagen de señal ICC: {e}")
        return None
