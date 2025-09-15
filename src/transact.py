import asyncio
import time
import random
import logging
from src.config_async import AsyncFibersConfig
from src.fiber_rpc_async import send_payment_async, send_invoice_payment_async

LOGGER = logging.getLogger(__name__)

async def run_transfer_scenario(fibers_config, transfer_config):
    duration = transfer_config.get('duration', 60)
    concurrency = transfer_config.get('user', 1)
    start_time = time.time()
    end_time = start_time + duration

    total_transactions = 0
    failed_transactions = 0
    success_transactions = 0

    tasks = set()
    last_print_time = time.time()
    completed_count = 0
    last_completed_count = 0
    last_success_count = 0

    # Submit initial batch of tasks
    for _ in range(concurrency):
        if time.time() < end_time:
            task = await submit_payment_task(fibers_config, transfer_config)
            if task:
                tasks.add(task)
                total_transactions += 1

    while tasks:
        # Wait for the next task to complete
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED, timeout=0.1)

        for task in done:
            completed_count += 1
            try:
                result = await task
                if result:
                    success_transactions += 1
                else:
                    failed_transactions += 1
            except Exception as e:
                failed_transactions += 1
                LOGGER.error(f"Task failed with exception: {e}")
            
            # Remove the completed task
            tasks.remove(task)

            # Submit a new task if there's still time
            if time.time() < end_time:
                new_task = await submit_payment_task(fibers_config, transfer_config)
                if new_task:
                    tasks.add(new_task)
                    total_transactions += 1

        if time.time() - last_print_time >= 10:
            current_time = time.time()
            elapsed_interval = current_time - last_print_time
            
            completed_in_interval = completed_count - last_completed_count
            success_in_interval = success_transactions - last_success_count
            tps = completed_in_interval / elapsed_interval if elapsed_interval > 0 else 0
            success_tps = success_in_interval / elapsed_interval if elapsed_interval > 0 else 0

            LOGGER.info(f"from:{transfer_config.get('from')},to:{transfer_config.get('to')} amount:{transfer_config.get('amount')} ,udt:{transfer_config.get('udt',None) !=None},users:{concurrency} Elapsed: {current_time - start_time:.2f}s/{duration}s, Total: {total_transactions}, Completed: {completed_count}, Success: {success_transactions}, Failed: {failed_transactions}, TPS: {tps:.2f}, Success TPS: {success_tps:.2f}, 10s Transactions: {completed_in_interval}, 10s Success: {success_in_interval}")
            last_print_time = current_time
            last_completed_count = completed_count
            last_success_count = success_transactions

    LOGGER.info(f"Scenario finished. Total: {total_transactions}, Success: {success_transactions}, Failed: {failed_transactions}")

async def send_transactions(config):
    LOGGER.info("--- Running Transaction Phase: Sending Transactions ---")
    fibers_config = AsyncFibersConfig(config)
    try:
        if 'transfer' in config:
            tasks = [run_transfer_scenario(fibers_config, tc) for tc in config['transfer']]
            await asyncio.gather(*tasks)
    finally:
        # 确保关闭所有会话
        await fibers_config.close_all_sessions()

    LOGGER.info("--- Transaction Phase Complete ---")

def get_random_node_id(fibers_config, node_specifier):
    if node_specifier in fibers_config.fibersMap.keys():
        return node_specifier
    elif node_specifier in fibers_config.typeCount.keys():
        node_type = node_specifier
        num_nodes = fibers_config.typeCount[node_type]
        node_index = random.randint(0, num_nodes - 1)
        return f"{node_type}_{node_index}"
    return None

