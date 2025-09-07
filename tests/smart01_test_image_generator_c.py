import pandas as pd
import plotly.graph_objects as go
import sys
import os
from datetime import datetime
import numpy as np
import time
from io import BytesIO
from PIL import Image
import plotly.io as pio
from tqdm import tqdm
import datetime

# Importar paquetes asumiendo ejecución como módulo (python -m tests.smart01)
from smartmoneyconcepts.smc import smc
from smartmoneyconcepts.market_analysis_lib import MarketAnalysisLib
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from image_generator_c import generate_smc_chart

# Importar estrategia ICC para obtener datos SMC reales
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from estrategia.icc import ICCStrategy



# ============================================================================
# FUNCIONES DE CÁLCULO DE INDICADORES TÉCNICOS
# ============================================================================

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




def calculate_hybrid_trend(df, timeframe_name, market_analysis_lib):
    """
    Calcular tendencia usando Smart Money Concepts (SMC) desde market_analysis_lib
    Simplificado para devolver solo -1 (bajista), 0 (lateral), 1 (alcista)
    
    Parámetros:
    df: DataFrame del timeframe actual
    timeframe_name: Nombre del timeframe (ej: '15M', '1H', '4H')
    market_analysis_lib: Instancia de MarketAnalysisLib
    """
    try:
        # Usar la función detect_trend de market_analysis_lib con método 'structural'
        trend_result = market_analysis_lib.detect_trend(df, method='structural')
        
        # Obtener el valor de tendencia actual (última vela)
        current_trend = trend_result['trend'].iloc[-1]
        
        # Convertir a valores claros -1, 0, 1 según especificación del usuario
        if current_trend > 0.5:
            final_trend = 1  # ALCISTA
        elif current_trend < -0.5:
            final_trend = -1  # BAJISTA
        else:
            final_trend = 0  # LATERAL
        
        print(f"DEBUG {timeframe_name}: SMC detectó tendencia: {final_trend}")
        print(f"   📊 Analizando {len(df)} velas con método 'structural' (HH+HL, LL+LH, BOS, CHoCH)")
        
        # Crear DataFrame de tendencia simplificado
        trend_data = pd.DataFrame({
            'trend': [final_trend] * len(df)
        }, index=df.index)
        
        return trend_data
        
    except Exception as e:
        print(f"Error calculando tendencia SMC para {timeframe_name}: {e}")
        # Retornar tendencia neutral en caso de error
        neutral_trend = pd.DataFrame({
            'trend': [0] * len(df)
        }, index=df.index)
        return neutral_trend

def analyze_simple_price_trend(window_df):
    """
    Análisis simple de tendencia basado en precio cuando no hay estructura SMC clara
    """
    if len(window_df) < 10:
        return 0
    
    # Calcular cambio de precio en las últimas 10 velas
    recent_prices = window_df['close'].tail(10)
    price_change = recent_prices.iloc[-1] - recent_prices.iloc[0]
    price_change_pct = (price_change / recent_prices.iloc[0]) * 100
    
    # Calcular medias móviles simples
    ma_short = window_df['close'].rolling(window=5).mean()
    ma_long = window_df['close'].rolling(window=10).mean()
    
    # Determinar tendencia por precios
    if (ma_short.iloc[-1] > ma_long.iloc[-1] and price_change_pct > 0.1):
        return 1  # Alcista
    elif (ma_short.iloc[-1] < ma_long.iloc[-1] and price_change_pct < -0.1):
        return -1  # Bajista
    else:
        return 0  # Lateral




def add_previous_high_low(fig, df, previous_high_low_data):
    window_size = len(df)
    
    # Asegurarse de que previous_high_low_data use los mismos índices que df
    previous_high_low_data = previous_high_low_data.reset_index(drop=True)
    
    # Obtener series de máximos y mínimos
    high = previous_high_low_data["PreviousHigh"]
    low = previous_high_low_data["PreviousLow"]

    # Procesar máximos previos
    high_levels = []
    high_indexes = []
    for i in range(len(high)):
        if i >= window_size:
            break
        if (not pd.isna(high.iloc[i]) and 
            high.iloc[i] != (high_levels[-1] if high_levels else None)):
            high_levels.append(high.iloc[i])
            high_indexes.append(i)

    # Procesar mínimos previos
    low_levels = [] 
    low_indexes = []
    for i in range(len(low)):
        if i >= window_size:
            break
        if (not pd.isna(low.iloc[i]) and 
            low.iloc[i] != (low_levels[-1] if low_levels else None)):
            low_levels.append(low.iloc[i])
            low_indexes.append(i)

    # Dibujar líneas de máximos previos
    for i in range(len(high_indexes)-1):
        if high_indexes[i] >= window_size or high_indexes[i+1] >= window_size:
            continue
            
        fig.add_trace(
            go.Scatter(
                x=[df.index[high_indexes[i]], df.index[high_indexes[i+1]]],
                y=[high_levels[i], high_levels[i]],
                mode="lines",
                line=dict(
                    color="rgba(255, 255, 255, 0.2)",
                ),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[df.index[high_indexes[i+1]]],
                y=[high_levels[i]],
                mode="text",
                text="PH",
                textposition="top center",
                textfont=dict(color="rgba(255, 255, 255, 0.4)", size=8),
            )
        )

    # Dibujar líneas de mínimos previos
    for i in range(len(low_indexes)-1):
        if low_indexes[i] >= window_size or low_indexes[i+1] >= window_size:
            continue
            
        fig.add_trace(
            go.Scatter(
                x=[df.index[low_indexes[i]], df.index[low_indexes[i+1]]],
                y=[low_levels[i], low_levels[i]],
                mode="lines",
                line=dict(
                    color="rgba(255, 255, 255, 0.2)",
                ),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[df.index[low_indexes[i+1]]],
                y=[low_levels[i]],
                mode="text",
                text="PL",
                textposition="bottom center",
                textfont=dict(color="rgba(255, 255, 255, 0.4)", size=8),
            )
        )

    return fig


