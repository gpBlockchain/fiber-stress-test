import asyncio
import time
import logging
from src.config_async import AsyncFibersConfig
from src.fiber_rpc_async import send_payment_async

LOGGER = logging.getLogger(__name__)

async def balance_check_async(config):
    balance_check_config = config['balance_check'][0]
    fibers_config = AsyncFibersConfig(config)
    from_node = balance_check_config['from']
    to_node = balance_check_config['to']
    amount = balance_check_config['amount']
    batch = balance_check_config['batch']
    duration = balance_check_config['duration']
    udt = balance_check_config.get('udt', None)
    
    try:
        # 检查from_node和to_node是否在fibers_config.fibersMap中
        if from_node not in fibers_config.fibersMap:
            raise Exception(f"from_node {from_node} not exist")
        if to_node not in fibers_config.fibersMap:
            raise Exception(f"to_node {to_node} not exist")
        
        from_fiber = fibers_config.fibersMap[from_node]
        to_fiber = fibers_config.fibersMap[to_node]
        begin_time = time.time()
        end_time = begin_time + duration
        check_count = 0
        
        while time.time() < end_time:
            # 发送一笔交易
            current_time = time.time()
            payment_hashs = []
            try:
                from_before_balance = await get_balance_async(from_fiber)
                to_before_balance = await get_balance_async(to_fiber)
            except Exception as e:
                LOGGER.error(f"get balance failed, {e}")
                continue

            for i in range(batch):
                try:
                    payment_hash = await send_payment_async(from_fiber, to_fiber, amount, wait=False, udt=udt, try_count=0)
                    payment_hashs.append(payment_hash)
                except Exception as e:
                    LOGGER.error(f"send payment failed, {e}")
                    continue
            
            # 等待所有支付完成
            for payment_hash in payment_hashs:
                try:
                    await wait_payment_finished_async(from_fiber, payment_hash, timeout=120)
                except Exception as e:
                    LOGGER.error(f"wait payment finished failed, {e}")
                    continue
            
            try:
                from_after_balance = await get_balance_async(from_fiber)
                to_after_balance = await get_balance_async(to_fiber)
            except Exception as e:
                LOGGER.error(f"get balance failed, {e}")
                continue
            
            from_balance_change = from_before_balance - from_after_balance
            to_balance_change = to_after_balance - to_before_balance
            
            check_count += 1
            LOGGER.info(f"check_count: {check_count}, from_balance_change: {from_balance_change}, to_balance_change: {to_balance_change}, batch: {batch}, amount: {amount}")
            
            if from_balance_change != to_balance_change:
                LOGGER.error(f"balance check failed, from_balance_change: {from_balance_change}, to_balance_change: {to_balance_change}")
            else:
                LOGGER.info(f"balance check success, from_balance_change: {from_balance_change}, to_balance_change: {to_balance_change}")
            
            # 等待一段时间再进行下一次检查
            await asyncio.sleep(1)
    
    finally:
        # 确保关闭所有会话
        await fibers_config.close_all_sessions()


async def wait_payment_finished_async(fiber_rpc, payment_hash, timeout=120):
    for i in range(timeout):
        try:
            result = await fiber_rpc.get_payment({"payment_hash": payment_hash})
            if result['status'] == 'Success' or result['status'] == 'Failed':
                return result
        except Exception as e:
            LOGGER.debug(f"Error checking payment status: {e}")
        await asyncio.sleep(1)
    raise TimeoutError(f"Payment {payment_hash} did not complete within {timeout} seconds")


async def get_balance_async(fiber_rpc):
    try:
        node_info = await fiber_rpc.node_info()
        return int(node_info['local_balance'], 16)
    except Exception as e:
        LOGGER.error(f"Error getting balance: {e}")
        # 如果获取余额失败，尝试通过 list_channels 获取
        try:
            channels = await fiber_rpc.list_channels({})
            total_balance = 0
            for channel in channels['channels']:
                if 'local_balance' in channel:
                    total_balance += int(channel['local_balance'], 16)
            return total_balance
        except Exception as e2:
            LOGGER.error(f"Error getting balance from channels: {e2}")
            raise e2