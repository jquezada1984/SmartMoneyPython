import os
from smartmoneyconcepts.smc import smc
from smartmoneyconcepts.candlestick_patterns import CandlestickPatterns
from smartmoneyconcepts.market_analysis_lib import MarketAnalysisLib

__all__ = ['smc', 'CandlestickPatterns', 'MarketAnalysisLib']

if os.getenv('SMC_CREDIT', '1') == '1':
    print("\033[1;33m¡Gracias por usar SmartMoneyConcepts! ⭐ Por favor muestra tu apoyo dando una estrella en el repositorio de GitHub: \033[4;34m")