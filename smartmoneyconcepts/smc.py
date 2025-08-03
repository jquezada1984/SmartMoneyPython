from functools import wraps
import pandas as pd
import numpy as np
from pandas import DataFrame, Series
from datetime import datetime

def inputvalidator(input_="ohlc"):
    def dfcheck(func):
        @wraps(func)
        def wrap(*args, **kwargs):
            args = list(args)
            i = 0 if isinstance(args[0], pd.DataFrame) else 1

            args[i] = args[i].rename(columns={c: c.lower() for c in args[i].columns})

            inputs = {
                "o": "open",
                "h": "high",
                "l": "low",
                "c": kwargs.get("column", "close").lower(),
                "v": "volume",
            }

            if inputs["c"] != "close":
                kwargs["column"] = inputs["c"]

            for l in input_:
                if inputs[l] not in args[i].columns:
                    raise LookupError(
                        'Must have a dataframe column named "{0}"'.format(inputs[l])
                    )

            return func(*args, **kwargs)

        return wrap

    return dfcheck


def apply(decorator):
    def decorate(cls):
        for attr in cls.__dict__:
            if callable(getattr(cls, attr)):
                setattr(cls, attr, decorator(getattr(cls, attr)))

        return cls

    return decorate


@apply(inputvalidator(input_="ohlc"))
class smc:
    __version__ = "0.0.29"

    @classmethod
    def fvg(cls, ohlc: DataFrame, join_consecutive=False) -> DataFrame:
        """
        FVG - Gap de Valor Justo
        Siempre retorna un DataFrame con columnas ['FVG', 'high', 'low', 'close'].
        """
        fvg = np.where(
            (
                (ohlc["high"].shift(1) < ohlc["low"].shift(-1))
                & (ohlc["close"] > ohlc["open"])
            )
            | (
                (ohlc["low"].shift(1) > ohlc["high"].shift(-1))
                & (ohlc["close"] < ohlc["open"])
            ),
            np.where(ohlc["close"] > ohlc["open"], 1, -1),
            np.nan,
        )

        top = np.where(
            ~np.isnan(fvg),
            np.where(
                ohlc["close"] > ohlc["open"],
                ohlc["low"].shift(-1),
                ohlc["low"].shift(1),
            ),
            np.nan,
        )

        bottom = np.where(
            ~np.isnan(fvg),
            np.where(
                ohlc["close"] > ohlc["open"],
                ohlc["high"].shift(1),
                ohlc["high"].shift(-1),
            ),
            np.nan,
        )

        # si hay múltiples fvg consecutivos, únelos usando el máximo más alto y el mínimo más bajo y el último índice
        if join_consecutive:
            for i in range(len(fvg) - 1):
                if fvg[i] == fvg[i + 1]:
                    top[i + 1] = max(top[i], top[i + 1])
                    bottom[i + 1] = min(bottom[i], bottom[i + 1])
                    fvg[i] = top[i] = bottom[i] = np.nan

        mitigated_index = np.zeros(len(ohlc), dtype=np.int32)
        for i in np.where(~np.isnan(fvg))[0]:
            mask = np.zeros(len(ohlc), dtype=np.bool_)
            if fvg[i] == 1:
                mask = ohlc["low"][i + 2 :] <= top[i]
            elif fvg[i] == -1:
                mask = ohlc["high"][i + 2 :] >= bottom[i]
            if np.any(mask):
                j = np.argmax(mask) + i + 2
                mitigated_index[i] = j

        mitigated_index = np.where(np.isnan(fvg), np.nan, mitigated_index)

        # Construir DataFrame resultado
        resultado = pd.DataFrame({
            "FVG": fvg,
            "Top": top,
            "Bottom": bottom,
            "MitigatedIndex": mitigated_index,
        }, index=ohlc.index)

        # Añadir columnas estándar si faltan
        columnas_necesarias = ['FVG', 'high', 'low', 'close']
        for col in columnas_necesarias:
            if col not in resultado.columns:
                if col in ohlc.columns:
                    resultado[col] = ohlc[col].values[:len(resultado)]
                else:
                    resultado[col] = np.nan
        # Reordenar columnas
        cols_final = columnas_necesarias + [c for c in resultado.columns if c not in columnas_necesarias]
        return resultado[cols_final]

    @classmethod
    def swing_highs_lows(cls, ohlc: DataFrame, swing_length: int = 50) -> Series:
        """
        Swing Highs y Lows
        Un swing high es cuando el máximo actual es el máximo más alto de la cantidad swing_length de velas antes y después.
        Un swing low es cuando el mínimo actual es el mínimo más bajo de la cantidad swing_length de velas antes y después.

        parámetros:
        swing_length: int - la cantidad de velas para mirar hacia atrás y hacia adelante para determinar el swing high o low

        retorna:
        HighLow = 1 si swing high, -1 si swing low
        Level = el nivel del swing high o low
        """

        swing_length *= 2
        # establece los máximos a 1 si el máximo actual es el máximo más alto en las últimas 5 velas y las siguientes 5 velas
        swing_highs_lows = np.where(
            ohlc["high"]
            == ohlc["high"].shift(-(swing_length // 2)).rolling(swing_length).max(),
            1,
            np.where(
                ohlc["low"]
                == ohlc["low"].shift(-(swing_length // 2)).rolling(swing_length).min(),
                -1,
                np.nan,
            ),
        )

        while True:
            positions = np.where(~np.isnan(swing_highs_lows))[0]

            if len(positions) < 2:
                break

            current = swing_highs_lows[positions[:-1]]
            next = swing_highs_lows[positions[1:]]

            highs = ohlc["high"].iloc[positions[:-1]].values
            lows = ohlc["low"].iloc[positions[:-1]].values

            next_highs = ohlc["high"].iloc[positions[1:]].values
            next_lows = ohlc["low"].iloc[positions[1:]].values

            index_to_remove = np.zeros(len(positions), dtype=bool)

            consecutive_highs = (current == 1) & (next == 1)
            index_to_remove[:-1] |= consecutive_highs & (highs < next_highs)
            index_to_remove[1:] |= consecutive_highs & (highs >= next_highs)

            consecutive_lows = (current == -1) & (next == -1)
            index_to_remove[:-1] |= consecutive_lows & (lows > next_lows)
            index_to_remove[1:] |= consecutive_lows & (lows <= next_lows)

            if not index_to_remove.any():
                break

            swing_highs_lows[positions[index_to_remove]] = np.nan

        positions = np.where(~np.isnan(swing_highs_lows))[0]

        if len(positions) > 0:
            if swing_highs_lows[positions[0]] == 1:
                swing_highs_lows[0] = -1
            if swing_highs_lows[positions[0]] == -1:
                swing_highs_lows[0] = 1
            if swing_highs_lows[positions[-1]] == -1:
                swing_highs_lows[-1] = 1
            if swing_highs_lows[positions[-1]] == 1:
                swing_highs_lows[-1] = -1

        level = np.where(
            ~np.isnan(swing_highs_lows),
            np.where(swing_highs_lows == 1, ohlc["high"], ohlc["low"]),
            np.nan,
        )

        return pd.concat(
            [
                pd.Series(swing_highs_lows, name="HighLow"),
                pd.Series(level, name="Level"),
            ],
            axis=1,
        )

    @classmethod
    def bos_choch(
        cls, ohlc: DataFrame, swing_highs_lows: DataFrame, close_break: bool = True
    ) -> Series:
        """
        BOS - Rotura de Estructura
        CHoCH - Cambio de Carácter
        estos son ambos indicaciones de cambio en la estructura del mercado

        parámetros:
        swing_highs_lows: DataFrame - proporciona el dataframe de la función swing_highs_lows
        close_break: bool - si es True entonces la ruptura de estructura se mitigará basándose en el cierre de la vela, de lo contrario será el high/low.

        retorna:
        BOS = 1 si ruptura de estructura alcista, -1 si ruptura de estructura bajista
        CHOCH = 1 si cambio de carácter alcista, -1 si cambio de carácter bajista
        Level = el nivel de la ruptura de estructura o cambio de carácter
        BrokenIndex = el índice de la vela que rompió el nivel
        """

        swing_highs_lows = swing_highs_lows.copy()

        level_order = []
        highs_lows_order = []

        bos = np.zeros(len(ohlc), dtype=np.int32)
        choch = np.zeros(len(ohlc), dtype=np.int32)
        level = np.zeros(len(ohlc), dtype=np.float32)

        last_positions = []

        for i in range(len(swing_highs_lows["HighLow"])):
            if not np.isnan(swing_highs_lows["HighLow"].iloc[i]):
                level_order.append(swing_highs_lows["Level"].iloc[i])
                highs_lows_order.append(swing_highs_lows["HighLow"].iloc[i])
                if len(level_order) >= 4:
                    # bullish bos
                    bos[last_positions[-2]] = (
                        1
                        if (
                            np.all(highs_lows_order[-4:] == [-1, 1, -1, 1])
                            and np.all(
                                level_order[-4]
                                < level_order[-2]
                                < level_order[-3]
                                < level_order[-1]
                            )
                        )
                        else 0
                    )
                    level[last_positions[-2]] = (
                        level_order[-3] if bos[last_positions[-2]] != 0 else 0
                    )

                    # bearish bos
                    bos[last_positions[-2]] = (
                        -1
                        if (
                            np.all(highs_lows_order[-4:] == [1, -1, 1, -1])
                            and np.all(
                                level_order[-4]
                                > level_order[-2]
                                > level_order[-3]
                                > level_order[-1]
                            )
                        )
                        else bos[last_positions[-2]]
                    )
                    level[last_positions[-2]] = (
                        level_order[-3] if bos[last_positions[-2]] != 0 else 0
                    )

                    # bullish choch
                    choch[last_positions[-2]] = (
                        1
                        if (
                            np.all(highs_lows_order[-4:] == [-1, 1, -1, 1])
                            and np.all(
                                level_order[-1]
                                > level_order[-3]
                                > level_order[-4]
                                > level_order[-2]
                            )
                        )
                        else 0
                    )
                    level[last_positions[-2]] = (
                        level_order[-3]
                        if choch[last_positions[-2]] != 0
                        else level[last_positions[-2]]
                    )

                    # bearish choch
                    choch[last_positions[-2]] = (
                        -1
                        if (
                            np.all(highs_lows_order[-4:] == [1, -1, 1, -1])
                            and np.all(
                                level_order[-1]
                                < level_order[-3]
                                < level_order[-4]
                                < level_order[-2]
                            )
                        )
                        else choch[last_positions[-2]]
                    )
                    level[last_positions[-2]] = (
                        level_order[-3]
                        if choch[last_positions[-2]] != 0
                        else level[last_positions[-2]]
                    )

                last_positions.append(i)

        broken = np.zeros(len(ohlc), dtype=np.int32)
        for i in np.where(np.logical_or(bos != 0, choch != 0))[0]:
            mask = np.zeros(len(ohlc), dtype=np.bool_)
            # if the bos is 1 then check if the candles high has gone above the level
            if bos[i] == 1 or choch[i] == 1:
                mask = ohlc["close" if close_break else "high"][i + 2 :] > level[i]
            # if the bos is -1 then check if the candles low has gone below the level
            elif bos[i] == -1 or choch[i] == -1:
                mask = ohlc["close" if close_break else "low"][i + 2 :] < level[i]
            if np.any(mask):
                j = np.argmax(mask) + i + 2
                broken[i] = j
                # if there are any unbroken bos or choch that started before this one and ended after this one then remove them
                for k in np.where(np.logical_or(bos != 0, choch != 0))[0]:
                    if k < i and broken[k] >= j:
                        bos[k] = 0
                        choch[k] = 0
                        level[k] = 0

        # remove the ones that aren't broken
        for i in np.where(
            np.logical_and(np.logical_or(bos != 0, choch != 0), broken == 0)
        )[0]:
            bos[i] = 0
            choch[i] = 0
            level[i] = 0

        # replace all the 0s with np.nan
        bos = np.where(bos != 0, bos, np.nan)
        choch = np.where(choch != 0, choch, np.nan)
        level = np.where(level != 0, level, np.nan)
        broken = np.where(broken != 0, broken, np.nan)

        bos = pd.Series(bos, name="BOS")
        choch = pd.Series(choch, name="CHOCH")
        level = pd.Series(level, name="Level")
        broken = pd.Series(broken, name="BrokenIndex")

        return pd.concat([bos, choch, level, broken], axis=1)

    @classmethod
    def ob(
        cls,
        ohlc: DataFrame,
        swing_highs_lows: DataFrame,
        close_mitigation: bool = False,
    ) -> Series:
        """
        OB - Bloques de Órdenes
        Este método detecta order blocks cuando existe una alta cantidad de órdenes de mercado en un rango de precios.

        parámetros:
        swing_highs_lows: DataFrame - proporciona el dataframe de la función swing_highs_lows
        close_mitigation: bool - si es True entonces el order block se mitigará basándose en el cierre de la vela, de lo contrario será el high/low.

        retorna:
        OB = 1 si order block alcista, -1 si order block bajista
        Top = tope del order block
        Bottom = fondo del order block
        OBVolume = volumen + 2 últimos volúmenes
        Percentage = fuerza del order block (min(highVolume, lowVolume)/max(highVolume, lowVolume))
        """

        ohlc_len = len(ohlc)
        _open = ohlc["open"].values
        _high = ohlc["high"].values
        _low = ohlc["low"].values
        _close = ohlc["close"].values
        _volume = ohlc["volume"].values
        swing_hl = swing_highs_lows["HighLow"].values

        # Pre-allocate arrays
        crossed = np.full(ohlc_len, False, dtype=bool)
        ob = np.zeros(ohlc_len, dtype=np.int32)
        top_arr = np.zeros(ohlc_len, dtype=np.float32)
        bottom_arr = np.zeros(ohlc_len, dtype=np.float32)
        obVolume = np.zeros(ohlc_len, dtype=np.float32)
        lowVolume = np.zeros(ohlc_len, dtype=np.float32)
        highVolume = np.zeros(ohlc_len, dtype=np.float32)
        percentage = np.zeros(ohlc_len, dtype=np.float32)
        mitigated_index = np.zeros(ohlc_len, dtype=np.int32)
        breaker = np.full(ohlc_len, False, dtype=bool)

        # Precompute swing indices (assumed sorted)
        swing_high_indices = np.flatnonzero(swing_hl == 1)
        swing_low_indices = np.flatnonzero(swing_hl == -1)

        # List to track active bullish order blocks
        active_bullish = []
        for i in range(ohlc_len):
            close_index = i
            # Update existing bullish OB
            for idx in active_bullish.copy():
                if breaker[idx]:
                    if _high[close_index] > top_arr[idx]:
                        # Reset this OB
                        ob[idx] = 0
                        top_arr[idx] = 0.0
                        bottom_arr[idx] = 0.0
                        obVolume[idx] = 0.0
                        lowVolume[idx] = 0.0
                        highVolume[idx] = 0.0
                        mitigated_index[idx] = 0
                        percentage[idx] = 0.0
                        active_bullish.remove(idx)
                else:
                    if ((not close_mitigation and _low[close_index] < bottom_arr[idx])
                        or (close_mitigation and min(_open[close_index], _close[close_index]) < bottom_arr[idx])):
                        breaker[idx] = True
                        mitigated_index[idx] = close_index - 1

            # Find last swing high index less than current candle (using binary search)
            pos = np.searchsorted(swing_high_indices, close_index)
            last_top_index = swing_high_indices[pos - 1] if pos > 0 else None

            if last_top_index is not None:
                if _close[close_index] > _high[last_top_index] and not crossed[last_top_index]:
                    crossed[last_top_index] = True
                    # Initialise with default values from previous candle
                    default_index = close_index - 1
                    obBtm = _high[default_index]
                    obTop = _low[default_index]
                    obIndex = default_index
                    # Look for a lower low between last_top_index and current candle
                    if close_index - last_top_index > 1:
                        start = last_top_index + 1
                        end = close_index  # up to but not including close_index
                        if end > start:
                            segment = _low[start:end]
                            min_val = segment.min()
                            # In case of ties, take the last occurrence
                            candidates = np.nonzero(segment == min_val)[0]
                            if candidates.size:
                                candidate_index = start + candidates[-1]
                                obBtm = _low[candidate_index]
                                obTop = _high[candidate_index]
                                obIndex = candidate_index
                    # Set bullish OB values
                    ob[obIndex] = 1
                    top_arr[obIndex] = obTop
                    bottom_arr[obIndex] = obBtm
                    vol_cur = _volume[close_index]
                    vol_prev1 = _volume[close_index - 1] if close_index >= 1 else 0.0
                    vol_prev2 = _volume[close_index - 2] if close_index >= 2 else 0.0
                    obVolume[obIndex] = vol_cur + vol_prev1 + vol_prev2
                    lowVolume[obIndex] = vol_prev2
                    highVolume[obIndex] = vol_cur + vol_prev1
                    max_vol = max(highVolume[obIndex], lowVolume[obIndex])
                    percentage[obIndex] = (min(highVolume[obIndex], lowVolume[obIndex]) / max_vol * 100.0) if max_vol != 0 else 100.0
                    active_bullish.append(obIndex)

        # List to track active bearish order blocks
        active_bearish = []
        for i in range(ohlc_len):
            close_index = i
            # Update existing bearish OB
            for idx in active_bearish.copy():
                if breaker[idx]:
                    if _low[close_index] < bottom_arr[idx]:
                        ob[idx] = 0
                        top_arr[idx] = 0.0
                        bottom_arr[idx] = 0.0
                        obVolume[idx] = 0.0
                        lowVolume[idx] = 0.0
                        highVolume[idx] = 0.0
                        mitigated_index[idx] = 0
                        percentage[idx] = 0.0
                        active_bearish.remove(idx)
                else:
                    if ((not close_mitigation and _high[close_index] > top_arr[idx])
                        or (close_mitigation and max(_open[close_index], _close[close_index]) > top_arr[idx])):
                        breaker[idx] = True
                        mitigated_index[idx] = close_index

            # Find last swing low index less than current candle
            pos = np.searchsorted(swing_low_indices, close_index)
            last_btm_index = swing_low_indices[pos - 1] if pos > 0 else None

            if last_btm_index is not None:
                if _close[close_index] < _low[last_btm_index] and not crossed[last_btm_index]:
                    crossed[last_btm_index] = True
                    default_index = close_index - 1
                    obTop = _high[default_index]
                    obBtm = _low[default_index]
                    obIndex = default_index
                    if close_index - last_btm_index > 1:
                        start = last_btm_index + 1
                        end = close_index
                        if end > start:
                            segment = _high[start:end]
                            max_val = segment.max()
                            candidates = np.nonzero(segment == max_val)[0]
                            if candidates.size:
                                candidate_index = start + candidates[-1]
                                obTop = _high[candidate_index]
                                obBtm = _low[candidate_index]
                                obIndex = candidate_index
                    ob[obIndex] = -1
                    top_arr[obIndex] = obTop
                    bottom_arr[obIndex] = obBtm
                    vol_cur = _volume[close_index]
                    vol_prev1 = _volume[close_index - 1] if close_index >= 1 else 0.0
                    vol_prev2 = _volume[close_index - 2] if close_index >= 2 else 0.0
                    obVolume[obIndex] = vol_cur + vol_prev1 + vol_prev2
                    lowVolume[obIndex] = vol_cur + vol_prev1
                    highVolume[obIndex] = vol_prev2
                    max_vol = max(highVolume[obIndex], lowVolume[obIndex])
                    percentage[obIndex] = (min(highVolume[obIndex], lowVolume[obIndex]) / max_vol * 100.0) if max_vol != 0 else 100.0
                    active_bearish.append(obIndex)

        # Convert zeros to NaN where OB was not set
        ob = np.where(ob != 0, ob, np.nan)
        top_arr = np.where(~np.isnan(ob), top_arr, np.nan)
        bottom_arr = np.where(~np.isnan(ob), bottom_arr, np.nan)
        obVolume = np.where(~np.isnan(ob), obVolume, np.nan)
        mitigated_index = np.where(~np.isnan(ob), mitigated_index, np.nan)
        percentage = np.where(~np.isnan(ob), percentage, np.nan)

        ob_series = pd.Series(ob, name="OB")
        top_series = pd.Series(top_arr, name="Top")
        bottom_series = pd.Series(bottom_arr, name="Bottom")
        obVolume_series = pd.Series(obVolume, name="OBVolume")
        mitigated_index_series = pd.Series(mitigated_index, name="MitigatedIndex")
        percentage_series = pd.Series(percentage, name="Percentage")

        return pd.concat(
            [
                ob_series,
                top_series,
                bottom_series,
                obVolume_series,
                mitigated_index_series,
                percentage_series,
            ],
            axis=1,
        )

    @classmethod
    def liquidity(cls, ohlc: DataFrame, swing_highs_lows: DataFrame, range_percent: float = 0.01) -> Series:
        """
        Liquidez
        Liquidez es cuando hay múltiples máximos dentro de un pequeño rango entre sí,
        o múltiples mínimos dentro de un pequeño rango entre sí.

        parámetros:
        swing_highs_lows: DataFrame - proporciona el dataframe de la función swing_highs_lows
        range_percent: float - el porcentaje del rango para determinar la liquidez

        retorna:
        Liquidity = 1 si liquidez alcista, -1 si liquidez bajista
        Level = el nivel de la liquidez
        End = el índice del último nivel de liquidez
        Swept = el índice de la vela que barrió la liquidez
        """

        # Trabaja en una copia para que el original no se modifique.
        shl = swing_highs_lows.copy()
        n = len(ohlc)
        
        # Calcula el rango de pips basado en el rango general alto-bajo.
        pip_range = (np.max(np.array(ohlc["high"])) - np.min(np.array(ohlc["low"]))) * range_percent

        # Preconvierte las columnas requeridas a arrays de numpy.
        ohlc_high = ohlc["high"].values
        ohlc_low = ohlc["low"].values
        # Haz una copia para permitir el marcado in-place de candidatos usados.
        shl_HL = shl["HighLow"].values.copy()
        shl_Level = shl["Level"].values.copy()

        # Inicializa arrays de salida con NaN (para coincidir con el reemplazo posterior de ceros).
        liquidity = np.full(n, np.nan, dtype=np.float32)
        liquidity_level = np.full(n, np.nan, dtype=np.float32)
        liquidity_end = np.full(n, np.nan, dtype=np.float32)
        liquidity_swept = np.full(n, np.nan, dtype=np.float32)

        # Procesa liquidez alcista (HighLow == 1)
        bull_indices = np.nonzero(np.array(shl_HL) == 1)[0]
        for i in bull_indices:
            # Salta si este candidato ya ha sido usado.
            if shl_HL[i] != 1:
                continue
            high_level = shl_Level[i]
            range_low = high_level - pip_range
            range_high = high_level + pip_range
            group_levels = [high_level]
            group_end = i

            # Determina el índice barrido:
            # Encuentra la primera vela después de i donde el máximo alcanza o excede range_high.
            c_start = i + 1
            if c_start < n:
                cond = ohlc_high[c_start:] >= range_high
                if np.any(cond):
                    swept = c_start + int(np.argmax(cond))
                else:
                    swept = 0
            else:
                swept = 0

            # Itera solo sobre índices candidatos mayores que i.
            for j in bull_indices:
                if j <= i:
                    continue
                # Emula la ruptura del bucle interno: si hemos alcanzado o pasado el índice barrido, detente.
                if swept and j >= swept:
                    break
                # Si el candidato j está dentro del rango de liquidez, agrégalo y márcalo como usado.
                if shl_HL[j] == 1 and (range_low <= shl_Level[j] <= range_high):
                    group_levels.append(shl_Level[j])
                    group_end = j
                    shl_HL[j] = 0  # marca candidato como usado
            # Solo registra liquidez si más de un candidato está agrupado.
            if len(group_levels) > 1:
                avg_level = sum(group_levels) / len(group_levels)
                liquidity[i] = 1
                liquidity_level[i] = avg_level
                liquidity_end[i] = group_end
                liquidity_swept[i] = swept

        # Procesa liquidez bajista (HighLow == -1)
        bear_indices = np.nonzero(shl_HL == -1)[0]
        for i in bear_indices:
            if shl_HL[i] != -1:
                continue
            low_level = shl_Level[i]
            range_low = low_level - pip_range
            range_high = low_level + pip_range
            group_levels = [low_level]
            group_end = i

            # Encuentra la primera vela después de i donde el mínimo alcanza o va por debajo de range_low.
            c_start = i + 1
            if c_start < n:
                cond = ohlc_low[c_start:] <= range_low
                if np.any(cond):
                    swept = c_start + int(np.argmax(cond))
                else:
                    swept = 0
            else:
                swept = 0

            for j in bear_indices:
                if j <= i:
                    continue
                if swept and j >= swept:
                    break
                if shl_HL[j] == -1 and (range_low <= shl_Level[j] <= range_high):
                    group_levels.append(shl_Level[j])
                    group_end = j
                    shl_HL[j] = 0
            if len(group_levels) > 1:
                avg_level = sum(group_levels) / len(group_levels)
                liquidity[i] = -1
                liquidity_level[i] = avg_level
                liquidity_end[i] = group_end
                liquidity_swept[i] = swept

        # Convierte arrays a Series con los nombres apropiados.
        liq_series = pd.Series(liquidity, name="Liquidity")
        level_series = pd.Series(liquidity_level, name="Level")
        end_series = pd.Series(liquidity_end, name="End")
        swept_series = pd.Series(liquidity_swept, name="Swept")

        return pd.concat([liq_series, level_series, end_series, swept_series], axis=1)

    @classmethod
    def previous_high_low(cls, ohlc: DataFrame, time_frame: str = "1D") -> Series:
        """
        High Low Anterior
        Este método retorna el máximo y mínimo anterior del marco de tiempo dado.

        parámetros:
        time_frame: str - el marco de tiempo para obtener el máximo y mínimo anterior 15m, 1H, 4H, 1D, 1W, 1M

        retorna:
        PreviousHigh = el máximo anterior
        PreviousLow = el mínimo anterior
        BrokenHigh = 1 una vez que el precio ha roto el máximo anterior del timeframe, 0 en caso contrario
        BrokenLow = 1 una vez que el precio ha roto el mínimo anterior del timeframe, 0 en caso contrario
        """

        ohlc.index = pd.to_datetime(ohlc.index)

        previous_high = np.zeros(len(ohlc), dtype=np.float32)
        previous_low = np.zeros(len(ohlc), dtype=np.float32)
        broken_high = np.zeros(len(ohlc), dtype=np.int32)
        broken_low = np.zeros(len(ohlc), dtype=np.int32)

        resampled_ohlc = ohlc.resample(time_frame).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        ).dropna()

        currently_broken_high = False
        currently_broken_low = False
        last_broken_time = None
        for i in range(len(ohlc)):
            resampled_previous_index = np.where(
                resampled_ohlc.index < ohlc.index[i]
            )[0]
            if len(resampled_previous_index) <= 1:
                previous_high[i] = np.nan
                previous_low[i] = np.nan
                continue
            resampled_previous_index = resampled_previous_index[-2]

            if last_broken_time != resampled_previous_index:
                currently_broken_high = False
                currently_broken_low = False
                last_broken_time = resampled_previous_index

            previous_high[i] = resampled_ohlc["high"].iloc[resampled_previous_index] 
            previous_low[i] = resampled_ohlc["low"].iloc[resampled_previous_index]
            currently_broken_high = ohlc["high"].iloc[i] > previous_high[i] or currently_broken_high
            currently_broken_low = ohlc["low"].iloc[i] < previous_low[i] or currently_broken_low
            broken_high[i] = 1 if currently_broken_high else 0
            broken_low[i] = 1 if currently_broken_low else 0

        previous_high = pd.Series(previous_high, name="PreviousHigh")
        previous_low = pd.Series(previous_low, name="PreviousLow")
        broken_high = pd.Series(broken_high, name="BrokenHigh")
        broken_low = pd.Series(broken_low, name="BrokenLow")

        return pd.concat([previous_high, previous_low, broken_high, broken_low], axis=1)

    @classmethod
    def sessions(
        cls,
        ohlc: DataFrame,
        session: str,
        start_time: str = "",
        end_time: str = "",
        time_zone: str = "UTC",
    ) -> Series:
        """
        Sesiones
        Este método retorna qué velas están dentro de la sesión especificada

        parámetros:
        session: str - la sesión que quieres verificar (Sydney, Tokyo, London, New York, Asian kill zone, London open kill zone, New York kill zone, london close kill zone, Custom)
        start_time: str - la hora de inicio de la sesión en formato "HH:MM" solo requerido para sesión personalizada.
        end_time: str - la hora de fin de la sesión en formato "HH:MM" solo requerido para sesión personalizada.
        time_zone: str - la zona horaria de las velas puede estar en formato "UTC+0" o "GMT+0"

        retorna:
        Active = 1 si la vela está dentro de la sesión, 0 si no
        High = el punto más alto de la sesión
        Low = el punto más bajo de la sesión
        """

        if session == "Custom" and (start_time == "" or end_time == ""):
            raise ValueError("Custom session requires a start and end time")

        default_sessions = {
            "Sydney": {
                "start": "21:00",
                "end": "06:00",
            },
            "Tokyo": {
                "start": "00:00",
                "end": "09:00",
            },
            "London": {
                "start": "07:00",
                "end": "16:00",
            },
            "New York": {
                "start": "13:00",
                "end": "22:00",
            },
            "Asian kill zone": {
                "start": "00:00",
                "end": "04:00",
            },
            "London open kill zone": {
                "start": "6:00",
                "end": "9:00",
            },
            "New York kill zone": {
                "start": "11:00",
                "end": "14:00",
            },
            "london close kill zone": {
                "start": "14:00",
                "end": "16:00",
            },
            "Custom": {
                "start": start_time,
                "end": end_time,
            },
        }

        ohlc.index = pd.to_datetime(ohlc.index)
        if time_zone != "UTC":
            time_zone = time_zone.replace("GMT", "Etc/GMT")
            time_zone = time_zone.replace("UTC", "Etc/GMT")
            ohlc.index = ohlc.index.tz_localize(time_zone).tz_convert("UTC")

        start_time = datetime.strptime(
            default_sessions[session]["start"], "%H:%M"
        ).strftime("%H:%M")
        start_time = datetime.strptime(start_time, "%H:%M")
        end_time = datetime.strptime(
            default_sessions[session]["end"], "%H:%M"
        ).strftime("%H:%M")
        end_time = datetime.strptime(end_time, "%H:%M")

        # si las velas están entre la hora de inicio y fin entonces es una sesión activa
        active = np.zeros(len(ohlc), dtype=np.int32)
        high = np.zeros(len(ohlc), dtype=np.float32)
        low = np.zeros(len(ohlc), dtype=np.float32)

        for i in range(len(ohlc)):
            current_time = ohlc.index[i].strftime("%H:%M")
            # convierte la hora actual al segundo del día
            current_time = datetime.strptime(current_time, "%H:%M")
            if (start_time < end_time and start_time <= current_time <= end_time) or (
                start_time >= end_time
                and (start_time <= current_time or current_time <= end_time)
            ):
                active[i] = 1
                high[i] = max(ohlc["high"].iloc[i], high[i - 1] if i > 0 else 0)
                low[i] = min(
                    ohlc["low"].iloc[i],
                    low[i - 1] if i > 0 and low[i - 1] != 0 else float("inf"),
                )

        active = pd.Series(active, name="Active")
        high = pd.Series(high, name="High")
        low = pd.Series(low, name="Low")

        return pd.concat([active, high, low], axis=1)

    @classmethod
    def retracements(cls, ohlc: DataFrame, swing_highs_lows: DataFrame) -> Series:
        """
        Retroceso
        Este método retorna el porcentaje de un retroceso desde el swing high o low

        parámetros:
        swing_highs_lows: DataFrame - proporciona el dataframe de la función swing_highs_lows

        retorna:
        Direction = 1 si retroceso alcista, -1 si retroceso bajista
        CurrentRetracement% = el porcentaje de retroceso actual desde el swing high o low
        DeepestRetracement% = el porcentaje de retroceso más profundo desde el swing high o low
        """

        swing_highs_lows = swing_highs_lows.copy()

        direction = np.zeros(len(ohlc), dtype=np.int32)
        current_retracement = np.zeros(len(ohlc), dtype=np.float64)
        deepest_retracement = np.zeros(len(ohlc), dtype=np.float64)

        top = 0
        bottom = 0
        for i in range(len(ohlc)):
            if swing_highs_lows["HighLow"].iloc[i] == 1:
                direction[i] = 1
                top = swing_highs_lows["Level"].iloc[i]
                # deepest_retracement[i] = 0
            elif swing_highs_lows["HighLow"].iloc[i] == -1:
                direction[i] = -1
                bottom = swing_highs_lows["Level"].iloc[i]
                # deepest_retracement[i] = 0
            else:
                direction[i] = direction[i - 1] if i > 0 else 0

            if direction[i - 1] == 1:
                current_retracement[i] = round(
                    100 - (((ohlc["low"].iloc[i] - bottom) / (top - bottom)) * 100), 1
                )
                deepest_retracement[i] = max(
                    (
                        deepest_retracement[i - 1]
                        if i > 0 and direction[i - 1] == 1
                        else 0
                    ),
                    current_retracement[i],
                )
            if direction[i] == -1:
                current_retracement[i] = round(
                    100 - ((ohlc["high"].iloc[i] - top) / (bottom - top)) * 100, 1
                )
                deepest_retracement[i] = max(
                    (
                        deepest_retracement[i - 1]
                        if i > 0 and direction[i - 1] == -1
                        else 0
                    ),
                    current_retracement[i],
                )

        # desplaza los arrays por 1
        current_retracement = np.roll(current_retracement, 1)
        deepest_retracement = np.roll(deepest_retracement, 1)
        direction = np.roll(direction, 1)

        # elimina los primeros 3 retrocesos ya que se calculan incorrectamente debido a datos insuficientes
        remove_first_count = 0
        for i in range(len(direction)):
            if i + 1 == len(direction):
                break
            if direction[i] != direction[i + 1]:
                remove_first_count += 1
            direction[i] = 0
            current_retracement[i] = 0
            deepest_retracement[i] = 0
            if remove_first_count == 3:
                direction[i + 1] = 0
                current_retracement[i + 1] = 0
                deepest_retracement[i + 1] = 0
                break

        direction = pd.Series(direction, name="Direction")
        current_retracement = pd.Series(current_retracement, name="CurrentRetracement%")
        deepest_retracement = pd.Series(deepest_retracement, name="DeepestRetracement%")

        return pd.concat([direction, current_retracement, deepest_retracement], axis=1)

    @classmethod
    def equal_highs_lows(cls, ohlc: DataFrame, swing_highs_lows: DataFrame, tolerance: float = 0.0001) -> Series:
        """
        Highs/Lows Iguales
        Este método identifica niveles donde hay múltiples swing highs o swing lows en el mismo precio,
        indicando zonas de resistencia o soporte significativas.

        parámetros:
        swing_highs_lows: DataFrame - proporciona el dataframe de la función swing_highs_lows
        tolerance: float - la tolerancia para considerar que dos niveles son iguales (por defecto 0.0001)

        retorna:
        EqualLevel = 1 si equal highs, -1 si equal lows, 0 si no hay equal level
        Level = el nivel del equal high o low
        Count = el número de veces que se ha tocado este nivel
        FirstIndex = el índice de la primera vez que se tocó este nivel
        LastIndex = el índice de la última vez que se tocó este nivel
        Strength = la fuerza del nivel basada en el número de toques y la distancia temporal
        """

        swing_highs_lows = swing_highs_lows.copy()
        n = len(ohlc)
        
        # Inicializa arrays de salida
        equal_level = np.full(n, np.nan, dtype=np.float32)
        level = np.full(n, np.nan, dtype=np.float32)
        count = np.full(n, np.nan, dtype=np.int32)
        first_index = np.full(n, np.nan, dtype=np.int32)
        last_index = np.full(n, np.nan, dtype=np.int32)
        strength = np.full(n, np.nan, dtype=np.float32)

        # Obtiene los swing highs y lows
        swing_high_indices = np.where(swing_highs_lows["HighLow"] == 1)[0]
        swing_low_indices = np.where(swing_highs_lows["HighLow"] == -1)[0]
        
        swing_high_levels = swing_highs_lows["Level"].iloc[swing_high_indices].values
        swing_low_levels = swing_highs_lows["Level"].iloc[swing_low_indices].values

        # Procesa Equal Highs
        if len(swing_high_indices) > 1:
            for i in range(len(swing_high_indices)):
                current_level = swing_high_levels[i]
                current_index = swing_high_indices[i]
                
                # Busca otros swing highs en el mismo nivel
                equal_indices = []
                equal_levels = []
                
                for j in range(len(swing_high_indices)):
                    if i != j and abs(swing_high_levels[j] - current_level) <= tolerance:
                        equal_indices.append(swing_high_indices[j])
                        equal_levels.append(swing_high_levels[j])
                
                # Si hay al menos un swing high adicional en el mismo nivel
                if len(equal_indices) > 0:
                    equal_indices.append(current_index)
                    equal_levels.append(current_level)
                    
                    # Ordena por índice para obtener first y last
                    sorted_indices = sorted(equal_indices)
                    first_idx = sorted_indices[0]
                    last_idx = sorted_indices[-1]
                    
                    # Calcula el nivel promedio
                    avg_level = np.mean(equal_levels)
                    
                    # Calcula la fuerza basada en el número de toques y la distancia temporal
                    touch_count = len(equal_indices)
                    time_distance = last_idx - first_idx
                    strength_value = touch_count * (1 + 1 / (time_distance + 1))  # Más toques y menos tiempo = más fuerte
                    
                    # Marca todos los índices donde ocurrió este equal high
                    for idx in equal_indices:
                        equal_level[idx] = 1
                        level[idx] = avg_level
                        count[idx] = touch_count
                        first_index[idx] = first_idx
                        last_index[idx] = last_idx
                        strength[idx] = strength_value

        # Procesa Equal Lows
        if len(swing_low_indices) > 1:
            for i in range(len(swing_low_indices)):
                current_level = swing_low_levels[i]
                current_index = swing_low_indices[i]
                
                # Busca otros swing lows en el mismo nivel
                equal_indices = []
                equal_levels = []
                
                for j in range(len(swing_low_indices)):
                    if i != j and abs(swing_low_levels[j] - current_level) <= tolerance:
                        equal_indices.append(swing_low_indices[j])
                        equal_levels.append(swing_low_levels[j])
                
                # Si hay al menos un swing low adicional en el mismo nivel
                if len(equal_indices) > 0:
                    equal_indices.append(current_index)
                    equal_levels.append(current_level)
                    
                    # Ordena por índice para obtener first y last
                    sorted_indices = sorted(equal_indices)
                    first_idx = sorted_indices[0]
                    last_idx = sorted_indices[-1]
                    
                    # Calcula el nivel promedio
                    avg_level = np.mean(equal_levels)
                    
                    # Calcula la fuerza basada en el número de toques y la distancia temporal
                    touch_count = len(equal_indices)
                    time_distance = last_idx - first_idx
                    strength_value = touch_count * (1 + 1 / (time_distance + 1))  # Más toques y menos tiempo = más fuerte
                    
                    # Marca todos los índices donde ocurrió este equal low
                    for idx in equal_indices:
                        equal_level[idx] = -1
                        level[idx] = avg_level
                        count[idx] = touch_count
                        first_index[idx] = first_idx
                        last_index[idx] = last_idx
                        strength[idx] = strength_value

        # Convierte arrays a Series con los nombres apropiados
        equal_level_series = pd.Series(equal_level, name="EqualLevel")
        level_series = pd.Series(level, name="Level")
        count_series = pd.Series(count, name="Count")
        first_index_series = pd.Series(first_index, name="FirstIndex")
        last_index_series = pd.Series(last_index, name="LastIndex")
        strength_series = pd.Series(strength, name="Strength")

        return pd.concat([
            equal_level_series, 
            level_series, 
            count_series, 
            first_index_series, 
            last_index_series, 
            strength_series
        ], axis=1)

    @classmethod
    def premium_discount_zones(cls, ohlc: DataFrame, swing_highs_lows: DataFrame, lookback_period: int = 50) -> Series:
        """
        Zonas de Precio Premium/Descuento
        Este método identifica zonas donde el precio está considerado "caro" (premium) o "barato" (discount)
        basándose en rangos de swing importantes. Las zonas se calculan usando el 50% del rango como punto de referencia.

        parámetros:
        swing_highs_lows: DataFrame - proporciona el dataframe de la función swing_highs_lows
        lookback_period: int - el número de velas hacia atrás para buscar el swing más relevante

        retorna:
        Zone = 1 si zona premium, -1 si zona discount, 0 si en el medio del rango
        RangeHigh = el swing high del rango de referencia
        RangeLow = el swing low del rango de referencia
        MidPoint = el punto medio (50%) del rango
        DistanceFromMid = la distancia porcentual desde el punto medio
        RangeStrength = la fuerza del rango basada en su tamaño y antigüedad
        """

        swing_highs_lows = swing_highs_lows.copy()
        n = len(ohlc)
        
        # Inicializa arrays de salida
        zone = np.full(n, np.nan, dtype=np.float32)
        range_high = np.full(n, np.nan, dtype=np.float32)
        range_low = np.full(n, np.nan, dtype=np.float32)
        mid_point = np.full(n, np.nan, dtype=np.float32)
        distance_from_mid = np.full(n, np.nan, dtype=np.float32)
        range_strength = np.full(n, np.nan, dtype=np.float32)

        # Obtiene los swing highs y lows
        swing_high_indices = np.where(swing_highs_lows["HighLow"] == 1)[0]
        swing_low_indices = np.where(swing_highs_lows["HighLow"] == -1)[0]
        
        swing_high_levels = swing_highs_lows["Level"].iloc[swing_high_indices].values
        swing_low_levels = swing_highs_lows["Level"].iloc[swing_low_indices].values

        for i in range(n):
            current_price = ohlc["close"].iloc[i]
            
            # Busca el swing high más reciente dentro del período de lookback
            recent_high_indices = swing_high_indices[swing_high_indices <= i]
            recent_high_indices = recent_high_indices[recent_high_indices >= max(0, i - lookback_period)]
            
            # Busca el swing low más reciente dentro del período de lookback
            recent_low_indices = swing_low_indices[swing_low_indices <= i]
            recent_low_indices = recent_low_indices[recent_low_indices >= max(0, i - lookback_period)]
            
            if len(recent_high_indices) > 0 and len(recent_low_indices) > 0:
                # Encuentra el swing high y low más recientes
                latest_high_idx = recent_high_indices[-1]
                latest_low_idx = recent_low_indices[-1]
                
                # Obtiene los niveles correspondientes
                high_level = swing_highs_lows["Level"].iloc[latest_high_idx]
                low_level = swing_highs_lows["Level"].iloc[latest_low_idx]
                
                # Calcula el punto medio del rango
                mid_level = (high_level + low_level) / 2
                range_size = high_level - low_level
                
                # Calcula la distancia desde el punto medio como porcentaje del rango
                if range_size > 0:
                    distance_pct = ((current_price - mid_level) / range_size) * 100
                else:
                    distance_pct = 0
                
                # Determina la zona basada en la distancia desde el punto medio
                if distance_pct > 5:  # Más de 5% por encima del medio = Premium
                    zone[i] = 1
                elif distance_pct < -5:  # Más de 5% por debajo del medio = Discount
                    zone[i] = -1
                else:  # Dentro del 5% del medio = Neutral
                    zone[i] = 0
                
                # Asigna los valores del rango
                range_high[i] = high_level
                range_low[i] = low_level
                mid_point[i] = mid_level
                distance_from_mid[i] = distance_pct
                
                # Calcula la fuerza del rango basada en su tamaño y antigüedad
                # Rango más grande y más reciente = más fuerte
                age_factor = 1 / (i - max(latest_high_idx, latest_low_idx) + 1)
                size_factor = range_size / ohlc["close"].iloc[i]  # Normalizado por el precio actual
                range_strength[i] = (age_factor + size_factor) * 100

        # Convierte arrays a Series con los nombres apropiados
        zone_series = pd.Series(zone, name="Zone")
        range_high_series = pd.Series(range_high, name="RangeHigh")
        range_low_series = pd.Series(range_low, name="RangeLow")
        mid_point_series = pd.Series(mid_point, name="MidPoint")
        distance_from_mid_series = pd.Series(distance_from_mid, name="DistanceFromMid")
        range_strength_series = pd.Series(range_strength, name="RangeStrength")

        return pd.concat([
            zone_series,
            range_high_series,
            range_low_series,
            mid_point_series,
            distance_from_mid_series,
            range_strength_series
        ], axis=1)

    @classmethod
    def trend_indicator(cls, ohlc: DataFrame, swing_highs_lows: DataFrame, lookback_period: int = 20) -> pd.DataFrame:
        """
        Indicador de Tendencia estructural menos estricto:
        0 = sin tendencia, +1 = alcista, +2 = alcista fuerte, -1 = bajista, -2 = bajista fuerte
        """
        n = len(ohlc)
        trend = np.full(n, np.nan, dtype=np.float32)
        swings = swing_highs_lows.copy()
        for i in range(lookback_period, n):
            swings_window = swings.iloc[:i].dropna()
            if len(swings_window) < 4:
                trend[i] = 0
                continue
            last_swings = swings_window.iloc[-4:]
            swing_types = last_swings['HighLow'].values
            swing_levels = last_swings['Level'].values
            # Tendencia alcista si HH o HL crecientes
            alcista = False
            if np.all(swing_types == [1, -1, 1, -1]):
                hh1, hl1, hh2, hl2 = swing_levels
                if hh2 > hh1 or hl2 > hl1:
                    alcista = True
            elif np.all(swing_types == [-1, 1, -1, 1]):
                lh1, ll1, lh2, ll2 = swing_levels
                if ll2 > ll1 or lh2 > lh1:
                    alcista = True
            # Tendencia bajista si LH o LL decrecientes
            bajista = False
            if np.all(swing_types == [1, -1, 1, -1]):
                hh1, hl1, hh2, hl2 = swing_levels
                if hh2 < hh1 or hl2 < hl1:
                    bajista = True
            elif np.all(swing_types == [-1, 1, -1, 1]):
                lh1, ll1, lh2, ll2 = swing_levels
                if ll2 < ll1 or lh2 < lh1:
                    bajista = True
            # Inicial: 0 sin tendencia
            trend[i] = 0
            if alcista:
                trend[i] = 1
            if bajista:
                trend[i] = -1
            # Fuerte si hay BOS, OB o FVG a favor
            if trend[i] == 1:
                bos_choch = cls.bos_choch(ohlc.iloc[:i+1], swings.iloc[:i+1])
                ob_data = cls.ob(ohlc.iloc[:i+1], swings.iloc[:i+1])
                fvg_data = cls.fvg(ohlc.iloc[:i+1])
                if (bos_choch['BOS'].iloc[-5:] == 1).sum() > 0 or (ob_data['OB'].iloc[-5:] == 1).sum() > 0 or (fvg_data['FVG'].iloc[-5:] == 1).sum() > 0:
                    trend[i] = 2
            if trend[i] == -1:
                bos_choch = cls.bos_choch(ohlc.iloc[:i+1], swings.iloc[:i+1])
                ob_data = cls.ob(ohlc.iloc[:i+1], swings.iloc[:i+1])
                fvg_data = cls.fvg(ohlc.iloc[:i+1])
                if (bos_choch['BOS'].iloc[-5:] == -1).sum() > 0 or (ob_data['OB'].iloc[-5:] == -1).sum() > 0 or (fvg_data['FVG'].iloc[-5:] == -1).sum() > 0:
                    trend[i] = -2
        trend_series = pd.Series(trend, name="Trend")
        return pd.DataFrame({"Trend": trend_series})

    @staticmethod
    def vwap(df):
        """
        Calcula el VWAP (Volume Weighted Average Price) para un DataFrame OHLCV.
        Requiere columnas: 'high', 'low', 'close', 'volume'.
        Devuelve una Serie con el VWAP acumulado.
        """
        precio_tipico = (df['high'] + df['low'] + df['close']) / 3
        vwap = (precio_tipico * df['volume']).cumsum() / df['volume'].cumsum()
        return vwap