def add_sessions(fig, df, sessions):
    window_size = len(df)
    
    # Asegurarse de que sessions use los mismos índices que df
    sessions = sessions.reset_index(drop=True)
    
    for i in range(len(sessions) - 1):
        if i >= window_size - 1:  # -1 porque necesitamos i+1 para el x1
            break
            
        if sessions["Active"].iloc[i] == 1:
            fig.add_shape(
                type="rect",
                x0=df.index[i],
                y0=sessions["Low"].iloc[i],
                x1=df.index[i + 1],
                y1=sessions["High"].iloc[i],
                line=dict(width=0),
                fillcolor="#16866E",
                opacity=0.2,
            )
    return fig


def add_retracements(fig, df, retracements):
    window_size = len(df)
    
    # Asegurarse de que retracements use los mismos índices que df
    retracements = retracements.reset_index(drop=True)
    
    for i in range(len(retracements)):
        if i >= window_size:
            break
            
        next_direction = (
            retracements["Direction"].iloc[i + 1]
            if i < len(retracements) - 1
            else 0
        )
        current_direction = retracements["Direction"].iloc[i]
        
        # Verificar condiciones para mostrar el retroceso
        if (
            (next_direction != current_direction or i == len(retracements) - 1) and
            current_direction != 0 and
            (next_direction if i < len(retracements) - 1 else current_direction) != 0
        ):
            # Determinar la posición Y basada en la dirección
            y_position = (
                df["high"].iloc[i]
                if current_direction == -1
                else df["low"].iloc[i]
            )
            
            # Agregar anotación con porcentajes de retroceso
            fig.add_annotation(
                x=df.index[i],
                y=y_position,
                xref="x",
                yref="y",
                text=(
                    f"C:{retracements['CurrentRetracement%'].iloc[i]}%<br>"
                    f"D:{retracements['DeepestRetracement%'].iloc[i]}%"
                ),
                font=dict(color="rgba(255, 255, 255, 0.4)", size=8),
                showarrow=False,
            )
    return fig


