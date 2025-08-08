# Integración con MetaTrader 5

Esta librería proporciona una integración completa con MetaTrader 5 para análisis de Smart Money Concepts y trading automatizado.

## 📋 Requisitos

### Software
- **MetaTrader 5** instalado y configurado
- **Python 3.8+**
- **MetaTrader5** package de Python

### Instalación de dependencias
```bash
pip install MetaTrader5 pandas numpy
```

## 🚀 Inicio Rápido

### Conexión básica
```python
from connectors.mt5_connector import MT5Connector

# Conectar a MT5 (sin credenciales - usa MT5 local)
mt5 = MT5Connector()

# O con credenciales
mt5 = MT5Connector(login=123456, password="tu_password", server="tu_broker")
```

### Análisis completo
```python
# Obtener datos
df = mt5.get_data("EURUSD", "1h", 500)

# Análisis SMC
smc_analysis = mt5.analyze_smc(df)

# Patrones de velas
patterns = mt5.analyze_patterns(df)

# Generar señales
signals = mt5.generate_signals(df, smc_analysis, patterns)
```

## 📊 Funcionalidades Principales

### 1. Obtención de Datos
```python
# Diferentes timeframes disponibles
df_1m = mt5.get_data("EURUSD", "1m", 1000)
df_5m = mt5.get_data("EURUSD", "5m", 500)
df_1h = mt5.get_data("EURUSD", "1h", 200)
df_1d = mt5.get_data("EURUSD", "1d", 100)

# Con fechas específicas
from datetime import datetime
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 12, 31)
df = mt5.get_data("EURUSD", "1h", start_date=start_date, end_date=end_date)
```

### 2. Análisis de Smart Money Concepts
```python
# Análisis completo
smc_analysis = mt5.analyze_smc(df, swing_length=20)

# Acceder a indicadores específicos
fvg_data = smc_analysis['fvg']
bos_data = smc_analysis['bos_choch']
ob_data = smc_analysis['ob']
trend_data = smc_analysis['trend_indicator']
```

### 3. Patrones de Velas Japonesas
```python
patterns = mt5.analyze_patterns(df)

# Verificar patrones específicos
if patterns['hammer'].iloc[-1]:
    print("¡Martillo detectado!")
if patterns['engulfing'].iloc[-1] == 1:
    print("¡Envolvente alcista!")
```

### 4. Generación de Señales
```python
signals = mt5.generate_signals(df, smc_analysis, patterns)

# Verificar señales
if signals['buy_signals']:
    for signal in signals['buy_signals']:
        print(f"Señal de compra: {signal['type']} - Score: {signal['score']}")
        print(f"Precio: {signal['price']:.5f}")
        print(f"Razón: {signal['reason']}")
```

## 💼 Trading Automatizado

### Colocación de Órdenes
```python
# Orden de compra
success = mt5.place_order(
    symbol="EURUSD",
    order_type="BUY",
    volume=0.1,  # 0.1 lotes
    sl=1.0500,   # Stop Loss
    tp=1.0600,   # Take Profit
    comment="SMC Signal"
)

# Orden de venta
success = mt5.place_order(
    symbol="EURUSD",
    order_type="SELL",
    volume=0.1,
    sl=1.0600,
    tp=1.0500,
    comment="SMC Signal"
)
```

### Gestión de Posiciones
```python
# Obtener posiciones abiertas
positions = mt5.get_positions("EURUSD")

# Cerrar posición específica
mt5.close_position(ticket=123456)
```

## ⚙️ Configuración Avanzada

### Usar archivo de configuración
```python
from config.mt5_config import MT5_CONFIG, SYMBOLS_CONFIG

# Configurar conector con parámetros predefinidos
mt5 = MT5Connector(
    login=MT5_CONFIG["login"],
    password=MT5_CONFIG["password"],
    server=MT5_CONFIG["server"]
)

# Usar símbolos predefinidos
forex_symbols = SYMBOLS_CONFIG["forex"]
for symbol in forex_symbols[:5]:  # Primeros 5 pares
    df = mt5.get_data(symbol, "1h", 100)
    # Análisis...
```

### Sistema de Trading Completo
```python
def trading_system():
    mt5 = MT5Connector()
    
    # Análisis de múltiples símbolos
    symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    
    for symbol in symbols:
        df = mt5.get_data(symbol, "1h", 500)
        smc_analysis = mt5.analyze_smc(df)
        patterns = mt5.analyze_patterns(df)
        signals = mt5.generate_signals(df, smc_analysis, patterns)
        
        # Ejecutar señales
        if signals['buy_signals']:
            signal = signals['buy_signals'][0]
            if signal['type'] == 'STRONG_BUY':
                mt5.place_order(symbol, "BUY", 0.1)
        
        elif signals['sell_signals']:
            signal = signals['sell_signals'][0]
            if signal['type'] == 'STRONG_SELL':
                mt5.place_order(symbol, "SELL", 0.1)
    
    mt5.disconnect()
```

