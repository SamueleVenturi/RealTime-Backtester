import numpy as np
from data_manager import send_telegram_message
import global_vars
import pandas as pd
import numpy as np
import uuid
fibonacci_1 = {}
fibonacci_2 = {}

class DanielStrategyLogic:
    def __init__(self, depth=1, levelsFormat="Values"):
        self.depth = depth
        self.levelsFormat = levelsFormat
        
        self.last_index = 0
        self.last_price = 0.0
        self.is_high_last = None
        self.last_opposite_index = 0
        self.last_opposite_price = 0.0
        
        self.lines_drawn = False
        
    def pivots(self, df, length):
        pivot_high_indices = []
        pivot_low_indices = []
  
        for i in range(length, len(df) - length):
            try:
                high_window = df['High'].iloc[i - length:i + length + 1]
                low_window = df['Low'].iloc[i - length:i + length + 1]

                high_central = df['High'].iloc[i]
                low_central = df['Low'].iloc[i]
            except Exception as e:
                print(f"Error in pivots at index {i}: {e}")

            if high_central == max(high_window):
                pivot_high_indices.append(i)
            if low_central == min(low_window):
                pivot_low_indices.append(i)

        return pivot_high_indices, pivot_low_indices     

    def draw_line(self, df, start_index, start_price, end_index, end_price, color, style):
        line = global_vars.chart.trend_line(
            df.index[start_index], start_price,  
            df.index[end_index], end_price,       
            line_color=color, style=style
        )
        return line             

    def update_line(self, df, current_index, current_price, color, style):
        if global_vars.list_of_lines:
            global_vars.list_of_lines[-1].delete()
            global_vars.list_of_lines.pop()
            global_vars.checked_pivots.pop()
        line = self.draw_line(df, self.last_opposite_index, self.last_opposite_price, current_index, current_price, color, style)
        global_vars.list_of_lines.append(line)
        global_vars.checked_pivots.append(current_index)     

    def update_last_pivot(self, current_index, current_price, is_high):
        self.last_index = current_index
        self.last_price = current_price
        self.is_high_last = is_high                     

    def combine_pivots(self, df, pivot_points, pivot_high_indices, color):
        if not self.lines_drawn:
            pivot_points = sorted(set(pivot_points))
            self.is_high_last = None
            for i in range(len(pivot_points)):
                current_index = pivot_points[i]
                try:
                    if (current_index in pivot_high_indices):
                        current_price = df['High'].iloc[current_index]
                        is_high = True
                    else:
                        current_price = df['Low'].iloc[current_index]
                        is_high = False
                except Exception as e:
                    print(f"Error in combine {current_index}: {e}")
                if self.is_high_last is None:
                    self.update_last_pivot(current_index, current_price, is_high)
                    self.last_opposite_index = self.last_index
                    self.last_opposite_price = self.last_price
                    global_vars.checked_pivots.append(current_index)
                else:
                    if self.is_high_last != is_high or (is_high and current_price > self.last_price) or (not is_high and current_price < self.last_price):
                        if self.is_high_last != is_high:
                            self.last_opposite_index = self.last_index
                            self.last_opposite_price = self.last_price
                            line = self.draw_line(df, self.last_index, self.last_price, current_index, current_price, color, 'dotted')
                            global_vars.list_of_lines.append(line)
                            global_vars.checked_pivots.append(current_index)
                        else:
                            self.update_line(df, current_index, current_price, color, 'dotted')
                        self.update_last_pivot(current_index, current_price, is_high)
            self.lines_drawn = True
        else:
            new_pivot_points = [p for p in pivot_points if p > self.last_index]
            for current_index in new_pivot_points:
                try:
                    if (current_index in pivot_high_indices):
                        current_price = df['High'].iloc[current_index]
                        is_high = True
                    else:
                        current_price = df['Low'].iloc[current_index]
                        is_high = False
                except Exception as e:
                    print(f"Error in setting True/False {current_index}: {e}")
                if self.is_high_last != is_high or (is_high and current_price > self.last_price) or (not is_high and current_price < self.last_price):
                    if self.is_high_last != is_high:
                        self.last_opposite_index = self.last_index
                        self.last_opposite_price = self.last_price
                        line = self.draw_line(df, self.last_index, self.last_price, current_index, current_price, color, 'dotted')
                        global_vars.list_of_lines.append(line)
                        global_vars.checked_pivots.append(current_index)
                    else:
                        self.update_line(df, current_index, current_price, color, 'dotted')
                    self.update_last_pivot(current_index, current_price, is_high)     

    def draw_fibonacci_levels(self, df, index_list):
        if len(index_list) < 5:
            return
        if global_vars.fibonacci_levels:
            for line in global_vars.fibonacci_levels:
                line.delete()
            global_vars.fibonacci_levels.clear()

        end_point_1 = index_list[-2]
        start_point_1 = index_list[-3]
        end_point_2 = index_list[-4]
        start_point_2 = index_list[-5]

        global fibonacci_1, fibonacci_2
        fibonacci_1 = self.draw_fibonacci(df, start_point_1, end_point_1)
        fibonacci_2 = self.draw_fibonacci(df, start_point_2, end_point_2)                

    def draw_fibonacci(self, df, start_index, end_index):
        try:
            start_high = df['High'].iloc[start_index]
            start_low = df['Low'].iloc[start_index]
            end_high = df['High'].iloc[end_index]
            end_low = df['Low'].iloc[end_index]
        except Exception as e:
            print(f"Error in draw_fibonacci at indices {start_index}, {end_index}: {e}")

        if self.is_high_last:
            start_price = start_high
            end_price = end_low
        else: 
            start_price = start_low
            end_price = end_high

        fibonacci_Levels = {}
        levels = [-0.25, 0.0, 0.25, 0.5, 0.618, 0.75, 1.0]

        colors = {
            -0.25: '#FF0000',
            0.0: '#808080',
            0.25: '#FF0000',
            0.5: '#00FF00',
            0.618: '#20B2AA',
            0.75: '#FFD700',
            1.0: '#800080'
        }

        for level in levels:
            fib_price = end_price + (start_price - end_price) * level
            line_color = colors.get(level, '#FFFFFF')
            line = self.draw_line(df, start_index, fib_price, end_index, fib_price, line_color, 'dashed')
            global_vars.fibonacci_levels.append(line)
            fibonacci_Levels[level] = fib_price

        return fibonacci_Levels       

    def execute(self, df):
        try:
            swing_high, swing_low = self.pivots(df, self.depth)
            pivot_points = sorted(np.concatenate([swing_high, swing_low]))
            self.combine_pivots(df, pivot_points, swing_high, '#FFFFFF')
            self.draw_fibonacci_levels(df, global_vars.checked_pivots)
        except Exception as e:
            print(e)           
    
