import argparse
import toml

from src.preparation import connect_nodes, check_connect
from src.transact import send_transactions
from src.cleanup import shutdown_nodes,force_shutdown
from src.check_balance import check_balance
from src.change_config import change_config
from src.health_check import health_check
from src.info import info
from src.connect_nodes import connect_channel_nodes
from src.balance_check import balance_check
from src.shutdown_check import shutdown_check
from src.graph_channel_info import graph_channels_info
from src.blance_channel import balance_channels


def main():
    """主函数入口"""
    parser = argparse.ArgumentParser(description="Fiber Stress Test Tool")
    parser.add_argument('config', help='Path to the configuration file.')
    parser.add_argument('command', choices=['connect_to', 'transfer', 'shutdown','force_shutdown', 'check_connect', 'check_balance', 'change_config', 'info', 'health_check','connect_channel_nodes','balance_check','shutdown_check','graph_channels_info','balance_channels'], help='The command to execute.')

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
    elif args.command == 'connect_channel_nodes':
        connect_channel_nodes(config)
    elif args.command == 'balance_check':
        balance_check(config)
    elif args.command == 'shutdown_check':
        shutdown_check(config)
    elif args.command == 'force_shutdown':
        force_shutdown(config)
    elif args.command == 'graph_channels_info':
        graph_channels_info(config)
    elif args.command == 'balance_channels':
        balance_channels(config)


if __name__ == '__main__':
    main()