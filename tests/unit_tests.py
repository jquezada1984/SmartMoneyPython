# this file will be used to test the functionality and accuracy of all the indicators in the smartmoneyconcepts package

import os
import sys
import time
import pandas as pd
import unittest

BASE_DIR = os.path.dirname(__file__)
sys.path.append(os.path.abspath(os.path.join(BASE_DIR, "..")))
from smartmoneyconcepts.smc import smc

# define and import test data
test_instrument = "EURUSD"
instrument_data = f"{test_instrument}_15M.csv"
TEST_DATA_DIR = os.path.join(BASE_DIR, "test_data", test_instrument)
df = pd.read_csv(os.path.join(TEST_DATA_DIR, instrument_data))
df = df.set_index("Date")
df.index = pd.to_datetime(df.index)

class TestSmartMoneyConcepts(unittest.TestCase):
    # to test each function in the smartmoneyconcepts package
    # each function will be called and the result will be compared to the result data

    def test_fvg(self):
        start_time = time.time()
        fvg_data = smc.fvg(df)
        fvg_result_data = pd.read_csv(
            os.path.join(TEST_DATA_DIR, "fvg_result_data.csv")
        )
        print("fvg test time: ", time.time() - start_time)
        pd.testing.assert_frame_equal(fvg_data, fvg_result_data, check_dtype=False)

    def test_fvg_consecutive(self):
        start_time = time.time()
        fvg_data = smc.fvg(df, join_consecutive=True)
        fvg_consecutive_result_data = pd.read_csv(
            os.path.join(TEST_DATA_DIR, "fvg_consecutive_result_data.csv")
        )
        print("fvg consecutive test time: ", time.time() - start_time)
        pd.testing.assert_frame_equal(fvg_data, fvg_consecutive_result_data, check_dtype=False)

    def test_swing_highs_lows(self):
        start_time = time.time()
        swing_highs_lows_data = smc.swing_highs_lows(df, swing_length=5)
        swing_highs_lows_result_data = pd.read_csv(
            os.path.join(TEST_DATA_DIR, "swing_highs_lows_result_data.csv")
        )
        print("swing_highs_lows test time: ", time.time() - start_time)
        pd.testing.assert_frame_equal(swing_highs_lows_data, swing_highs_lows_result_data, check_dtype=False)

    def test_bos_choch(self):
        start_time = time.time()
        swing_highs_lows_data = smc.swing_highs_lows(df, swing_length=5)
        bos_choch_data = smc.bos_choch(df, swing_highs_lows_data)
        bos_choch_result_data = pd.read_csv(
            os.path.join(TEST_DATA_DIR, "bos_choch_result_data.csv")
        )
        print("bos_choch test time: ", time.time() - start_time)
        pd.testing.assert_frame_equal(
            bos_choch_data, bos_choch_result_data, check_dtype=False
        )

    def test_ob(self):
        start_time = time.time()
        swing_highs_lows_data = smc.swing_highs_lows(df, swing_length=5)
        ob_data = smc.ob(df, swing_highs_lows_data)
        ob_result_data = pd.read_csv(
            os.path.join(TEST_DATA_DIR, "ob_result_data.csv")
        )
        print("ob test time: ", time.time() - start_time)
        pd.testing.assert_frame_equal(ob_data, ob_result_data, check_dtype=False)

    def test_ob_early_data(self):
        """Ensure early candles do not cause index errors in OB calculation."""
        short_df = pd.DataFrame(
            {
                "open": [1.0, 1.1, 1.2],
                "high": [1.05, 1.15, 1.25],
                "low": [0.95, 1.05, 1.15],
                "close": [1.02, 1.14, 1.24],
                "volume": [5, 6, 7],
            }
        )
        swing = smc.swing_highs_lows(short_df, swing_length=1)
        ob_df = smc.ob(short_df, swing)
        self.assertEqual(len(ob_df), len(short_df))

    def test_liquidity(self):
        start_time = time.time()
        swing_highs_lows_data = smc.swing_highs_lows(df, swing_length=5)
        liquidity_data = smc.liquidity(df, swing_highs_lows_data)
        liquidity_result_data = pd.read_csv(
            os.path.join(TEST_DATA_DIR, "liquidity_result_data.csv")
        )
        print("liquidity test time: ", time.time() - start_time)
        pd.testing.assert_frame_equal(liquidity_data, liquidity_result_data, check_dtype=False)

    def test_previous_high_low(self):
        # test 4h time frame
        start_time = time.time()
        previous_high_low_data = smc.previous_high_low(df, time_frame="4h")
        previous_high_low_result_data = pd.read_csv(
            os.path.join(TEST_DATA_DIR, "previous_high_low_result_data_4h.csv")
        )
        print("previous_high_low test time: ", time.time() - start_time)
        pd.testing.assert_frame_equal(previous_high_low_data, previous_high_low_result_data, check_dtype=False)

        # test 1D time frame
        start_time = time.time()
        previous_high_low_data = smc.previous_high_low(df, time_frame="1D")
        previous_high_low_result_data = pd.read_csv(
            os.path.join(TEST_DATA_DIR, "previous_high_low_result_data_1D.csv")
        )
        print("previous_high_low test time: ", time.time() - start_time)
        pd.testing.assert_frame_equal(previous_high_low_data, previous_high_low_result_data, check_dtype=False)

        # test W time frame
        start_time = time.time()
        previous_high_low_data = smc.previous_high_low(df, time_frame="W")
        previous_high_low_result_data = pd.read_csv(
            os.path.join(TEST_DATA_DIR, "previous_high_low_result_data_W.csv")
        )
        print("previous_high_low test time: ", time.time() - start_time)
        pd.testing.assert_frame_equal(previous_high_low_data, previous_high_low_result_data, check_dtype=False)

    def test_sessions(self):
        start_time = time.time()
        sessions = smc.sessions(df, session="London")
        sessions_result_data = pd.read_csv(
            os.path.join(TEST_DATA_DIR, "sessions_result_data.csv")
        )
        print("sessions test time: ", time.time() - start_time)
        pd.testing.assert_frame_equal(sessions, sessions_result_data, check_dtype=False)

    def test_retracements(self):
        start_time = time.time()
        swing_highs_lows_data = smc.swing_highs_lows(df, swing_length=5)
        retracements_data = smc.retracements(df, swing_highs_lows_data)
        retracements_result_data = pd.read_csv(
            os.path.join(TEST_DATA_DIR, "retracements_result_data.csv")
        )
        print("retracements test time: ", time.time() - start_time)
        pd.testing.assert_frame_equal(retracements_data, retracements_result_data, check_dtype=False)

    def test_equal_highs_lows(self):
        start_time = time.time()
        swing_highs_lows_data = smc.swing_highs_lows(df, swing_length=5)
        equal_highs_lows_data = smc.equal_highs_lows(df, swing_highs_lows_data, tolerance=0.0001)
        
        # Verifica que el resultado tiene las columnas esperadas
        expected_columns = ["EqualLevel", "Level", "Count", "FirstIndex", "LastIndex", "Strength"]
        self.assertEqual(list(equal_highs_lows_data.columns), expected_columns)
        
        # Verifica que el resultado tiene la misma longitud que el dataframe original
        self.assertEqual(len(equal_highs_lows_data), len(df))
        
        # Verifica que los valores de EqualLevel son válidos (1, -1, o NaN)
        valid_values = equal_highs_lows_data["EqualLevel"].dropna()
        if len(valid_values) > 0:
            self.assertTrue(all(val in [1, -1] for val in valid_values))
        
        print("equal_highs_lows test time: ", time.time() - start_time)

    def test_premium_discount_zones(self):
        start_time = time.time()
        swing_highs_lows_data = smc.swing_highs_lows(df, swing_length=5)
        premium_discount_data = smc.premium_discount_zones(df, swing_highs_lows_data, lookback_period=50)
        
        # Verifica que el resultado tiene las columnas esperadas
        expected_columns = ["Zone", "RangeHigh", "RangeLow", "MidPoint", "DistanceFromMid", "RangeStrength"]
        self.assertEqual(list(premium_discount_data.columns), expected_columns)
        
        # Verifica que el resultado tiene la misma longitud que el dataframe original
        self.assertEqual(len(premium_discount_data), len(df))
        
        # Verifica que los valores de Zone son válidos (1, -1, 0, o NaN)
        valid_values = premium_discount_data["Zone"].dropna()
        if len(valid_values) > 0:
            self.assertTrue(all(val in [1, -1, 0] for val in valid_values))
        
        # Verifica que MidPoint está aproximadamente entre RangeHigh y RangeLow cuando están disponibles
        # Usa una tolerancia para errores de precisión en punto flotante
        valid_ranges = premium_discount_data.dropna(subset=["RangeHigh", "RangeLow", "MidPoint"])
        if len(valid_ranges) > 0:
            for _, row in valid_ranges.iterrows():
                tolerance = 0.001  # Tolerancia del 0.1%
                self.assertGreaterEqual(row["MidPoint"], row["RangeLow"] - tolerance)
                self.assertLessEqual(row["MidPoint"], row["RangeHigh"] + tolerance)
        
        print("premium_discount_zones test time: ", time.time() - start_time)

    def test_trend_indicator(self):
        start_time = time.time()
        swing_highs_lows_data = smc.swing_highs_lows(df, swing_length=5)
        trend_data = smc.trend_indicator(df, swing_highs_lows_data, lookback_period=20)
        
        # Verifica que el resultado tiene las columnas esperadas
        expected_columns = ["Trend", "Strength", "Confidence", "LastBOS", "LastCHOCH", "TrendChange"]
        self.assertEqual(list(trend_data.columns), expected_columns)
        
        # Verifica que el resultado tiene la misma longitud que el dataframe original
        self.assertEqual(len(trend_data), len(df))
        
        # Verifica que los valores de Trend son válidos (1, -1, 0, o NaN)
        valid_trends = trend_data["Trend"].dropna()
        if len(valid_trends) > 0:
            self.assertTrue(all(val in [1, -1, 0] for val in valid_trends))
        
        # Verifica que Strength está en el rango 0-100
        valid_strengths = trend_data["Strength"].dropna()
        if len(valid_strengths) > 0:
            self.assertTrue(all(0 <= val <= 100 for val in valid_strengths))
        
        # Verifica que Confidence está en el rango 0-100
        valid_confidences = trend_data["Confidence"].dropna()
        if len(valid_confidences) > 0:
            self.assertTrue(all(0 <= val <= 100 for val in valid_confidences))
        
        # Verifica que TrendChange es binario (0 o 1)
        valid_changes = trend_data["TrendChange"].dropna()
        if len(valid_changes) > 0:
            self.assertTrue(all(val in [0, 1] for val in valid_changes))
        
        print("trend_indicator test time: ", time.time() - start_time)


