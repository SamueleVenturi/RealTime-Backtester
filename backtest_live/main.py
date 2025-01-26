from visualizer import plot_chart
from data_manager import get_all_crypto_symbols
import global_vars

def main():
    global_vars.crypto_symbols = get_all_crypto_symbols()
    plot_chart()

if __name__ == "__main__":
    main()


