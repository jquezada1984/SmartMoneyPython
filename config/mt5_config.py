"""
Configuración para MetaTrader 5 y Smart Money Concepts
Este archivo contiene configuraciones predefinidas para facilitar el uso de la librería
"""

# Configuración de conexión MT5
MT5_CONFIG = {
    # Credenciales (opcional - si no se proporcionan, usa MT5 local)
    "login": None,  # Tu número de cuenta MT5
    "password": None,  # Tu contraseña
    "server": None,  # Tu servidor del broker
    
    # Configuración por defecto
    "default_symbol": "EURUSD",
    "default_timeframe": "1h",
    "default_bars": 500,
    
    # Configuración de análisis
    "swing_length": 20,
    "lookback_period": 20,
    
    # Configuración de trading
    "default_volume": 0.1,  # Volumen por defecto en lotes
    "risk_percent": 2.0,  # Porcentaje de riesgo por operación
    "sl_atr_multiplier": 2.0,  # Multiplicador de ATR para Stop Loss
    "tp_risk_ratio": 2.0,  # Ratio riesgo/beneficio para Take Profit
}

# Configuración de símbolos populares
SYMBOLS_CONFIG = {
    "forex": [
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
        "EURGBP", "EURJPY", "GBPJPY", "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD",
        "CADCHF", "CADJPY", "CHFJPY", "EURAUD", "EURCAD", "EURCHF", "EURNZD"
    ],
    "indices": [
        "US30", "US500", "NAS100", "GER30", "UK100", "FRA40", "ESP35", "ITA40"
    ],
    "commodities": [
        "XAUUSD", "XAGUSD", "WTIUSD", "BRENTUSD"
    ],
    "crypto": [
        "BTCUSD", "ETHUSD", "LTCUSD", "XRPUSD"
    ]
}

# Configuración de timeframes
TIMEFRAMES_CONFIG = {
    "1m": "1 minuto",
    "5m": "5 minutos", 
    "15m": "15 minutos",
    "30m": "30 minutos",
    "1h": "1 hora",
    "4h": "4 horas",
    "1d": "1 día",
    "1w": "1 semana",
    "1M": "1 mes"
}

# Configuración de análisis SMC
SMC_CONFIG = {
    "indicators": [
        "fvg", "swing_highs_lows", "bos_choch", "ob", "liquidity",
        "previous_high_low", "sessions", "retracements", 
        "equal_highs_lows", "premium_discount_zones", "trend_indicator"
    ],
    "sessions": [
        "Sydney", "Tokyo", "London", "New York", 
        "Asian kill zone", "London open kill zone", 
        "New York kill zone", "london close kill zone"
    ],
    "fvg_join_consecutive": True,
    "liquidity_range_percent": 0.01,
    "premium_discount_tolerance": 0.0001
}

# Configuración de patrones de velas
PATTERNS_CONFIG = {
    "indicators": [
        "hammer", "shooting_star", "doji", "engulfing", 
        "morning_star", "evening_star"
    ],
    "hammer_body_ratio": 0.3,
    "hammer_shadow_ratio": 2.0,
    "doji_threshold": 0.05,
    "morning_star_body_threshold": 0.3,
    "volume_confirmation": {
        "enabled": True,
        "vol_window": 20,  # Ventana para calcular media de volumen
        "vol_mult": 1.2,   # Multiplicador para confirmación (1.2 = 20% más que la media)
        "spike_threshold": 2.0  # Umbral para picos de volumen (2.0 = 200% de la media)
    }
}

# Configuración de señales
SIGNALS_CONFIG = {
    "score_thresholds": {
        "strong_buy": 30,
        "buy": 15,
        "strong_sell": -30,
        "sell": -15
    },
    "weights": {
        "trend": 30,
        "bos": 20,
        "choch": 15,
        "fvg": 10,
        "ob": 15,
        "premium_discount": 10,
        "momentum": 5,
        "patterns": {
            "hammer": 10,
            "shooting_star": -10,
            "morning_star": 15,
            "evening_star": -15,
            "engulfing_bullish": 12,
            "engulfing_bearish": -12
        }
    }
}

# Configuración de gestión de riesgo
RISK_CONFIG = {
    "max_positions": 5,  # Máximo número de posiciones simultáneas
    "max_daily_loss": 5.0,  # Máxima pérdida diaria en porcentaje
    "max_drawdown": 20.0,  # Máximo drawdown en porcentaje
    "position_sizing": {
        "method": "fixed",  # "fixed", "risk_based", "kelly"
        "fixed_amount": 0.1,  # Lotes fijos
        "risk_per_trade": 0.02,  # 2% del capital por operación
    }
}

# Configuración de notificaciones
NOTIFICATIONS_CONFIG = {
    "enable_email": False,
    "enable_telegram": False,
    "enable_discord": False,
    "email_config": {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "email": "tu_email@gmail.com",
        "password": "tu_password"
    },
    "telegram_config": {
        "bot_token": "tu_bot_token",
        "chat_id": "tu_chat_id"
    }
}

# Configuración de logging
LOGGING_CONFIG = {
    "level": "INFO",  # DEBUG, INFO, WARNING, ERROR
    "file": "trading.log",
    "max_size": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5
}

# Configuración de backtesting
BACKTEST_CONFIG = {
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "initial_balance": 10000,
    "commission": 0.0001,  # 1 pip por operación
    "slippage": 0.0001,  # 1 pip de slippage
    "spread": 0.0002,  # 2 pips de spread
}

# Ejemplos de uso
USAGE_EXAMPLES = {
    "basic_analysis": """
# Análisis básico
from connectors.mt5_connector import MT5Connector

mt5 = MT5Connector()
df = mt5.get_data("EURUSD", "1h", 500)
smc_analysis = mt5.analyze_smc(df)
signals = mt5.generate_signals(df, smc_analysis, {})
    """,
    
    "volume_confirmation": """
# Análisis con confirmación por volumen
from smartmoneyconcepts.candlestick_patterns import CandlestickPatterns

patterns = CandlestickPatterns()

# Detectar patrones
hammer = patterns.hammer(df)
engulfing = patterns.engulfing(df)

# Confirmación por volumen
volume_conf = patterns.volume_confirmation(df, vol_window=20, vol_mult=1.2)
volume_ratio = patterns.high_volume_relative(df, vol_window=20, vol_mult=1.2)

# Señal de compra con confirmación
if hammer.iloc[-1] and volume_conf.iloc[-1]:
    print("🟢 Señal de compra confirmada por volumen")
elif hammer.iloc[-1] and not volume_conf.iloc[-1]:
    print("🟡 Señal de compra débil (sin confirmación de volumen)")
    """,
    
    "trading_system": """
# Sistema de trading completo
mt5 = MT5Connector(login=123456, password="pass", server="broker")
df = mt5.get_data("EURUSD", "1h", 1000)
smc_analysis = mt5.analyze_smc(df)
patterns = mt5.analyze_patterns(df)
signals = mt5.generate_signals(df, smc_analysis, patterns)

if signals['buy_signals']:
    mt5.place_order("EURUSD", "BUY", 0.1, sl=1.0500, tp=1.0600)
    """,
    
    "portfolio_monitoring": """
# Monitoreo de portafolio
mt5 = MT5Connector()
positions = mt5.get_positions()
for _, pos in positions.iterrows():
    print(f"Posición: {pos['symbol']} - P&L: ${pos['profit']:.2f}")
    """
} 