## 📈 Ejemplos Prácticos

### 1. Scanner de Mercado
```python
def market_scanner():
    mt5 = MT5Connector()
    
    # Escanear múltiples símbolos
    symbols = SYMBOLS_CONFIG["forex"]
    opportunities = []
    
    for symbol in symbols:
        try:
            df = mt5.get_data(symbol, "1h", 200)
            smc_analysis = mt5.analyze_smc(df)
            signals = mt5.generate_signals(df, smc_analysis, {})
            
            if signals['buy_signals'] or signals['sell_signals']:
                opportunities.append({
                    'symbol': symbol,
                    'signals': signals,
                    'price': df['close'].iloc[-1]
                })
        except:
            continue
    
    # Mostrar oportunidades
    for opp in opportunities:
        print(f"📊 {opp['symbol']} - Precio: {opp['price']:.5f}")
        if opp['signals']['buy_signals']:
            print(f"   🟢 Señales de compra: {len(opp['signals']['buy_signals'])}")
        if opp['signals']['sell_signals']:
            print(f"   🔴 Señales de venta: {len(opp['signals']['sell_signals'])}")
    
    mt5.disconnect()
```

### 2. Monitor de Portafolio
```python
def portfolio_monitor():
    mt5 = MT5Connector()
    
    # Obtener todas las posiciones
    positions = mt5.get_positions()
    
    if not positions.empty:
        total_pnl = positions['profit'].sum()
        print(f"💰 P&L Total: ${total_pnl:.2f}")
        
        for _, pos in positions.iterrows():
            pos_type = "COMPRA" if pos['type'] == 0 else "VENTA"
            print(f"   {pos['symbol']} {pos_type} - P&L: ${pos['profit']:.2f}")
    else:
        print("📭 No hay posiciones abiertas")
    
    mt5.disconnect()
```

### 3. Backtesting Simple
```python
def simple_backtest(symbol, timeframe, bars):
    mt5 = MT5Connector()
    
    # Obtener datos históricos
    df = mt5.get_data(symbol, timeframe, bars)
    
    # Análisis completo
    smc_analysis = mt5.analyze_smc(df)
    patterns = mt5.analyze_patterns(df)
    
    # Simular señales
    signals_count = 0
    for i in range(100, len(df)):  # Empezar después de 100 barras
        window_df = df.iloc[:i+1]
        window_smc = {k: v.iloc[:i+1] for k, v in smc_analysis.items()}
        window_patterns = {k: v.iloc[:i+1] for k, v in patterns.items()}
        
        signals = mt5.generate_signals(window_df, window_smc, window_patterns)
        
        if signals['buy_signals'] or signals['sell_signals']:
            signals_count += 1
    
    print(f"📊 Señales generadas: {signals_count}")
    print(f"📈 Frecuencia: {signals_count/len(df)*100:.1f}%")
    
    mt5.disconnect()
```

## 🔧 Solución de Problemas

### Error de conexión
```python
# Verificar que MT5 esté abierto
if not mt5.connected:
    print("❌ Verifica que MetaTrader 5 esté abierto")
    print("❌ Verifica que las credenciales sean correctas")
```

### Error de símbolo
```python
# Obtener símbolos disponibles
symbols = mt5.get_symbols()
print(f"Símbolos disponibles: {len(symbols)}")
print(f"Ejemplos: {symbols[:10]}")
```

### Error de datos
```python
# Verificar datos obtenidos
df = mt5.get_data("EURUSD", "1h", 100)
if df.empty:
    print("❌ No se pudieron obtener datos")
    print("❌ Verifica el símbolo y timeframe")
else:
    print(f"✅ Datos obtenidos: {len(df)} barras")
```

## 📚 Recursos Adicionales

- [Documentación oficial de MetaTrader5](https://www.mql5.com/en/docs/integration/python_metatrader5)
- [Ejemplos de uso](examples/mt5_trading_example.py)
- [Configuración](config/mt5_config.py)

## ⚠️ Advertencias

1. **Siempre prueba en cuenta demo primero**
2. **Usa gestión de riesgo adecuada**
3. **No inviertas más de lo que puedas permitirte perder**
4. **Los indicadores técnicos no garantizan ganancias**
5. **Mantén tu software actualizado**

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver [LICENSE](LICENSE) para más detalles. 