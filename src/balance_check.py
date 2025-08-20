from src.config import FibersConfig
from src.fiber_rpc import send_payment
import time 
# 
# [[balance_check]]
# from = "edge1"
# to = "edge2"
# amount = 1000
# batch = 5  # 发送5笔后，检查结果
# duration = 10

def balance_check(config):
    balance_check_config = config['balance_check'][0]
    fibers_config = FibersConfig(config)
    from_node = balance_check_config['from']
    to_node = balance_check_config['to']
    amount = balance_check_config['amount']
    batch = balance_check_config['batch']
    duration = balance_check_config['duration']
    udt = balance_check_config.get('udt', None)
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
            from_before_balance = get_balance(from_fiber)
            to_before_balance = get_balance(to_fiber)
        except Exception as e:
            print(f"get balance failed, {e}")
            continue

        for i in range(batch):
            try:
                payment_hash = send_payment(from_fiber, to_fiber, amount, wait=False, udt=udt, try_count=0)
                payment_hashs.append(payment_hash)
            except Exception as e:
                print(f"send payment failed, {e}")
        
        # 检查交易是否成功
        transfer_amoount = 0
        fee_amount = 0
        for payment_hash in payment_hashs:
            # wait payment finised 
            # todo 超时怎么办
            payment= wait_payment_finished(from_fiber, payment_hash)
            print(f"payment: {payment}")
            if payment["status"] == "Success":
                transfer_amoount += amount
                fee_amount += int(payment["fee"], 16)

        # 检查余额是否正确
        try:
            from_after_balance = get_balance(from_fiber)
            to_after_balance = get_balance(to_fiber)
        except Exception as e:
            print(f"get balance failed, {e}")
            continue
        print(f"from_before_balance: {from_before_balance},to_before_balance: {to_before_balance} ,transfer:{transfer_amoount},fee:{fee_amount}")
        print(f"from_after_balance: {from_after_balance},to_after_balance: {to_after_balance}")
        # check blance 
        if udt is None:
            assert from_after_balance["ckb"]["local_balance"] == from_before_balance["ckb"]["local_balance"] - transfer_amoount - fee_amount
            assert to_after_balance["ckb"]["local_balance"] == to_before_balance["ckb"]["local_balance"] + transfer_amoount
        else:
            assert from_after_balance[udt['args']]["local_balance"] == from_before_balance[udt['args']]["local_balance"] - transfer_amoount - fee_amount
            assert to_after_balance[udt['args']]["local_balance"] == to_before_balance[udt['args']]["local_balance"] + transfer_amoount
        # 等待一段时间
        time.sleep(1)
        check_count += 1
        print(f"check idx: {check_count},cost time: {time.time() - current_time},transfer:{transfer_amoount},fee:{fee_amount}")



def wait_payment_finished(fiber_rpc, payment_hash, timeout=120):
        for i in range(timeout):
            result = fiber_rpc.get_payment({"payment_hash": payment_hash})
            if result["status"] == "Success" or result["status"] == "Failed":
                return result
            time.sleep(1)
        raise TimeoutError(
            f"status did not reach state {expected_state} within timeout period."
        )


def get_balance(fiber_rpc):
    channels = fiber_rpc.list_channels({})
    balance_map = {}
    for i in range(len(channels["channels"])):
        channel = channels["channels"][i]
        if channel["state"]["state_name"] == "CHANNEL_READY":
            key = "ckb"
            if channel["funding_udt_type_script"] is not None:
                key = channel["funding_udt_type_script"]["args"]
            if balance_map.get(key) is None:
                balance_map[key] = {
                    "local_balance": 0,
                    "offered_tlc_balance": 0,
                    "received_tlc_balance": 0,
                }
            balance_map[key]["local_balance"] += int(channel["local_balance"], 16)
            balance_map[key]["offered_tlc_balance"] += int(
                channel["offered_tlc_balance"], 16
            )
            balance_map[key]["received_tlc_balance"] += int(
                channel["received_tlc_balance"], 16
            )
    return balance_map
