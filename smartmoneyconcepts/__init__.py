import os
from smartmoneyconcepts.smc import smc

if os.getenv('SMC_CREDIT', '1') == '1':
    print("\033[1;33m¡Gracias por usar SmartMoneyConcepts! ⭐ Por favor muestra tu apoyo dando una estrella en el repositorio de GitHub: \033[4;34mhttps://github.com/joshyattridge/smart-money-concepts\033[0m")