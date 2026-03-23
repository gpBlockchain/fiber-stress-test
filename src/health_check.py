from src.config import FibersConfig
from src.fiber_rpc import CKB_UNIT
from src.fiber_rpc import wait_payment_state
import time 
def health_check(config):
    fibers_config = FibersConfig(config)
    # 定时 检查
    # skip check node 
    skip_check_node = []
    skip_check_pubkeys = []
    for key in list(fibers_config.fibersMap.keys()):
        if key.startswith("check"):
            skip_check_node.append(key)
            skip_check_pubkeys.append(fibers_config.fibersMap[key].node_info()['pubkey']) 
    while True:
        print("--- Running Health Check ---")
        msgs = {}
        for key in list(fibers_config.fibersMap.keys()):
        # fiber list channel 
            if key in skip_check_node:
                continue
            msgs[key] = {"channel_size":0,"peer_size":0,"payment_failed_size":0,"payment_success_size":0,"not_found_pubkey":[],"payment_err":[],"url":fibers_config.fibersMap[key].url}
            try:
                channel =  fibers_config.fibersMap[key].list_channels({})
                peers_info = fibers_config.fibersMap[key].list_peers()
                msgs[key]["channel_size"] = len(channel["channels"])
                msgs[key]["peer_size"] = len(peers_info["peers"])
            except Exception as e:
                print(f"cur id:{key} list channel failed:",e)
                msgs[key]["err"] = e
                continue
            for channel in channel["channels"]:
                try:
                    pubkey = channel["pubkey"]
                    if pubkey in skip_check_pubkeys:
                        continue
                    # 如果local balance <1 ckb 就算了
                    if int(channel['local_balance'],16) < 1 * CKB_UNIT:
                        continue
                    # send payment 
                    begin_time = time.time()
                    payment = fibers_config.fibersMap[key].send_payment({
                        "target_pubkey": pubkey,
                        "amount": hex(1) ,
                        "keysend":True,
                        "udt_type_script": channel['funding_udt_type_script'],
                    })
                    wait_payment_state(fibers_config.fibersMap[key], payment["payment_hash"], "Success",timeout=150, interval=0.1)
                    end_time = time.time()
                    print(f"cur id:{key} channel id:{channel['channel_id']}remote pubkey:{channel['pubkey']} payment:{payment['payment_hash']},fee:{payment['fee']} success cost time:{end_time-begin_time}")
                    msgs[key]["payment_success_size"] += 1
                    # 打印一些日志
                except Exception as e:
                    print(f"cur id:{key} channel id:{channel['channel_id']}remote pubkey:{channel['pubkey']} payment failed:",e)
                    msgs[key]["payment_err"].append(f"channel id:{channel['channel_id']}remote pubkey:{channel['pubkey']} payment failed:{e}")
                    msgs[key]["payment_failed_size"] += 1
        print("===============================检查结果===============================")
        for key in msgs.keys():
            print(msgs[key])
        print("===============================检查结果 ERROR :===============================")
        for key in msgs.keys():
            if "err" in msgs[key].keys():
                print(f"ERROR: cur id:{key},url:{msgs[key]['url']} list channel failed:",msgs[key]["err"])
            if len(msgs[key]["not_found_pubkey"]) > 0:
                print(f"ERROR: cur id:{key},url:{msgs[key]['url']} not found pubkey:",msgs[key]["not_found_pubkey"])
            if msgs[key]["payment_failed_size"] > 0:
                print(f"ERROR: cur id:{key},url:{msgs[key]['url']} payment failed size:{msgs[key]['payment_failed_size']} err:",msgs[key]["payment_err"])
        print("===============================检查结果 END ===============================")
