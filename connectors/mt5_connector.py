import pandas as pd
import numpy as np
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

from .smc import smc
from .candlestick_patterns import CandlestickPatterns

class MT5Connector:
    """
    Conector completo para MetaTrader 5 con análisis de Smart Money Concepts
    Incluye obtención de datos, análisis técnico y señales de trading
    """
    
    def __init__(self, login: int = None, password: str = None, server: str = None):
        """
        Inicializa la conexión con MetaTrader 5
        
        Parámetros:
        login: int - Número de cuenta MT5
        password: str - Contraseña de la cuenta
        server: str - Servidor del broker
        """
        self.connected = False
        self.login = login
        self.password = password
        self.server = server
        self.account_info = None
        
        # Configuración por defecto
        self.default_timeframe = mt5.TIMEFRAME_H1
        self.default_symbol = "EURUSD"
        
        # Mapeo de timeframes
        self.timeframe_map = {
            "1m": mt5.TIMEFRAME_M1,
            "5m": mt5.TIMEFRAME_M5,
            "15m": mt5.TIMEFRAME_M15,
            "30m": mt5.TIMEFRAME_M30,
            "1h": mt5.TIMEFRAME_H1,
            "4h": mt5.TIMEFRAME_H4,
            "1d": mt5.TIMEFRAME_D1,
            "1w": mt5.TIMEFRAME_W1,
            "1M": mt5.TIMEFRAME_MN1
        }
        
        # Inicializar conexión
        self.connect()
    
    def connect(self) -> bool:
        """
        Conecta con MetaTrader 5
        
        Retorna:
        bool: True si la conexión fue exitosa
        """
        try:
            # Inicializar MT5
            if not mt5.initialize():
                print(f"❌ Error al inicializar MT5: {mt5.last_error()}")
                return False
            
            # Login si se proporcionan credenciales
            if self.login and self.password and self.server:
                if not mt5.login(login=self.login, password=self.password, server=self.server):
                    print(f"❌ Error al hacer login: {mt5.last_error()}")
                    return False
                print(f"✅ Conectado a MT5 - Cuenta: {self.login}")
            else:
                print("✅ Conectado a MT5 (sin login)")
            
            # Obtener información de la cuenta
            self.account_info = mt5.account_info()
            if self.account_info:
                print(f"💰 Balance: ${self.account_info.balance:.2f}")
                print(f"💵 Equity: ${self.account_info.equity:.2f}")
            
            self.connected = True
            return True
            
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            return False
    
    def disconnect(self):
        """Desconecta de MetaTrader 5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            print("🔌 Desconectado de MT5")
    
    def get_symbols(self) -> List[str]:
        """
        Obtiene lista de símbolos disponibles
        
        Retorna:
        List[str]: Lista de símbolos
        """
        if not self.connected:
            print("❌ No conectado a MT5")
            return []
        
        symbols = mt5.symbols_get()
        return [symbol.name for symbol in symbols]
    
    def get_data(self, symbol: str, timeframe: str = "1h", bars: int = 1000, 
                 start_date: datetime = None, end_date: datetime = None) -> pd.DataFrame:
        """
        Obtiene datos históricos de un símbolo
        
        Parámetros:
        symbol: str - Símbolo a consultar
        timeframe: str - Timeframe ("1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M")
        bars: int - Número de barras a obtener
        start_date: datetime - Fecha de inicio
        end_date: datetime - Fecha de fin
        
        Retorna:
        pd.DataFrame: DataFrame con datos OHLCV
        """
        if not self.connected:
            print("❌ No conectado a MT5")
            return pd.DataFrame()
        
        try:
            # Mapear timeframe
            mt5_timeframe = self.timeframe_map.get(timeframe, mt5.TIMEFRAME_H1)
            
            # Obtener datos
            if start_date and end_date:
                rates = mt5.copy_rates_range(symbol, mt5_timeframe, start_date, end_date)
            else:
                rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, bars)
            
            if rates is None or len(rates) == 0:
                print(f"❌ No se pudieron obtener datos para {symbol}")
                return pd.DataFrame()
            
            # Convertir a DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            
            # Renombrar columnas para compatibilidad con SMC
            df.columns = ['open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']
            # Usar tick_volume como volumen (más confiable en forex)
            df = df[['open', 'high', 'low', 'close', 'tick_volume']]  # Solo OHLCV
            df = df.rename(columns={'tick_volume': 'real_volume'})  # Renombrar para compatibilidad
            
            print(f"✅ Obtenidos {len(df)} registros de {symbol} ({timeframe})")
            return df
            
        except Exception as e:
            print(f"❌ Error al obtener datos: {e}")
            return pd.DataFrame()
    
    def analyze_smc(self, df: pd.DataFrame, swing_length: int = 50) -> Dict:
        """
        Realiza análisis completo de Smart Money Concepts
        
        Parámetros:
        df: pd.DataFrame - Datos OHLCV
        swing_length: int - Longitud para swing highs/lows
        
        Retorna:
        Dict: Diccionario con todos los análisis SMC
        """
        try:
            print("🔍 Analizando Smart Money Concepts...")
            
            # Calcular swing highs/lows (base para otros indicadores)
            swing_highs_lows = smc.swing_highs_lows(df, swing_length=swing_length)
            
            # Análisis completo
            analysis = {
                'fvg': smc.fvg(df, join_consecutive=True),
                'swing_highs_lows': swing_highs_lows,
                'bos_choch': smc.bos_choch(df, swing_highs_lows),
                'ob': smc.ob(df, swing_highs_lows),
                'liquidity': smc.liquidity(df, swing_highs_lows),
                'previous_high_low': smc.previous_high_low(df, time_frame="1d"),
                'sessions': smc.sessions(df, session="London"),
                'retracements': smc.retracements(df, swing_highs_lows),
                'equal_highs_lows': smc.equal_highs_lows(df, swing_highs_lows),
                'premium_discount_zones': smc.premium_discount_zones(df, swing_highs_lows),
                'trend_indicator': smc.trend_indicator(df, swing_highs_lows)
            }
            
            print("✅ Análisis SMC completado")
            return analysis
            
        except Exception as e:
            print(f"❌ Error en análisis SMC: {e}")
            return {}
    
    def analyze_patterns(self, df: pd.DataFrame) -> Dict:
        """
        Analiza patrones de velas japonesas
        
        Parámetros:
        df: pd.DataFrame - Datos OHLCV
        
        Retorna:
        Dict: Diccionario con patrones detectados
        """
        try:
            print("🕯️ Analizando patrones de velas...")
            
            patterns = {
                'hammer': CandlestickPatterns.hammer(df),
                'shooting_star': CandlestickPatterns.shooting_star(df),
                'doji': CandlestickPatterns.doji(df),
                'engulfing': CandlestickPatterns.engulfing(df),
                'morning_star': CandlestickPatterns.morning_star(df),
                'evening_star': CandlestickPatterns.evening_star(df)
            }
            
            print("✅ Análisis de patrones completado")
            return patterns
            
        except Exception as e:
            print(f"❌ Error en análisis de patrones: {e}")
            return {}
    
    def generate_signals(self, df: pd.DataFrame, smc_analysis: Dict, patterns: Dict) -> Dict:
        """
        Genera señales de trading basadas en SMC y patrones
        
        Parámetros:
        df: pd.DataFrame - Datos OHLCV
        smc_analysis: Dict - Análisis SMC
        patterns: Dict - Patrones de velas
        
        Retorna:
        Dict: Señales de trading
        """
        try:
            print("📊 Generando señales de trading...")
            
            signals = {
                'buy_signals': [],
                'sell_signals': [],
                'strength': 0,
                'confidence': 0,
                'trend': 'neutral'
            }
            
            # Obtener datos más recientes
            current_price = df['close'].iloc[-1]
            trend_data = smc_analysis.get('trend_indicator', pd.DataFrame())
            
            if not trend_data.empty:
                latest_trend = trend_data.iloc[-1]
                signals['trend'] = 'bullish' if latest_trend['Trend'] == 1 else 'bearish' if latest_trend['Trend'] == -1 else 'neutral'
                signals['strength'] = latest_trend['Strength']
                signals['confidence'] = latest_trend['Confidence']
            
            # Análisis de señales basado en múltiples factores
            signal_score = 0
            
            # 1. Análisis de tendencia
            if signals['trend'] == 'bullish':
                signal_score += 30
            elif signals['trend'] == 'bearish':
                signal_score -= 30
            
            # 2. Análisis de FVG
            fvg_data = smc_analysis.get('fvg', pd.DataFrame())
            if not fvg_data.empty:
                recent_fvg = fvg_data.iloc[-5:]  # Últimas 5 velas
                bullish_fvg = recent_fvg[recent_fvg['FVG'] == 1]
                bearish_fvg = recent_fvg[recent_fvg['FVG'] == -1]
                
                if len(bullish_fvg) > len(bearish_fvg):
                    signal_score += 15
                elif len(bearish_fvg) > len(bullish_fvg):
                    signal_score -= 15
            
            # 3. Análisis de Order Blocks
            ob_data = smc_analysis.get('ob', pd.DataFrame())
            if not ob_data.empty:
                recent_ob = ob_data.iloc[-10:]  # Últimas 10 velas
                bullish_ob = recent_ob[recent_ob['OB'] == 1]
                bearish_ob = recent_ob[recent_ob['OB'] == -1]
                
                if len(bullish_ob) > len(bearish_ob):
                    signal_score += 20
                elif len(bearish_ob) > len(bullish_ob):
                    signal_score -= 20
            
            # 4. Análisis de patrones de velas
            if patterns:
                # Patrones alcistas
                if patterns.get('hammer', pd.Series()).iloc[-1]:
                    signal_score += 10
                if patterns.get('morning_star', pd.Series()).iloc[-1]:
                    signal_score += 15
                if patterns.get('engulfing', pd.Series()).iloc[-1] == 1:
                    signal_score += 12
                
                # Patrones bajistas
                if patterns.get('shooting_star', pd.Series()).iloc[-1]:
                    signal_score -= 10
                if patterns.get('evening_star', pd.Series()).iloc[-1]:
                    signal_score -= 15
                if patterns.get('engulfing', pd.Series()).iloc[-1] == -1:
                    signal_score -= 12
            
            # 5. Análisis de Premium/Discount Zones
            pd_data = smc_analysis.get('premium_discount_zones', pd.DataFrame())
            if not pd_data.empty:
                current_zone = pd_data.iloc[-1]['Zone']
                if current_zone == -1:  # Discount zone - favorable para compra
                    signal_score += 10
                elif current_zone == 1:  # Premium zone - favorable para venta
                    signal_score -= 10
            
            # Determinar señales finales
            if signal_score >= 30:
                signals['buy_signals'].append({
                    'type': 'STRONG_BUY',
                    'score': signal_score,
                    'price': current_price,
                    'reason': 'Múltiples indicadores alcistas'
                })
            elif signal_score >= 15:
                signals['buy_signals'].append({
                    'type': 'BUY',
                    'score': signal_score,
                    'price': current_price,
                    'reason': 'Indicadores alcistas moderados'
                })
            elif signal_score <= -30:
                signals['sell_signals'].append({
                    'type': 'STRONG_SELL',
                    'score': signal_score,
                    'price': current_price,
                    'reason': 'Múltiples indicadores bajistas'
                })
            elif signal_score <= -15:
                signals['sell_signals'].append({
                    'type': 'SELL',
                    'score': signal_score,
                    'price': current_price,
                    'reason': 'Indicadores bajistas moderados'
                })
            
            print("✅ Señales generadas")
            return signals
            
        except Exception as e:
            print(f"❌ Error generando señales: {e}")
            return {}
    
    def place_order(self, symbol: str, order_type: str, volume: float, 
                   price: float = None, sl: float = None, tp: float = None, 
                   comment: str = "SMC Signal") -> bool:
        """
        Coloca una orden en MetaTrader 5
        
        Parámetros:
        symbol: str - Símbolo
        order_type: str - "BUY" o "SELL"
        volume: float - Volumen de la orden
        price: float - Precio de entrada (None para mercado)
        sl: float - Stop Loss
        tp: float - Take Profit
        comment: str - Comentario de la orden
        
        Retorna:
        bool: True si la orden fue colocada exitosamente
        """
        if not self.connected:
            print("❌ No conectado a MT5")
            return False
        
        try:
            # Mapear tipo de orden
            if order_type.upper() == "BUY":
                mt5_order_type = mt5.ORDER_TYPE_BUY
            elif order_type.upper() == "SELL":
                mt5_order_type = mt5.ORDER_TYPE_SELL
            else:
                print("❌ Tipo de orden inválido")
                return False
            
            # Preparar request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5_order_type,
                "comment": comment,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Agregar precio si se especifica
            if price:
                request["price"] = price
            
            # Agregar Stop Loss
            if sl:
                request["sl"] = sl
            
            # Agregar Take Profit
            if tp:
                request["tp"] = tp
            
            # Enviar orden
            result = mt5.order_send(request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ Orden {order_type} colocada exitosamente")
                print(f"   Símbolo: {symbol}")
                print(f"   Volumen: {volume}")
                print(f"   Precio: {result.price}")
                if sl:
                    print(f"   Stop Loss: {sl}")
                if tp:
                    print(f"   Take Profit: {tp}")
                return True
            else:
                print(f"❌ Error al colocar orden: {result.retcode}")
                return False
                
        except Exception as e:
            print(f"❌ Error en orden: {e}")
            return False
    
    def get_positions(self, symbol: str = None) -> pd.DataFrame:
        """
        Obtiene posiciones abiertas
        
        Parámetros:
        symbol: str - Símbolo específico (None para todos)
        
        Retorna:
        pd.DataFrame: DataFrame con posiciones
        """
        if not self.connected:
            print("❌ No conectado a MT5")
            return pd.DataFrame()
        
        try:
            positions = mt5.positions_get(symbol=symbol)
            
            if positions is None:
                return pd.DataFrame()
            
            # Convertir a DataFrame
            positions_df = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())
            positions_df['time'] = pd.to_datetime(positions_df['time'], unit='s')
            
            return positions_df
            
        except Exception as e:
            print(f"❌ Error obteniendo posiciones: {e}")
            return pd.DataFrame()
    
    def close_position(self, ticket: int) -> bool:
        """
        Cierra una posición específica
        
        Parámetros:
        ticket: int - Ticket de la posición
        
        Retorna:
        bool: True si se cerró exitosamente
        """
        if not self.connected:
            print("❌ No conectado a MT5")
            return False
        
        try:
            position = mt5.positions_get(ticket=ticket)
            
            if not position:
                print(f"❌ Posición {ticket} no encontrada")
                return False
            
            position = position[0]
            
            # Determinar tipo de orden para cerrar
            if position.type == mt5.POSITION_TYPE_BUY:
                close_type = mt5.ORDER_TYPE_SELL
            else:
                close_type = mt5.ORDER_TYPE_BUY
            
            # Request para cerrar
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": close_type,
                "position": ticket,
                "comment": "SMC Close",
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ Posición {ticket} cerrada exitosamente")
                return True
            else:
                print(f"❌ Error cerrando posición: {result.retcode}")
                return False
                
        except Exception as e:
            print(f"❌ Error cerrando posición: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect() 