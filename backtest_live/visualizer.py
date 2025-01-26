from lightweight_charts import Chart
from data_manager import fetch_data_from_binance, fetch_data_from_yf, get_market_calendar
import global_vars
from datetime import datetime, timedelta
import asyncio
from danielStrategyLogic import DanielStrategyLogic, Portfolio

is_backtest_mode = False
symbol_type = None
update_task = None  
strategy_task = None  
run_backtest_task = None

def clear_global_vars():
    for line in global_vars.list_of_lines:
        line.delete()
    global_vars.list_of_lines.clear()

    for line in global_vars.fibonacci_levels:
        line.delete()
    global_vars.fibonacci_levels.clear()

    global_vars.checked_pivots.clear()

def get_bar_data(chart, symbol, timeframe, limit):
    if symbol == 'n/a':
        return False
    elif symbol_type:
        fetch_data_from_binance(symbol, timeframe, limit=limit)
    else:
        fetch_data_from_yf(symbol, timeframe, limit=limit, chart=chart)
    return True

def start_task(chart):
    global update_task, strategy_task
    update_task = asyncio.create_task(schedule_next_update(chart))
    strategy_task = asyncio.create_task(run_strategy())
    print(f"Started update task: {update_task}")
    print(f"Started strategy task: {strategy_task}")

def close_tasks():
    global update_task, strategy_task, run_backtest_task
    if update_task is not None:
        print(f"Closing update task: {update_task}")
        update_task.cancel()

    if strategy_task is not None:
        print(f"Closing strategy task: {strategy_task}")
        strategy_task.cancel()
        clear_global_vars()

    if run_backtest_task is not None:
        print(f"Closing run backtest task: {run_backtest_task}")
        run_backtest_task.cancel()
        clear_global_vars()

def on_search(chart, searched_string):
    global symbol_type, run_backtest_task
    symbol_type = searched_string in global_vars.crypto_symbols
    close_tasks()
    if get_bar_data(chart, searched_string, chart.topbar['timeframe'].value, 500):
        chart.topbar['symbol'].set(searched_string)
        if is_backtest_mode:
            df = global_vars.chart_data.copy()
            run_backtest_task = asyncio.create_task(run_backtest(chart, df))
        else:
            chart.set(global_vars.chart_data)
            start_task(chart)

def on_timeframe_selection(chart):
    global run_backtest_task
    close_tasks()
    if get_bar_data(chart, chart.topbar['symbol'].value, chart.topbar['timeframe'].value, 500):
        if is_backtest_mode:
            df = global_vars.chart_data.copy()
            run_backtest_task = asyncio.create_task(run_backtest(chart, df))
        else:
            chart.set(global_vars.chart_data)
            start_task(chart)

async def schedule_next_update(chart):
    while True:
        try:
            symbol = chart.topbar['symbol'].value
            if symbol_type:
                await asyncio.sleep(0.5)
                get_bar_data(chart, symbol, chart.topbar['timeframe'].value, 1)
                chart.set(global_vars.chart_data)
            else:
                market_calendar = get_market_calendar(symbol)
                if market_calendar is None:
                    close_tasks()
                    return
                now = datetime.now()

                schedule = market_calendar.schedule(start_date=now.date(), end_date=now.date())
                if not schedule.empty:
                    market_open = schedule.iloc[0]['market_open'].to_pydatetime().time()
                    market_close = schedule.iloc[0]['market_close'].to_pydatetime().time()

                    current_time = now.time()

                    if market_open <= current_time <= market_close:
                        timeframe = chart.topbar['timeframe'].value
                        minutes = int(timeframe[:-1])
                        next_update_time = (now + timedelta(minutes=minutes)).replace(second=1, microsecond=0)
                        next_update_time = next_update_time.replace(minute=(next_update_time.minute // minutes) * minutes)
                        wait_time = (next_update_time - now).total_seconds()
                        
                        print(f"Waiting for next interval at {next_update_time.strftime('%H:%M:%S')}, sleeping for {wait_time} seconds")
                        await asyncio.sleep(wait_time)

                        get_bar_data(chart, symbol, chart.topbar['timeframe'].value, 1)
                        chart.set(global_vars.chart_data)
                    else:
                        if current_time < market_open:
                            wait_time = (datetime.combine(now.date(), market_open) - now).total_seconds()
                        else:
                            wait_time = (datetime.combine(now.date() + timedelta(days=1), market_open) - now).total_seconds()
                        print(f"Market is closed. Waiting for market to open at {market_open}, sleeping for {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                else:
                    print(f"The market is closed all day on {now.date()}. Checking again tomorrow.")
                    wait_time = (datetime.combine(now.date() + timedelta(days=1), datetime.min.time()) - now).total_seconds()
                    await asyncio.sleep(wait_time)
        except asyncio.CancelledError:
            print("Update task was cancelled")
            break
        except Exception as e:
            print(f"An error occurred in schedule_next_update: {e}")

async def run_strategy():
    strategy = DanielStrategyLogic()
    while True:
        try:
            await global_vars.wait_event.wait()
            global_vars.wait_event.clear()
            if not global_vars.chart_data.empty:
                strategy.execute(global_vars.chart_data)
            else:
                print("Waiting for data...")
        except asyncio.CancelledError:
            print("Strategy task was cancelled")
            break
        except Exception as e:
            print(f"An error occurred in run_strategy: {e}")

async def run_backtest(chart, df):
    depths = [1, 2, 5, 10]
    for depth in depths:
        clear_global_vars()
        global_vars.chart.set()

        portfolio = Portfolio()
        strategy = DanielStrategyLogic(depth=depth)
        global_vars.chart.set(df.head(30))
        for i in range(30, len(df)):
            series = df.iloc[:i+1]
            chart.update(df.iloc[i])
            
            strategy.execute(series)
            portfolio.find_position(series)
            await asyncio.sleep(0.1)
        portfolio.close_all_positions(df)
        portfolio.report()

def plot_chart():
    global_vars.chart = Chart(toolbox=True, debug=False)
    chart = global_vars.chart
    chart.legend(True)
    chart.events.search += on_search
    chart.topbar.textbox('symbol', 'n/a')
    chart.topbar.switcher(
        'timeframe',
        ('1m', '2m', '5m', '15m', '30m'),
        default='1m',
        func=on_timeframe_selection
    )
    chart.topbar.switcher(
        'mode',
        ('Live', 'Backtest'),
        default='Live',
        func=on_mode_switch
    )
    chart.show(block=True)

def on_mode_switch(mode):
    close_tasks()
    global is_backtest_mode
    is_backtest_mode = True if mode.topbar['mode'].value == 'Backtest' else False
    global_vars.chart.set()
    global_vars.chart.topbar['symbol'].set('n/a')