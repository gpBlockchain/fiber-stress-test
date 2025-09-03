import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import time
import random
import logging
from src.config import FibersConfig
from src.fiber_rpc import send_payment,send_invoice_payment

LOGGER = logging.getLogger(__name__)

def run_transfer_scenario(fibers_config, transfer_config):
    duration = transfer_config.get('duration', 60)
    concurrency = transfer_config.get('user', 1)
    start_time = time.time()
    end_time = start_time + duration

    total_transactions = 0
    failed_transactions = 0
    success_transactions = 0

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = set()
        last_print_time = time.time()
        completed_count = 0
        last_completed_count = 0
        last_success_count = 0

        # Submit initial batch of tasks
        for _ in range(concurrency):
            if time.time() < end_time:
                future = submit_payment_task(executor, fibers_config, transfer_config)
                if future:
                    futures.add(future)
                    total_transactions += 1

        while futures:
            # Wait for the next future to complete
            done, _ = concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED, timeout=0.1)

            for future in done:
                completed_count += 1
                try:
                    if future.result():
                        success_transactions += 1
                    else:
                        failed_transactions += 1
                except Exception as e:
                    failed_transactions += 1
                    LOGGER.error(f"Task failed with exception: {e}")
                
                # Remove the completed future
                futures.remove(future)

                # Submit a new task if there's still time
                if time.time() < end_time:
                    new_future = submit_payment_task(executor, fibers_config, transfer_config)
                    if new_future:
                        futures.add(new_future)
                        total_transactions += 1

            if time.time() - last_print_time >= 30:
                current_time = time.time()
                elapsed_interval = current_time - last_print_time
                
                completed_in_interval = completed_count - last_completed_count
                success_in_interval = success_transactions - last_success_count
                tps = completed_in_interval / elapsed_interval if elapsed_interval > 0 else 0
                success_tps = success_in_interval / elapsed_interval if elapsed_interval > 0 else 0

                print(f"from:{transfer_config.get("from")},to:{transfer_config.get("to")} amount:{transfer_config.get("amount")} ,udt:{transfer_config.get("udt",None) !=None},users:{concurrency} Elapsed: {current_time - start_time:.2f}s/{duration}s, Total: {total_transactions}, Completed: {completed_count}, Success: {success_transactions}, Failed: {failed_transactions}, TPS: {tps:.2f}, Success TPS: {success_tps:.2f}, 30s Transactions: {completed_in_interval}, 30s Success: {success_in_interval}")
                last_print_time = current_time
                last_completed_count = completed_count
                last_success_count = success_transactions

    LOGGER.info(f"Scenario finished. Total: {total_transactions}, Success: {success_transactions}, Failed: {failed_transactions}")

def send_transactions(config):
    LOGGER.info("--- Running Transaction Phase: Sending Transactions ---")
    fibers_config = FibersConfig(config)
    if 'transfer' in config:
        with ThreadPoolExecutor(max_workers=len(config['transfer'])) as scenario_executor:
            scenario_futures = [scenario_executor.submit(run_transfer_scenario, fibers_config, tc) for tc in config['transfer']]
            for future in scenario_futures:
                future.result()

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

def submit_payment_task(executor, fibers_config, transaction):
    from_spec = transaction.get('from')
    to_spec = transaction.get('to')

    # 确保发送方和接收方不是同一个节点
    while True:
        from_node_id = get_random_node_id(fibers_config, from_spec)
        to_node_id = get_random_node_id(fibers_config, to_spec)
        if from_node_id != to_node_id:
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
        return executor.submit(send_payment_by_id, fibers_config, payment_transaction)
    elif tx_type == 'invoice':
        return executor.submit(send_invoice_payment_by_id, fibers_config, payment_transaction)
    else:
        LOGGER.warning(f"Unknown transaction type {tx_type}. Skipping.")
        return None


def send_payment_by_id(fibers_config, transaction):
    from_node_id = transaction.get('from')
    to_node_id = transaction.get('to')
    amount = transaction.get('amount')
    udt = transaction.get('udt',None)

    from_rpc = fibers_config.fibersMap.get(from_node_id)
    to_rpc = fibers_config.fibersMap.get(to_node_id)

    if not from_rpc or not to_rpc:
        LOGGER.warning(f"Skipping transaction from {from_node_id} to {to_node_id} due to missing node RPC client.")
        return False
    start_time = time.time()
    try:
        send_payment(from_rpc, to_rpc, amount, wait=True, udt=udt, try_count=0)
        end_time = time.time()
        return True
    except Exception as e:
        end_time = time.time()
        LOGGER.error(f"Error sending transaction from {from_node_id} to {to_node_id} took {end_time - start_time:.4f} seconds. : {e}")
        return False

def send_invoice_payment_by_id(fibers_config, transaction):
    from_node_id = transaction.get('from')
    to_node_id = transaction.get('to')
    amount = transaction.get('amount')
    udt = transaction.get('udt',None)

    from_rpc = fibers_config.fibersMap.get(from_node_id)
    to_rpc = fibers_config.fibersMap.get(to_node_id)

    if not from_rpc or not to_rpc:
        LOGGER.warning(f"Skipping transaction from {from_node_id} to {to_node_id} due to missing node RPC client.")
        return False
    start_time = time.time()
    try:
        send_invoice_payment(from_rpc, to_rpc, amount, wait=True, udt=udt, try_count=0)
        end_time = time.time()
        return True
    except Exception as e:
        end_time = time.time()
        LOGGER.error(f"Error sending transaction from {from_node_id} to {to_node_id} took {end_time - start_time:.4f} seconds. : {e}")
        return False