async def submit_payment_task(fibers_config, transaction):
    from_spec = transaction.get('from')
    to_spec = transaction.get('to')
    udt = transaction.get('udt',None)

    # 确保发送方和接收方不是同一个节点
    while True:
        from_node_id = get_random_node_id(fibers_config, from_spec)
        # get ckb and udt channels len
        ckb_channels = 0
        udt_channels = 0
        from_channels = await fibers_config.fibersMap[from_node_id].list_channels({})
        for channel in from_channels['channels']:
            if channel['funding_udt_type_script'] == None:
                ckb_channels += 1
            else:
                udt_channels += 1
        if udt==None and ckb_channels != 0:
            break
        elif udt!=None and udt_channels != 0:
            break
    while True:
        to_node_id = get_random_node_id(fibers_config, to_spec)
        if from_node_id == to_node_id:
            continue
        # get ckb and udt channels len
        ckb_channels = 0
        udt_channels = 0
        to_channels = await fibers_config.fibersMap[to_node_id].list_channels({})
        
        for channel in to_channels['channels']:
            if channel['funding_udt_type_script'] == None:
                ckb_channels += 1
            else:
                udt_channels += 1
        if udt==None and ckb_channels != 0:
            break
        elif udt!=None and udt_channels != 0:
            break
    if not from_node_id or not to_node_id:
        LOGGER.warning(f"Could not resolve nodes for transaction from {from_spec} to {to_spec}. Skipping.")
        return None

    # Create a new transaction object for the specific payment
    payment_transaction = transaction.copy()
    payment_transaction['from'] = from_node_id
    payment_transaction['to'] = to_node_id
    tx_type = transaction.get('type','payment')
    if tx_type == 'payment':
        return asyncio.create_task(send_payment_by_id(fibers_config, payment_transaction))
    elif tx_type == 'invoice':
        return asyncio.create_task(send_invoice_payment_by_id(fibers_config, payment_transaction))
    else:
        LOGGER.warning(f"Unknown transaction type {tx_type}. Skipping.")
        return None


async def send_payment_by_id(fibers_config, transaction):
    from_node_id = transaction.get('from')
    to_node_id = transaction.get('to')
    amount = transaction.get('amount')
    udt = transaction.get('udt',None)
    LOGGER.debug(f"send payment from {from_node_id} to {to_node_id} amount {amount} udt {udt}")
    from_rpc = fibers_config.fibersMap.get(from_node_id)
    to_rpc = fibers_config.fibersMap.get(to_node_id)

    if not from_rpc or not to_rpc:
        LOGGER.warning(f"Skipping transaction from {from_node_id} to {to_node_id} due to missing node RPC client.")
        return False
    start_time = time.time()
    try:
        # 直接调用异步函数
        await send_payment_async(from_rpc, to_rpc, amount, wait=True, udt=udt, try_count=0)
        end_time = time.time()
        LOGGER.debug(f"Success sending transaction from {from_node_id} to {to_node_id} took {end_time - start_time:.4f} seconds.")
        return True
    except Exception as e:
        end_time = time.time()
        LOGGER.error(f"Error sending transaction from {from_node_id} to {to_node_id} took {end_time - start_time:.4f} seconds. : {e}")
        return False

async def send_invoice_payment_by_id(fibers_config, transaction):
    from_node_id = transaction.get('from')
    to_node_id = transaction.get('to')
    amount = transaction.get('amount')
    udt = transaction.get('udt',None)
    LOGGER.debug(f"send invoice payment from {from_node_id} to {to_node_id} amount {amount} udt {udt}")
    from_rpc = fibers_config.fibersMap.get(from_node_id)
    to_rpc = fibers_config.fibersMap.get(to_node_id)

    if not from_rpc or not to_rpc:
        LOGGER.warning(f"Skipping transaction from {from_node_id} to {to_node_id} due to missing node RPC client.")
        return False
    start_time = time.time()
    try:
        # 直接调用异步函数
        await send_invoice_payment_async(from_rpc, to_rpc, amount, wait=True, udt=udt, try_count=0)
        end_time = time.time()
        LOGGER.debug(f"Success sending invoice payment from {from_node_id} to {to_node_id} took {end_time - start_time:.4f} seconds.")
        return True
    except Exception as e:
        end_time = time.time()
        LOGGER.error(f"Error sending transaction from {from_node_id} to {to_node_id} took {end_time - start_time:.4f} seconds. : {e}")
        return False