# get the data
def import_data():
    # Usar el archivo CSV exportado de MT5 con datos de 5 minutos (40,000 velas)
    csv_path = "tests/test_data/EURUSD/EURUSD_5M_2025_filtrado_fast.csv"
    """Importa datos desde CSV - procesados igual que los datos de Binance"""
    # Leer el CSV desde el directorio raíz
    df = pd.read_csv(csv_path, index_col="datetime")
    
    # Convertir todas las columnas a float (igual que en Binance)
    df = df.astype(float)    
    # Asegurar que las columnas estén en el orden correcto
    df = df[["open", "high", "low", "close", "volume"]]    
    # Convertir el índice a datetime y luego a string con formato específico (igual que Binance)
    df.index = pd.to_datetime(df.index)
    df.index = df.index.strftime("%Y-%m-%d %H:%M:%S")    
    
    # Para 5 minutos: tomar las últimas 500 velas para tener más contexto
    df_5m = df.tail(500)
    
    # Para 15 minutos: agregar 3 velas de 5M para crear 1 vela de 15M
    # Tomamos las últimas 1500 velas para tener más contexto (500 velas de 15M)
    df_extended = df.tail(1500)
    
    # Crear DataFrame de 15M agregando cada 3 velas de 5M de manera manual
    df_15m = pd.DataFrame()
    
    # Agregar cada 3 velas de 5M para crear 1 vela de 15M
    open_prices = []
    high_prices = []
    low_prices = []
    close_prices = []
    volume_prices = []
    time_index = []
    
    for i in range(0, len(df_extended), 3):
        if i + 2 < len(df_extended):  # Asegurar que tenemos 3 velas
            # Open: primera vela del grupo
            open_prices.append(df_extended['open'].iloc[i])
            # High: máximo de las 3 velas
            high_prices.append(df_extended['high'].iloc[i:i+3].max())
            # Low: mínimo de las 3 velas
            low_prices.append(df_extended['low'].iloc[i:i+3].min())
            # Close: última vela del grupo
            close_prices.append(df_extended['close'].iloc[i+2])
            # Volume: suma de las 3 velas
            volume_prices.append(df_extended['volume'].iloc[i:i+3].sum())
            # Time: tiempo de la primera vela del grupo
            time_index.append(df_extended.index[i])
    
    df_15m['open'] = open_prices
    df_15m['high'] = high_prices
    df_15m['low'] = low_prices
    df_15m['close'] = close_prices
    df_15m['volume'] = volume_prices
    df_15m.index = time_index
    
    # Tomar las últimas 500 velas de 15M para tener más contexto
    df_15m = df_15m.tail(500)
    
    # Para 1 hora: agregar 12 velas de 5M para crear 1 vela de 1H
    # Tomamos las últimas 6000 velas para tener más contexto (500 velas de 1H)
    df_extended_1h = df.tail(6000)
    
    # Crear DataFrame de 1H agregando cada 12 velas de 5M
    df_1h = pd.DataFrame()
    open_prices_1h = []
    high_prices_1h = []
    low_prices_1h = []
    close_prices_1h = []
    volume_prices_1h = []
    time_index_1h = []
    
    for i in range(0, len(df_extended_1h), 12):
        if i + 11 < len(df_extended_1h):  # Asegurar que tenemos 12 velas
            # Open: primera vela del grupo
            open_prices_1h.append(df_extended_1h['open'].iloc[i])
            # High: máximo de las 12 velas
            high_prices_1h.append(df_extended_1h['high'].iloc[i:i+12].max())
            # Low: mínimo de las 12 velas
            low_prices_1h.append(df_extended_1h['low'].iloc[i:i+12].min())
            # Close: última vela del grupo
            close_prices_1h.append(df_extended_1h['close'].iloc[i+11])
            # Volume: suma de las 12 velas
            volume_prices_1h.append(df_extended_1h['volume'].iloc[i:i+12].sum())
            # Time: tiempo de la primera vela del grupo
            time_index_1h.append(df_extended_1h.index[i])
    
    df_1h['open'] = open_prices_1h
    df_1h['high'] = high_prices_1h
    df_1h['low'] = low_prices_1h
    df_1h['close'] = close_prices_1h
    df_1h['volume'] = volume_prices_1h
    df_1h.index = time_index_1h
    
    # Tomar las últimas 500 velas de 1H
    df_1h = df_1h.tail(500)
    
    # Para 4 horas: agregar 48 velas de 5M para crear 1 vela de 4H
    # Tomamos las últimas 24000 velas para tener más contexto (500 velas de 4H)
    df_extended_4h = df.tail(24000)
    
    # Crear DataFrame de 4H agregando cada 48 velas de 5M
    df_4h = pd.DataFrame()
    open_prices_4h = []
    high_prices_4h = []
    low_prices_4h = []
    close_prices_4h = []
    volume_prices_4h = []
    time_index_4h = []
    
    for i in range(0, len(df_extended_4h), 48):
        if i + 47 < len(df_extended_4h):  # Asegurar que tenemos 48 velas
            # Open: primera vela del grupo
            open_prices_4h.append(df_extended_4h['open'].iloc[i])
            # High: máximo de las 48 velas
            high_prices_4h.append(df_extended_4h['high'].iloc[i:i+48].max())
            # Low: mínimo de las 48 velas
            low_prices_4h.append(df_extended_4h['low'].iloc[i:i+48].min())
            # Close: última vela del grupo
            close_prices_4h.append(df_extended_4h['close'].iloc[i+47])
            # Volume: suma de las 48 velas
            volume_prices_4h.append(df_extended_4h['volume'].iloc[i:i+48].sum())
            # Time: tiempo de la primera vela del grupo
            time_index_4h.append(df_extended_4h.index[i])
    
    df_4h['open'] = open_prices_4h
    df_4h['high'] = high_prices_4h
    df_4h['low'] = low_prices_4h
    df_4h['close'] = close_prices_4h
    df_4h['volume'] = volume_prices_4h
    df_4h.index = time_index_4h
    
    # Tomar las últimas 500 velas de 4H
    df_4h = df_4h.tail(500)
    
    print(f"📊 Datos cargados desde: {csv_path}")
    print(f"   📈 Total de velas en CSV: {len(df)}")
    print(f"   📈 Velas seleccionadas para 5M: {len(df_5m)} (últimas 500)")
    print(f"   📈 Velas seleccionadas para 15M: {len(df_15m)} (últimas 500)")
    print(f"   📈 Velas seleccionadas para 1H: {len(df_1h)} (últimas 500)")
    print(f"   📈 Velas seleccionadas para 4H: {len(df_4h)} (últimas 500)")
    print(f"   ⏰ Timeframes: 5 minutos (datos principales), 15M, 1H y 4H (agregados)")
    print(f"   📅 Rango 5M: {df_5m.index[0]} a {df_5m.index[-1]}")
    print(f"   📅 Rango 15M: {df_15m.index[0]} a {df_15m.index[-1]}")
    print(f"   📅 Rango 1H: {df_1h.index[0]} a {df_1h.index[-1]}")
    print(f"   📅 Rango 4H: {df_4h.index[0]} a {df_4h.index[-1]}")
    print(f"   💡 Análisis múltiple: 5M (visualización) + 15M, 1H, 4H (tendencias)")
    
    return df_5m, df_15m, df_1h, df_4h, df  # Retornar datos de todos los timeframes y CSV completo


