from src.config import FibersConfig
from src.fiber_rpc import CKB_UNIT
from src.fiber_rpc import wait_payment_state

def health_check(config):
    fibers_config = FibersConfig(config)
    # 定时 检查
    while True:
        print("--- Running Health Check ---")
        msgs = {}
        for key in list(fibers_config.fibersMap.keys()):
        # fiber list channel 
            msgs[key] = {"channel_size":0,"peer_size":0,"payment_failed_size":0,"payment_success_size":0,"not_found_peer_id":[],"payment_err":[],"url":fibers_config.fibersMap[key].url}
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
                # 从 peer id 获取 pubkey
                try:
                    pubkey = None
                    peer_id = channel["peer_id"]
                    for peer in peers_info["peers"]:
                        if peer["peer_id"] == peer_id:
                            pubkey = peer["pubkey"]
                            break
                    # 如果没找到pubkey 报错

                    if pubkey == None:
                        msgs[key]["not_found_peer_id"].append(peer_id)
                        raise Exception("peer id not found pubkey:",peer_id)
                    # 如果local balance <1 ckb 就算了
                    if int(channel['local_balance'],16) < 1 * CKB_UNIT:
                        continue
                    # send payment 
                    payment = fibers_config.fibersMap[key].send_payment({
                        "target_pubkey": pubkey,
                        "amount": hex(1) ,
                        "keysend":True,
                        "udt_type_script": channel['funding_udt_type_script'],
                    })
                    wait_payment_state(fibers_config.fibersMap[key], payment["payment_hash"], "Success",timeout=15, interval=1)
                    print(f"cur id:{key} channel id:{channel['channel_id']}remote id:{channel["peer_id"]} payment:{payment["payment_hash"]} success")
                    msgs[key]["payment_success_size"] += 1
                    # 打印一些日志
                except Exception as e:
                    print(f"cur id:{key} channel id:{channel['channel_id']}remote id:{channel["peer_id"]} payment failed:",e)
                    msgs[key]["payment_err"].append(f"channel id:{channel['channel_id']}remote id:{channel["peer_id"]} payment failed:{e}")
                    msgs[key]["payment_failed_size"] += 1
        print("===============================检查结果===============================")
        for key in msgs.keys():
            print(msgs[key])
        print("===============================检查结果 ERROR :===============================")
        for key in msgs.keys():
            if "err" in msgs[key].keys():
                print(f"ERROR: cur id:{key},url:{msgs[key]["url"]} list channel failed:",msgs[key]["err"])
            if len(msgs[key]["not_found_peer_id"]) > 0:
                print(f"ERROR: cur id:{key},url:{msgs[key]["url"]} not found peer id:",msgs[key]["not_found_peer_id"])
            if msgs[key]["payment_failed_size"] > 0:
                print(f"ERROR: cur id:{key},url:{msgs[key]["url"]} payment failed size:{msgs[key]["payment_failed_size"]} err:",msgs[key]["payment_err"])
        print("===============================检查结果 END ===============================")