if __name__ == "__main__":
    unittest.main()


# def generate_results_data():
#     fvg_data = smc.fvg(df)
#     fvg_data.to_csv(
#         os.path.join("test_data", test_instrument, "fvg_result_data.csv"), index=False
#     )

    # fvg_data = smc.fvg(df, join_consecutive=True)
    # fvg_data.to_csv(
    #     os.path.join("test_data", test_instrument, "fvg_consecutive_result_data.csv"), index=False
    # )

#     swing_highs_lows_data = smc.swing_highs_lows(df, swing_length=5)
#     swing_highs_lows_data.to_csv(
#         os.path.join("test_data", test_instrument, "swing_highs_lows_result_data.csv"),
#         index=False,
#     )

#     bos_choch_data = smc.bos_choch(df, swing_highs_lows_data)
#     bos_choch_data.to_csv(
#         os.path.join("test_data", test_instrument, "bos_choch_result_data.csv"),
#         index=False,
#     )

#     ob_data = smc.ob(df, swing_highs_lows_data)
#     ob_data.to_csv(
#         os.path.join("test_data", test_instrument, "ob_result_data.csv"), index=False
#     )

#     liquidity_data = smc.liquidity(df, swing_highs_lows_data)
#     liquidity_data.to_csv(
#         os.path.join("test_data", test_instrument, "liquidity_result_data.csv"),
#         index=False,
#     )

#     previous_high_low_data = smc.previous_high_low(df, time_frame="4h")
#     previous_high_low_data.to_csv(
#         os.path.join("test_data", test_instrument, "previous_high_low_result_data_4h.csv"),
#         index=False,
#     )

#     previous_high_low_data = smc.previous_high_low(df, time_frame="1D")
#     previous_high_low_data.to_csv(
#         os.path.join("test_data", test_instrument, "previous_high_low_result_data_1D.csv"),
#         index=False,
#     )

#     previous_high_low_data = smc.previous_high_low(df, time_frame="W")
#     previous_high_low_data.to_csv(
#         os.path.join("test_data", test_instrument, "previous_high_low_result_data_W.csv"),
#         index=False,
#     )

#     sessions = smc.sessions(df, session="London")
#     sessions.to_csv(
#         os.path.join("test_data", test_instrument, "sessions_result_data.csv"),
#         index=False,
#     )

#     retracements = smc.retracements(df, swing_highs_lows_data)
#     retracements.to_csv(
#         os.path.join("test_data", test_instrument, "retracements_result_data.csv"),
#         index=False,
#     )


# generate_results_data()
