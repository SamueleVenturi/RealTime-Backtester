import pandas as pd

UPDATE_INTERVAL = 60
crypto_symbols = []

chart = None
chart_data = pd.DataFrame()
list_of_lines = []
fibonacci_levels = []
checked_pivots = []

import asyncio
wait_event = asyncio.Event()