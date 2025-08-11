import argparse
import toml

from src.preparation import connect_nodes, check_connect
from src.transact import send_transactions
from src.cleanup import shutdown_nodes
from src.check_balance import check_balance
from src.change_config import change_config
from src.health_check import health_check
from src.info import info

def main():
    """主函数入口"""
    parser = argparse.ArgumentParser(description="Fiber Stress Test Tool")
    parser.add_argument('config', help='Path to the configuration file.')
    parser.add_argument('command', choices=['connect_to', 'transfer', 'shutdown', 'check_connect', 'check_balance', 'change_config', 'info', 'health_check'], help='The command to execute.')

    args = parser.parse_args()

    try:
        with open(args.config, 'r') as f:
            config = toml.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file not found at '{args.config}'")
        return
    except Exception as e:
        print(f"Error reading or parsing configuration file: {e}")
        return

    if args.command == 'connect_to':
        connect_nodes(config)
    elif args.command == 'check_connect':
        check_connect(config)
    elif args.command == 'transfer':
        send_transactions(config)
    elif args.command == 'shutdown':
        shutdown_nodes(config)
    elif args.command == 'check_balance':
        check_balance(config)
    elif args.command == 'change_config':
        change_config(config)
    elif args.command == 'info':
        info(config)
    elif args.command == 'health_check':
        health_check(config)


if __name__ == '__main__':
    main()