class Portfolio:
    def __init__(self):
        self.positions = []
        self.closed_positions = []
        self.balance = 100000
        self.trade_size = 1000
        self.last_alert = None

    def open_position(self, symbol, direction, price, tp_price, sl_price, candle_index):
        position_id = str(uuid.uuid4())
        position = {
            "id": position_id,
            "symbol": symbol,
            "direction": direction,
            "entry_price": price,
            "tp_price": tp_price,
            "sl_price": sl_price,
            "size": self.trade_size,
            "entry_value": self.trade_size / price,
            "timestamp": pd.Timestamp.now(),
            "candle_index": candle_index
        }
        self.positions.append(position)
        print(f"Opened {direction} position for {symbol} at {price}. TP: {tp_price}, SL: {sl_price}, ID: {position_id}, Candle Index: {candle_index}")

    def close_position(self, position, price):
        profit_loss = (         
            (price - position["entry_price"]) * position["entry_value"]
            if position["direction"] == "LONG"
            else (position["entry_price"] - price) * position["entry_value"]
        )
        self.balance += profit_loss
        send_telegram_message(f"Closed {position['direction']} position for {position['symbol']} at {price}. P/L: ${profit_loss:.2f}, ID: {position['id']}")

    def close_all_positions(self, df):
        for position in self.positions:
            if position["direction"] == "LONG":
                for idx in range(position["candle_index"], len(df)):
                    if df['High'].iloc[idx] >= position["tp_price"]:
                        print(f"Long TP closed at index: {idx}")
                        self.close_position(position, position["tp_price"])
                        break
                    if df['Low'].iloc[idx] <= position["sl_price"]:
                        print(f"Long SL closed at index: {idx}")
                        self.close_position(position, position["sl_price"])
                        break
            elif position["direction"] == "SHORT":
                for idx in range(position["candle_index"], len(df)):
                    if df['Low'].iloc[idx] <= position["tp_price"]:
                        print(f"Short TP closed at index: {idx}")
                        self.close_position(position, position["tp_price"])
                        break
                    if df['High'].iloc[idx] >= position["sl_price"]:
                        print(f"Short SL closed at index: {idx}")
                        self.close_position(position, position["sl_price"])
                        break

    def report(self):
        print("---- Portfolio Report ----")
        print(f"Current Balance: ${self.balance:.2f}")
        print(f"Open Positions: {len(self.positions)}")
        print(f"Closed Positions: {len(self.closed_positions)}")
        for pos in self.closed_positions:
            print(
                f"Symbol: {pos['symbol']}, P/L: ${pos['profit_loss']:.2f}, "
                f"Direction: {pos['direction']}, Entry: {pos['entry_price']}, Exit: {pos['exit_price']}, ID: {pos['id']}, Candle Index: {pos['candle_index']}"
            )

    def find_position(self, df):
        global fibonacci_1, fibonacci_2
        percentuale_stoploss = 0.0001
        _0_75_line_price = fibonacci_1.get(0.75, None)
        _0_25_line_price =  fibonacci_1.get(-0.25, None)
        _0_5_line_price = fibonacci_1.get(0.5, None)
        _0_618_line_price = fibonacci_2.get(0.618, None)

        if len(global_vars.checked_pivots) < 5:
            return
    
        i2 = global_vars.checked_pivots[-3]  
        i4 = global_vars.checked_pivots[-5]  
        i3 = global_vars.checked_pivots[-4]  
        i1 = global_vars.checked_pivots[-2] 

        long_conditions = (
            _0_75_line_price < _0_5_line_price and
            _0_618_line_price > df['Low'].iloc[i2] and
            df['Low'].iloc[i2] > df['Low'].iloc[i4] and
            df['Close'].iloc[i1] > df['High'].iloc[i3]
        )
        
        short_conditions = (
            _0_75_line_price > _0_5_line_price and
            _0_618_line_price < df['High'].iloc[i2] and
            df['High'].iloc[i2] < df['High'].iloc[i4] and
            df['Close'].iloc[i1] < df['Low'].iloc[i3]
        )
        
        current_alert = {
            "type": "LONG" if long_conditions else "SHORT" if short_conditions else None,
            "symbol": global_vars.chart.topbar['symbol'].value,
            "0.618": _0_618_line_price,
            "0.75": _0_75_line_price,
            "i2": df['Low'].iloc[i2] if long_conditions else df['High'].iloc[i2],
            "i4": df['Low'].iloc[i4] if long_conditions else df['High'].iloc[i4],
            "i1": df['Close'].iloc[i1],
            "i3": df['Low'].iloc[i3] if long_conditions else df['High'].iloc[i3]
        }
        
        if long_conditions and current_alert != self.last_alert:
            for idx in range(i1 + 1, len(df)):
                if df['Low'].iloc[idx] <= _0_75_line_price:
                    self.open_position(
                        symbol=current_alert["symbol"],
                        direction="LONG",
                        price=_0_75_line_price,
                        tp_price=_0_25_line_price,
                        sl_price = df['Low'].iloc[i4] - (df['Low'].iloc[i4] * percentuale_stoploss),
                        candle_index=idx
                    )
                    self.last_alert = current_alert
                    send_telegram_message(f"LONG ALERT {current_alert['symbol']} \n 0.68: {current_alert['0.618']} > i2: {current_alert['i2']} >  i4: {current_alert['i4']} \n i1: {current_alert['i1']} > i3: {current_alert['i3']} \n Entry point: {_0_75_line_price} \n Stopploss: {current_alert['i2']} \n takeprofit: {_0_25_line_price}", send_photo=True )
                    break

        if short_conditions and current_alert != self.last_alert:
            for idx in range(i1 + 1, len(df)):
                if df['High'].iloc[idx] >= _0_75_line_price:
                    self.open_position(
                        symbol=current_alert["symbol"],
                        direction="SHORT",
                        price=_0_75_line_price,
                        tp_price=_0_25_line_price,
                        sl_price = df['High'].iloc[i4] + (df['High'].iloc[i4] * percentuale_stoploss),
                        candle_index=idx
                    )
                    self.last_alert = current_alert
                    send_telegram_message(f"SHORT ALERT {current_alert['symbol']} \n 0.68: {current_alert['0.618']} < i2: {current_alert['i2']} <  i4: {current_alert['i4']} \n i1: {current_alert['i1']} < i3: {current_alert['i3']} \n Entry point: {_0_75_line_price}  \n Stopploss: {current_alert['i2']} \n takeprofit: {_0_25_line_price}", send_photo=True)
                    break

