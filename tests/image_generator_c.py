# -*- coding: utf-8 -*-
"""
Generador de gráficos SMC (Smart Money Concepts)
Crea gráficos profesionales con indicadores técnicos para análisis de mercado
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import numpy as np
from datetime import datetime
import os

def generate_smc_chart(
    window_df,
    macd_line,
    signal_line,
    histogram,
    rsi,
    current_trend,
    current_trend_15m,
    current_trend_1h,
    current_trend_4h,
    fvg_data,
    swing_highs_lows_data,
    bos_choch_data,
    ob_data,
    liquidity_data,
    previous_high_low_data,
    sessions,
    retracements,
    output_filename
):
    """
    Genera un gráfico completo de Smart Money Concepts con todos los indicadores
    
    Args:
        window_df: DataFrame con datos de precios
        macd_line: Línea MACD
        signal_line: Línea de señal MACD
        histogram: Histograma MACD
        rsi: Valores RSI
        current_trend: Tendencia actual
        current_trend_15m: Tendencia 15m
        current_trend_1h: Tendencia 1h
        current_trend_4h: Tendencia 4h
        fvg_data: Datos de Fair Value Gaps
        swing_highs_lows_data: Datos de swing highs/lows
        bos_choch_data: Datos de BOS/CHoCH
        ob_data: Datos de Order Blocks
        liquidity_data: Datos de liquidez
        previous_high_low_data: Datos de máximos/mínimos anteriores
        sessions: Datos de sesiones
        retracements: Datos de retrocesos
        output_filename: Nombre del archivo de salida
    """
    
    try:
        print(f"🔍 Generando gráfico para: {output_filename}")
        print(f"📊 DataFrame shape: {window_df.shape}")
        print(f"📊 Columnas disponibles: {list(window_df.columns)}")
        
        # Verificar que el DataFrame tenga las columnas necesarias
        required_columns = ['open', 'high', 'low', 'close']
        missing_columns = [col for col in required_columns if col not in window_df.columns]
        if missing_columns:
            print(f"⚠️ Columnas faltantes en window_df: {missing_columns}")
            print(f"📊 Columnas disponibles: {list(window_df.columns)}")
            return
        
        # Crear figura con subplots
        fig = make_subplots(
            rows=4, cols=1,
            row_heights=[0.5, 0.2, 0.15, 0.15],
            subplot_titles=(
                'Precio con Smart Money Concepts',
                'MACD',
                'RSI',
                'Volumen'
            ),
            vertical_spacing=0.08
        )
        
        # === GRÁFICO PRINCIPAL (Precio) ===
        # Gráfico de velas
        fig.add_trace(go.Candlestick(
            x=window_df.index,
            open=window_df['open'],
            high=window_df['high'],
            low=window_df['low'],
            close=window_df['close'],
            name='Precio',
            increasing_line_color='#00ff88',
            decreasing_line_color='#ff4444'
        ), row=1, col=1)
        
        # Agregar Order Blocks si existen
        if ob_data is not None and len(ob_data) > 0:
            for _, ob in ob_data.iterrows():
                color = 'rgba(0, 255, 136, 0.3)' if ob['type'] == 'bullish' else 'rgba(255, 68, 68, 0.3)'
                fig.add_shape(
                    type="rect",
                    x0=ob['start_time'], x1=ob['end_time'],
                    y0=ob['low'], y1=ob['high'],
                    fillcolor=color,
                    line=dict(width=0),
                    row=1, col=1
                )
        
        # Agregar Fair Value Gaps si existen
        if fvg_data is not None and len(fvg_data) > 0:
            for _, fvg in fvg_data.iterrows():
                color = 'rgba(0, 255, 136, 0.2)' if fvg['type'] == 'bullish' else 'rgba(255, 68, 68, 0.2)'
                fig.add_shape(
                    type="rect",
                    x0=fvg['start_time'], x1=fvg['end_time'],
                    y0=fvg['low'], y1=fvg['high'],
                    fillcolor=color,
                    line=dict(width=0),
                    row=1, col=1
                )
        
        # Agregar swing highs/lows
        if swing_highs_lows_data is not None and len(swing_highs_lows_data) > 0:
            swing_highs = swing_highs_lows_data[swing_highs_lows_data['type'] == 'high']
            swing_lows = swing_highs_lows_data[swing_highs_lows_data['type'] == 'low']
            
            if len(swing_highs) > 0:
                fig.add_trace(go.Scatter(
                    x=swing_highs['time'],
                    y=swing_highs['price'],
                    mode='markers',
                    marker=dict(color='red', size=8, symbol='triangle-down'),
                    name='Swing Highs',
                    showlegend=True
                ), row=1, col=1)
            
            if len(swing_lows) > 0:
                fig.add_trace(go.Scatter(
                    x=swing_lows['time'],
                    y=swing_lows['price'],
                    mode='markers',
                    marker=dict(color='green', size=8, symbol='triangle-up'),
                    name='Swing Lows',
                    showlegend=True
                ), row=1, col=1)
        
        # === GRÁFICO MACD ===
        if macd_line is not None and signal_line is not None:
            fig.add_trace(go.Scatter(
                x=window_df.index,
                y=macd_line,
                mode='lines',
                name='MACD',
                line=dict(color='blue', width=2)
            ), row=2, col=1)
            
            fig.add_trace(go.Scatter(
                x=window_df.index,
                y=signal_line,
                mode='lines',
                name='Signal',
                line=dict(color='red', width=2)
            ), row=2, col=1)
            
            # Histograma MACD
            if histogram is not None:
                colors = ['green' if h >= 0 else 'red' for h in histogram]
                fig.add_trace(go.Bar(
                    x=window_df.index,
                    y=histogram,
                    name='MACD Histogram',
                    marker_color=colors,
                    opacity=0.7
                ), row=2, col=1)
        
        # === GRÁFICO RSI ===
        if rsi is not None:
            fig.add_trace(go.Scatter(
                x=window_df.index,
                y=rsi,
                mode='lines',
                name='RSI',
                line=dict(color='purple', width=2)
            ), row=3, col=1)
            
            # Líneas de sobrecompra y sobreventa
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
        
        # === GRÁFICO VOLUMEN ===
        if 'volume' in window_df.columns:
            fig.add_trace(go.Bar(
                x=window_df.index,
                y=window_df['volume'],
                name='Volumen',
                marker_color='lightblue',
                opacity=0.7
            ), row=4, col=1)
        
        # === CONFIGURACIÓN DEL LAYOUT ===
        fig.update_layout(
            title={
                'text': f'Smart Money Concepts Analysis - {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16}
            },
            height=1200,
            width=1600,
            showlegend=True,
            template='plotly_dark',
            xaxis_rangeslider_visible=False
        )
        
        # Configurar ejes
        fig.update_xaxes(title_text="Tiempo", row=4, col=1)
        fig.update_yaxes(title_text="Precio ($)", row=1, col=1)
        fig.update_yaxes(title_text="MACD", row=2, col=1)
        fig.update_yaxes(title_text="RSI", row=3, col=1)
        fig.update_yaxes(title_text="Volumen", row=4, col=1)
        
        # Configurar rangos de RSI
        fig.update_yaxes(range=[0, 100], row=3, col=1)
        
        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        print(f"📁 Directorio creado/verificado: {os.path.dirname(output_filename)}")
        
        # Guardar como imagen
        print(f"💾 Guardando imagen en: {output_filename}")
        pio.write_image(fig, output_filename, format='png', width=1600, height=1200, scale=2)
        
        # Verificar que el archivo se creó
        if os.path.exists(output_filename):
            file_size = os.path.getsize(output_filename)
            print(f"✅ Gráfico SMC guardado exitosamente: {output_filename} ({file_size} bytes)")
        else:
            print(f"❌ Error: El archivo no se creó: {output_filename}")
        
    except Exception as e:
        print(f"❌ Error al generar gráfico SMC: {str(e)}")
        raise e
