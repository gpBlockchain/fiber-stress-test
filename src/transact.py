from concurrent.futures import ThreadPoolExecutor
import time
import random
from src.config import FibersConfig
from src.preparation import send_payment
def run_transfer_scenario(fibers_config, transfer_config):
    duration = transfer_config.get('duration', 60)
    concurrency = transfer_config.get('user', 1)
    start_time = time.time()
    end_time = start_time + duration

    total_transactions = 0
    failed_transactions = 0

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        last_print_time = time.time()

        while time.time() < end_time:
            future = submit_payment_task(executor, fibers_config, transfer_config)
            if future:
                futures.append(future)
                total_transactions += 1
            time.sleep(0.1)

            if time.time() - last_print_time >= 5:
                completed_count = sum(1 for f in futures if f.done())
                failed_count = sum(1 for f in futures if f.done() and f.result() is False)
                print(f"Elapsed: {time.time() - start_time:.2f}s, Total: {total_transactions}, Completed: {completed_count}, Failed: {failed_count}")
                last_print_time = time.time()

        for future in futures:
            if not future.result():
                failed_transactions += 1
    
    print(f"Scenario finished. Total: {total_transactions}, Failed: {failed_transactions}")

def send_transactions(config):
    print("--- Running Transaction Phase: Sending Transactions ---")
    fibers_config = FibersConfig(config)
    if 'transfer' in config:
        with ThreadPoolExecutor(max_workers=len(config['transfer'])) as scenario_executor:
            scenario_futures = [scenario_executor.submit(run_transfer_scenario, fibers_config, tc) for tc in config['transfer']]
            for future in scenario_futures:
                future.result()

    print("--- Transaction Phase Complete ---")

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

    from_node_id = get_random_node_id(fibers_config, from_spec)
    to_node_id = get_random_node_id(fibers_config, to_spec)

    if not from_node_id or not to_node_id:
        print(f"Could not resolve nodes for transaction from {from_spec} to {to_spec}. Skipping.")
        return None

    # Create a new transaction object for the specific payment
    payment_transaction = transaction.copy()
    payment_transaction['from'] = from_node_id
    payment_transaction['to'] = to_node_id

    return executor.submit(send_payment_by_id, fibers_config, payment_transaction)

def send_payment_by_id(fibers_config, transaction):
    from_node_id = transaction.get('from')
    to_node_id = transaction.get('to')
    amount = transaction.get('amount')

    from_rpc = fibers_config.fibersMap.get(from_node_id)
    to_rpc = fibers_config.fibersMap.get(to_node_id)

    if not from_rpc or not to_rpc:
        print(f"Skipping transaction from {from_node_id} to {to_node_id} due to missing node RPC client.")
        return False
    try:
        print(f"Sending {amount} from {from_node_id} to {to_node_id}")
        # send_payment_by_rpc(from_rpc, to_rpc, amount)
        # def send_payment(fiber1, fiber2, amount, wait=True, udt=None, try_count=5):
        send_payment(from_rpc, to_rpc, amount)
        
        return True
    except Exception as e:
        print(f"Error sending transaction from {from_node_id} to {to_node_id}: {e}")
        return False
    
# def send_payment_by_rpc(from_rpc, to_rpc, amount):
#     """
#     Simulates sending a payment from one node to another.
#     """
#     # Placeholder for actual payment logic
#     send_payment(from_rpc, to_rpc, amount)
