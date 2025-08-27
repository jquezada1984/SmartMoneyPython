from datetime import datetime
import backtrader as bt
import yfinance as yf
import pandas as pd

# Create a subclass of Strategy to define the indicators and logic

class SmaCross(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = dict(
        pfast=10,  # period for the fast moving average
        pslow=30   # period for the slow moving average
    )

    def __init__(self):
        sma1 = bt.ind.SMA(period=self.p.pfast)  # fast moving average
        sma2 = bt.ind.SMA(period=self.p.pslow)  # slow moving average
        self.crossover = bt.ind.CrossOver(sma1, sma2)  # crossover signal

    def next(self):
        if not self.position:  # not in the market
            if self.crossover > 0:  # if fast crosses slow to the upside
                self.buy()  # enter long

        elif self.crossover < 0:  # in the market & cross to the downside
            self.close()  # close long position


cerebro = bt.Cerebro()  # create a "Cerebro" engine instance

# Descarga datos con yfinance
print("📊 Descargando datos de AAPL...")
df = yf.download("AAPL", start="2022-01-01", end="2023-01-01", progress=False)

# Verificar que los datos se descargaron correctamente
if df.empty:
    print("❌ Error: No se pudieron descargar datos")
    exit()

print(f"✅ Datos descargados: {len(df)} registros")
print(f"📅 Rango: {df.index[0]} a {df.index[-1]}")

# Verificar y corregir las columnas del DataFrame
print(f"📋 Columnas originales: {list(df.columns)}")

# Si las columnas son tuplas, extraer el primer elemento
if isinstance(df.columns[0], tuple):
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    print(f"📋 Columnas corregidas: {list(df.columns)}")

# Asegurar que las columnas estén en minúsculas
df.columns = [str(col).lower() for col in df.columns]
print(f"📋 Columnas finales: {list(df.columns)}")

# Verificar que tenemos las columnas necesarias
required_columns = ['open', 'high', 'low', 'close', 'volume']
missing_columns = [col for col in required_columns if col not in df.columns]

if missing_columns:
    print(f"❌ Error: Columnas faltantes: {missing_columns}")
    print(f"   Columnas disponibles: {list(df.columns)}")
    exit()

# Seleccionar solo las columnas necesarias
df = df[required_columns]

# Convierte a feed para Backtrader
data = bt.feeds.PandasData(
    dataname=df,
    datetime=None,  # Usar el índice como datetime
    open=0,
    high=1,
    low=2,
    close=3,
    volume=4,
    openinterest=-1
)

cerebro.adddata(data)  # Add the data feed
cerebro.addstrategy(SmaCross)  # Add the trading strategy

print("🚀 Ejecutando backtesting...")
cerebro.run()  # run it all

print("📊 Generando gráfico...")
cerebro.plot()  # and plot it with a single command