df_5m, df_15m, df_1h, df_4h, df = import_data()

# Inicializar MarketAnalysisLib para detección de tendencias SMC
market_analysis = MarketAnalysisLib()

start_time = datetime.datetime.now()
print(f"🚀 INICIO DEL SCRIPT: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"📊 Datos 5M cargados: {len(df_5m)} filas")
print(f"📊 Datos 15M cargados: {len(df_15m)} filas")
print(f"📊 Datos 1H cargados: {len(df_1h)} filas")
print(f"📊 Datos 4H cargados: {len(df_4h)} filas")
print(f"📅 Rango 5M: {df_5m.index[0]} a {df_5m.index[-1]}")
print(f"📅 Rango 15M: {df_15m.index[0]} a {df_15m.index[-1]}")
print(f"📅 Rango 1H: {df_1h.index[0]} a {df_1h.index[-1]}")
print(f"📅 Rango 4H: {df_4h.index[0]} a {df_4h.index[-1]}")
print("=" * 80)





# DICCIONARIO GLOBAL para mantener CONTINUIDAD TEMPORAL de tendencias
# Cada vela mantiene su tendencia histórica
global_trend_history = {}

# No se calculan señales de trading (librería eliminada)
trading_signals = []
print("ℹ️ Librería de señales de trading eliminada - continuando sin señales")

frames_dir = "frames_png"
if os.path.exists(frames_dir):
    import shutil
    shutil.rmtree(frames_dir)
os.makedirs(frames_dir)

window = 100  # Ventana de visualización (últimas 100 velas)
# Generar frames desde la vela 100 en adelante para tener más PNGs
total_frames_to_generate = len(df_5m) - window  # Generar desde vela 100 hasta el final
# Iniciar desde la vela 100 (window)
start_pos = window

print(f"🎬 Generando frames PNG desde vela {start_pos} hasta {len(df_5m)}")
print(f"📊 Total de frames a generar: {total_frames_to_generate}")
print(f"🔍 Ventana de visualización: {window} velas por frame")
print(f"🔍 Datos totales disponibles: {len(df_5m)} velas para análisis SMC")
print(f"🔍 Análisis extendido: {window + 50} velas para indicadores técnicos")
print(f"🔍 Verificando cálculos de tendencia múltiple: 5M (visualización) + 15M, 1H, 4H (tendencias)")

print(f"🔄 Iniciando generación de frames...")
print(f"   📊 Posiciones a procesar: {start_pos} a {len(df_5m)}")
print(f"   ⏰ Total de frames: {total_frames_to_generate}")
print(f"   🔍 Cada frame analiza {len(df_5m)} velas pero visualiza solo {window} velas")

for pos in tqdm(range(start_pos, len(df_5m)), desc="Generando últimos frames"):
    print(f"\n🎬 Procesando frame {pos}/{len(df_5m)}...")
    
    # Calcular la ventana de análisis extendida para indicadores
    # Necesitamos al menos 50 velas antes para RSI y MACD
    analysis_start = max(0, pos - window - 50)  # 50 velas adicionales para análisis
    analysis_df = df_5m.iloc[analysis_start : pos]  # Datos para calcular indicadores
    
    # Ventana de visualización (últimas 100 velas)
    window_df = df_5m.iloc[pos - window : pos]
    
    # Calcular indicadores básicos con datos extendidos
    if len(analysis_df) >= 26:  # Mínimo para MACD (26 períodos) + RSI (14 períodos)
        macd_line, signal_line, histogram = calculate_macd(analysis_df)
        rsi = calculate_rsi(analysis_df)
        
        # Tomar solo la parte correspondiente a la ventana de visualización
        macd_line = macd_line.tail(len(window_df))
        signal_line = signal_line.tail(len(window_df))
        histogram = histogram.tail(len(window_df))
        rsi = rsi.tail(len(window_df))
        
        print(f"   📊 Análisis: {len(analysis_df)} velas, Visualización: {len(window_df)} velas")
    else:
        # Si no hay suficientes datos, crear indicadores básicos
        macd_line = pd.Series([0] * len(window_df), index=window_df.index)
        signal_line = pd.Series([0] * len(window_df), index=window_df.index)
        histogram = pd.Series([0] * len(window_df), index=window_df.index)
        rsi = pd.Series([50] * len(window_df), index=window_df.index)
    
    # Calcular tendencia usando Smart Money Concepts (SMC) - Estructura del mercado
    # IMPLEMENTAR CONTINUIDAD DE TENDENCIA para evitar cambios abruptos entre frames
    if pos >= 20:  # Necesitamos suficientes datos para identificar estructura
        try:
            # Obtener la tendencia anterior del frame previo si existe
            previous_trend = None
            if pos > start_pos:
                # Buscar la tendencia del frame anterior en el historial global
                previous_frame_pos = pos - 1
                if previous_frame_pos in global_trend_history:
                    previous_trend = global_trend_history[previous_frame_pos]
                    print(f"   🔍 Tendencia anterior del frame {previous_frame_pos}: {previous_trend}")
            
            # Analizar solo las velas hasta la posición actual del frame
            current_df = df_5m.iloc[:pos]  # Solo velas hasta la posición actual
            
            trend_result = market_analysis.detect_trend(current_df, method='structural')
            
            # Obtener el valor de tendencia actual (última vela analizada)
            current_trend = trend_result['trend'].iloc[-1]
            
            # Convertir a valores -1, 0, 1 según especificación del usuario
            if current_trend > 0.5:
                new_trend = 1  # Alcista
            elif current_trend < -0.5:
                new_trend = -1  # Bajista
            else:
                new_trend = 0  # Lateral
            
            # IMPLEMENTAR LÓGICA DE CONTINUIDAD: Solo cambiar tendencia si hay confirmación clara
            if previous_trend is not None:
                # Si hay tendencia anterior, aplicar lógica de continuidad
                if new_trend == previous_trend:
                    # Confirmación: mantener la misma tendencia
                    base_trend = new_trend
                    print(f"   ✅ Confirmación: Manteniendo tendencia {base_trend}")
                elif abs(new_trend - previous_trend) == 2:
                    # Cambio drástico (de -1 a 1 o viceversa): requerir confirmación adicional
                    # Usar análisis de precio para confirmar el cambio
                    price_confirmation = analyze_simple_price_trend(window_df)
                    if price_confirmation == new_trend:
                        base_trend = new_trend
                        print(f"   🔄 Cambio confirmado: {previous_trend} → {base_trend}")
                    else:
                        base_trend = previous_trend
                        print(f"   ⚠️ Cambio no confirmado: Manteniendo tendencia anterior {base_trend}")
                else:
                    # Cambio menor (de 0 a 1/-1 o viceversa): permitir cambio gradual
                    base_trend = new_trend
                    print(f"   🔄 Cambio gradual: {previous_trend} → {base_trend}")
            else:
                # Primer frame: usar la tendencia detectada
                base_trend = new_trend
                print(f"   🆕 Primer frame: Estableciendo tendencia {base_trend}")
            
            print(f"   🔍 SMC detectó: Tendencia={new_trend}, Aplicando: {base_trend}")
            print(f"   📊 Analizando {len(current_df)} velas hasta posición {pos} con método 'structural'")
            print(f"   📊 Última vela analizada: {current_df.index[-1]}")
            
        except Exception as e:
            print(f"   ⚠️ Error en SMC, usando análisis simple: {e}")
            # Fallback a análisis simple si SMC falla
            base_trend = analyze_simple_price_trend(window_df)
    else:
        base_trend = 0
    
    # Crear tendencia con CONTINUIDAD TEMPORAL usando diccionario global
    # Almacenar la tendencia por posición de frame, no por vela individual
    
    trend_values = []
    
    # Almacenar la tendencia actual en el historial global por posición de frame
    global_trend_history[pos] = base_trend
    
    # Aplicar la misma tendencia a todas las velas del frame actual
    for i, candle_index in enumerate(window_df.index):
        trend_values.append(base_trend)
    
    trend_data = pd.DataFrame({'trend': trend_values}, index=window_df.index)
    
    # Debug: mostrar tendencia SMC actual
    print(f"   🔍 SMC detectó: Tendencia={base_trend}")
    print(f"   📊 Aplicando tendencia {base_trend} a todas las velas del frame actual")
    print(f"   📊 Historial global: {len(global_trend_history)} frames analizados")
    
   
    

    # Agregar indicador de tendencia de 5M directamente en el gráfico de velas
    current_trend = trend_data['trend'].iloc[-1] if len(trend_data) > 0 else 0
    
    # Inicializar variables de tendencia para múltiples timeframes
    trend_type_15m = "15M:NA"
    trend_type_1h = "1H:NA"
    trend_type_4h = "4H:NA"
    current_trend_15m = 0
    current_trend_1h = 0
    current_trend_4h = 0
    
    # Agregar indicador de tendencia de 15M en la parte inferior derecha del gráfico
    # Calcular tendencia de 15M basada en los datos agregados
    try:
        # Encontrar la posición correspondiente en los datos de 15M
        current_time = window_df.index[-1]
        # Buscar la vela de 15M más cercana
        closest_15m_idx = None
        for i, time_15m in enumerate(df_15m.index):
            if pd.to_datetime(time_15m) >= pd.to_datetime(current_time):
                closest_15m_idx = i
                break
        
        if closest_15m_idx is not None and closest_15m_idx < len(df_15m):
            # Analizar tendencia de 15M usando las velas hasta la posición actual
            current_df_15m = df_15m.iloc[:closest_15m_idx + 1]
            if len(current_df_15m) >= 20:
                trend_result_15m = market_analysis.detect_trend(current_df_15m, method='structural')
                current_trend_15m = trend_result_15m['trend'].iloc[-1]
                print(f"   🔍 15M detectó: Tendencia={current_trend_15m:.2f} → {trend_type_15m}")
            else:
                trend_type_15m = "15M:NA"
                print(f"   ⚠️ Insuficientes datos para 15M: {len(current_df_15m)} velas")
        else:
            trend_type_15m = "15M:NA"
            print(f"   ⚠️ No se pudo mapear tiempo 5M a 15M")
             
    except Exception as e:
        print(f"   ⚠️ Error calculando tendencia 15M: {e}")
        trend_type_15m = "15M:ERROR"
     
    # Calcular tendencia de 1H
    try:
        # Encontrar la posición correspondiente en los datos de 1H
        current_time = window_df.index[-1]
        # Buscar la vela de 1H más cercana
        closest_1h_idx = None
        for i, time_1h in enumerate(df_1h.index):
            if pd.to_datetime(time_1h) >= pd.to_datetime(current_time):
                closest_1h_idx = i
                break
        
        if closest_1h_idx is not None and closest_1h_idx < len(df_1h):
            # Analizar tendencia de 1H usando las velas hasta la posición actual
            current_df_1h = df_1h.iloc[:closest_1h_idx + 1]
            if len(current_df_1h) >= 20:
                trend_result_1h = market_analysis.detect_trend(current_df_1h, method='structural')
                current_trend_1h = trend_result_1h['trend'].iloc[-1]
                
                print(f"   🔍 1H detectó: Tendencia={current_trend_1h:.2f} → {trend_type_1h}")
            else:
                trend_type_1h = "1H:NA"
                print(f"   ⚠️ Insuficientes datos para 1H: {len(current_df_1h)} velas")
        else:
            trend_type_1h = "1H:NA"
            print(f"   ⚠️ No se pudo mapear tiempo 5M a 1H")
            
    except Exception as e:
        print(f"   ⚠️ Error calculando tendencia 1H: {e}")
        trend_type_1h = "1H:ERROR"
     
    # Calcular tendencia de 4H
    try:
        # Encontrar la posición correspondiente en los datos de 4H
        current_time = window_df.index[-1]
        # Buscar la vela de 4H más cercana
        closest_4h_idx = None
        for i, time_4h in enumerate(df_4h.index):
            if pd.to_datetime(time_4h) >= pd.to_datetime(current_time):
                closest_4h_idx = i
                break
        
        if closest_4h_idx is not None and closest_4h_idx < len(df_4h):
            # Analizar tendencia de 4H usando las velas hasta la posición actual
            current_df_4h = df_4h.iloc[:closest_4h_idx + 1]
            if len(current_df_4h) >= 20:
                trend_result_4h = market_analysis.detect_trend(current_df_4h, method='structural')
                current_trend_4h = trend_result_4h['trend'].iloc[-1]
                
               
                
                # Agregar anotación de tendencia 4H debajo de la de 1H
                # NOTA: trend_type_4h puede ser actualizado con sufijo _ALCISTA/_BAJISTA
               
                
                print(f"   🔍 4H detectó: Tendencia={current_trend_4h:.2f} → {trend_type_4h}")
            else:
                trend_type_4h = "4H:NA"
                print(f"   ⚠️ Insuficientes datos para 4H: {len(current_df_4h)} velas")
        else:
            trend_type_4h = "4H:NA"
            print(f"   ⚠️ No se pudo mapear tiempo 5M a 4H")
            
    except Exception as e:
        print(f"   ⚠️ Error calculando tendencia 4H: {e}")
        trend_type_4h = "4H:ERROR"
    
    # MEJORA: Verificar si las tendencias de 15M, 1H y 4H son idénticas y agregar sufijos
    try:
        # Solo procesar si tenemos tendencias válidas (no NA ni ERROR)
        valid_trends = []
        if 'trend_type_15m' in locals() and not trend_type_15m.endswith(('NA', 'ERROR')):
            valid_trends.append(('15M', trend_type_15m, current_trend_15m))
        if 'trend_type_1h' in locals() and not trend_type_1h.endswith(('NA', 'ERROR')):
            valid_trends.append(('1H', trend_type_1h, current_trend_1h))
        if 'trend_type_4h' in locals() and not trend_type_4h.endswith(('NA', 'ERROR')):
            valid_trends.append(('4H', trend_type_4h, current_trend_4h))
        
        # Verificar si hay al menos 2 tendencias válidas para comparar
        if len(valid_trends) >= 2:
            # Extraer solo los valores de tendencia (-1, 0, 1)
            trend_values = [trend[2] for trend in valid_trends]
            
            # Verificar si todas las tendencias son iguales y no son laterales (0)
            if len(set(trend_values)) == 1 and trend_values[0] != 0:
                # Todas las tendencias son idénticas y no son laterales
                if trend_values[0] > 0:
                    # Todas son alcistas
                    suffix = "_ALCISTA"
                    print(f"   🎯 CONFIRMACIÓN MÚLTIPLE: Todas las tendencias son ALCISTAS → Agregando sufijo {suffix}")
                else:
                    # Todas son bajistas
                    suffix = "_BAJISTA"
                    print(f"   🎯 CONFIRMACIÓN MÚLTIPLE: Todas las tendencias son BAJISTAS → Agregando sufijo {suffix}")
                
                # Aplicar sufijo a todas las tendencias válidas
                for timeframe, trend_type, trend_value in valid_trends:
                    if timeframe == '15M':
                        trend_type_15m = trend_type + suffix
                    elif timeframe == '1H':
                        trend_type_1h = trend_type + suffix
                    elif timeframe == '4H':
                        trend_type_4h = trend_type + suffix
            else:
                print(f"   📊 Tendencias mixtas: 15M={trend_values[0] if len(trend_values) > 0 else 'N/A'}, 1H={trend_values[1] if len(trend_values) > 1 else 'N/A'}, 4H={trend_values[2] if len(trend_values) > 2 else 'N/A'}")
        else:
            print(f"   ⚠️ Insuficientes tendencias válidas para comparar: {len(valid_trends)}")
            
    except Exception as e:
        print(f"   ⚠️ Error en análisis de confirmación múltiple: {e}")
    
    # Obtener datos SMC reales de la estrategia ICC
    print("   🔍 Obteniendo datos SMC reales de la estrategia ICC...")
    try:
        # Crear instancia de la estrategia ICC
        smartmoney_icc = ICCStrategy()
        
        # Obtener datos SMC reales
        smc_data = smartmoney_icc.get_smc_data(window_df, df_1h, df_4h)
        
        if smc_data:
            # Extraer datos reales de SMC
            fvg_data = smc_data.get('fvg_data', pd.DataFrame())
            swing_highs_lows_data = smc_data.get('swing_data', pd.DataFrame())
            bos_choch_data = smc_data.get('bos_choch_data', pd.DataFrame())
            ob_data = smc_data.get('order_blocks', pd.DataFrame())
            
            print(f"   ✅ Datos SMC reales obtenidos:")
            print(f"      • Fair Value Gaps: {len(fvg_data) if not fvg_data.empty else 0}")
            print(f"      • Swing Points: {len(swing_highs_lows_data) if not swing_highs_lows_data.empty else 0}")
            print(f"      • BOS/CHOCH: {len(bos_choch_data) if not bos_choch_data.empty else 0}")
            print(f"      • Order Blocks: {len(ob_data) if not ob_data.empty else 0}")
        else:
            print("   ⚠️ No se pudieron obtener datos SMC reales, usando datos vacíos")
            fvg_data = pd.DataFrame()
            swing_highs_lows_data = pd.DataFrame()
            bos_choch_data = pd.DataFrame()
            ob_data = pd.DataFrame()
            
    except Exception as e:
        print(f"   ❌ Error obteniendo datos SMC reales: {e}")
        # Fallback a datos vacíos si hay error
        fvg_data = pd.DataFrame()
        swing_highs_lows_data = pd.DataFrame()
        bos_choch_data = pd.DataFrame()
        ob_data = pd.DataFrame()
    
    # Los datos BOS/CHOCH y Order Blocks ya se obtuvieron de la estrategia ICC arriba
    
    # Crear datos vacíos para indicadores adicionales (mantener compatibilidad)
    liquidity_data = pd.DataFrame()
    previous_high_low_data = pd.DataFrame()
    sessions = pd.DataFrame()
    retracements = pd.DataFrame()
    
    # MEJORA: Renombrar archivo según confirmación múltiple de tendencias
    base_filename = f"frame_{pos:04d}"
    
    # Verificar si hay confirmación múltiple para renombrar el archivo
    file_suffix = ""
    try:
        # Solo procesar si tenemos tendencias válidas (no NA ni ERROR)
        valid_trends = []
        if 'trend_type_15m' in locals() and not trend_type_15m.endswith(('NA', 'ERROR')):
            valid_trends.append(('15M', trend_type_15m, current_trend_15m))
        if 'trend_type_1h' in locals() and not trend_type_1h.endswith(('NA', 'ERROR')):
            valid_trends.append(('1H', trend_type_1h, current_trend_1h))
        if 'trend_type_4h' in locals() and not trend_type_4h.endswith(('NA', 'ERROR')):
            valid_trends.append(('4H', trend_type_4h, current_trend_4h))
        
        # Verificar si hay al menos 2 tendencias válidas para comparar
        if len(valid_trends) >= 2:
            # Extraer solo los valores de tendencia (-1, 0, 1)
            trend_values = [trend[2] for trend in valid_trends]
            
            # Verificar si todas las tendencias son iguales y no son laterales (0)
            if len(set(trend_values)) == 1 and trend_values[0] != 0:
                # Todas las tendencias son idénticas y no son laterales
                if trend_values[0] > 0:
                    # Todas son alcistas
                    file_suffix = "_ALCISTA"
                    print(f"   🎯 CONFIRMACIÓN MÚLTIPLE: Todas las tendencias son ALCISTAS → Archivo: {base_filename}{file_suffix}.png")
                else:
                    # Todas son bajistas
                    file_suffix = "_BAJISTA"
                    print(f"   🎯 CONFIRMACIÓN MÚLTIPLE: Todas las tendencias son BAJISTAS → Archivo: {base_filename}{file_suffix}.png")
            else:
                print(f"   📊 Tendencias mixtas: No hay confirmación múltiple para renombrar archivo")
        else:
            print(f"   ⚠️ Insuficientes tendencias válidas para confirmación múltiple: {len(valid_trends)}")
            
    except Exception as e:
        print(f"   ⚠️ Error en análisis de confirmación múltiple para renombrar: {e}")
    
    # Crear nombre final del archivo
    frame_filename = f"{frames_dir}/{base_filename}{file_suffix}.png"
    
    # Guardar frame como PNG
    try:
        
        generate_smc_chart(
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
            frame_filename
        )
        # Mostrar información consolidada del frame
        current_trend = trend_data['trend'].iloc[-1] if len(trend_data) > 0 else 0
        print(f"✅ Frame {pos} guardado: {frame_filename}")
        print(f"   📊 Resumen del frame:")
        print(f"      • 5M: Tendencia: {current_trend:.2f}")
        print(f"      • 15M: Tendencia: {trend_type_15m if 'trend_type_15m' in locals() else 'N/A'}")
        print(f"      • 1H: Tendencia: {trend_type_1h if 'trend_type_1h' in locals() else 'N/A'}")
        print(f"      • 4H: Tendencia: {trend_type_4h if 'trend_type_4h' in locals() else 'N/A'}")
        
        print(f"   🎯 Progreso: {pos - start_pos + 1}/{len(df_5m) - start_pos} frames completados")
        
    except Exception as e:
        print(f"❌ Frame en posición {pos} falló: {e}")
        print(f"   🔄 Continuando con el siguiente frame...")

end_time = datetime.datetime.now()
print(f"✅ Frames PNG con CANDLESTICKS, MACD y RSI guardados en: {frames_dir}/")
print(f"📊 Total de frames generados: {len(df_5m) - start_pos}")
print(f"⏱️ Tiempo total de ejecución: {end_time - start_time}")
print("=" * 80)

# Resumen del análisis simplificado
print(f"\n🔍 RESUMEN DEL ANÁLISIS SIMPLIFICADO:")
print(f"   📅 Frames analizados: {start_pos} a {len(df_5m)} (últimos {len(df_5m) - start_pos} frames)")
print(f"   ⏰ Ventana de análisis: {window} velas por frame")
print(f"   📊 Temporalidad procesada:")
print(f"      • 5M: Últimas 500 velas del CSV (datos principales para visualización)")
print(f"      • 15M: Últimas 500 velas agregadas (datos para análisis de tendencia)")
print(f"      • 1H: Últimas 500 velas agregadas (datos para análisis de tendencia)")
print(f"      • 4H: Últimas 500 velas agregadas (datos para análisis de tendencia)")
print(f"      • Visualización: Últimas 100 velas por frame (5M)")
print(f"   🎯 Cada frame incluye:")
print(f"      • Candlesticks principales con indicadores SMC (datos 5M)")
print(f"      • Tendencia 5M en esquina inferior izquierda")
print(f"      • Tendencia 15M debajo de 5M")
print(f"      • Tendencia 1H debajo de 15M")
print(f"      • Tendencia 4H debajo de 1H")
print(f"      • MACD y RSI en paneles separados")
print(f"      • Indicadores SMC (FVG, Order Blocks, Swing Points)")
print(f"   📈 Lógica SMC implementada:")
print(f"      • Análisis múltiple: 5M (visualización) + 15M, 1H, 4H (tendencias)")
print(f"      • 5M: market_analysis_lib.detect_trend('structural') para estructura")
print(f"      • 15M, 1H, 4H: market_analysis_lib.detect_trend('structural') para tendencias")
print(f"      • Indicadores técnicos estándar (MACD, RSI)")
print(f"      • Fallback a análisis simple si SMC falla")