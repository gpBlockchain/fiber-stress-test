import argparse
import toml
import logging
import asyncio

from src.preparation import connect_nodes, check_connect
from src.transact import send_transactions
from src.cleanup import shutdown_nodes,force_shutdown
from src.check_balance import check_balance
from src.change_config import change_config
from src.health_check import health_check
from src.info import info
from src.connect_nodes import connect_channel_nodes
from src.balance_check import balance_check
from src.balance_check_async import balance_check_async
from src.shutdown_check import shutdown_check
from src.graph_channel_info import graph_channels_info
from src.blance_channel import balance_channels
from src.blance_channel_async import balance_channels_async
from src.check_shutdown_msg import check_shutdown_msg


def main():
    """主函数入口"""
    # 配置日志格式，包含时间戳
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    parser = argparse.ArgumentParser(description="Fiber Stress Test Tool")
    parser.add_argument('config', help='Path to the configuration file.')
    parser.add_argument('command', choices=['connect_to', 'transfer', 'shutdown','force_shutdown', 'check_connect', 'check_balance', 'change_config', 'info', 'health_check','connect_channel_nodes','balance_check','shutdown_check','graph_channels_info','balance_channels','check_shutdown_msg'], help='The command to execute.')

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
        asyncio.run(send_transactions(config))
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
    elif args.command == 'balance_check_async':
        asyncio.run(balance_check_async(config))
    elif args.command == 'shutdown_check':
        shutdown_check(config)
    elif args.command == 'force_shutdown':
        force_shutdown(config)
    elif args.command == 'graph_channels_info':
        graph_channels_info(config)
    elif args.command == 'balance_channels':
        balance_channels(config)
    elif args.command == 'balance_channels_async':
        asyncio.run(balance_channels_async(config))
    elif args.command == 'check_shutdown_msg':
        check_shutdown_msg(config)


if __name__ == '__main__':
    main()