from src.config import FibersConfig

def connect_channel_nodes(config):
    fibers_config = FibersConfig(config)
    # map[peer_id] = fiber 
    peer_id_map = {}
    for key in fibers_config.fibersMap.keys():
        try:
            node_info = fibers_config.fibersMap[key].node_info()
            peer_id_map[node_info["addresses"][0].split("/")[-1]] = node_info['addresses'][0]
            print(f"cur id:{key} url:{fibers_config.fibersMap[key].url} peer id:{node_info["addresses"][0].split("/")[-1]}")
        except Exception as e:
            print(f"cur id:{key},url:{fibers_config.fibersMap[key].url} failed:",e)
    for key in fibers_config.fibersMap.keys():
        fiber = fibers_config.fibersMap[key]
        try:
            channels = fiber.list_channels({})
            list_peers = fiber.list_peers()
            # linked 
            peer_id_set = set()
            for channel in channels['channels']:
                peer_id_set.add(channel['peer_id'])
            print(f"connect {key} channels:{len(channels['channels'])},peer_id_set:{len(peer_id_set)},list_peers:{len(list_peers['peers'])}")

            peers = []
            for peer in list_peers['peers']:
                peers.append(peer['peer_id'])
            for channel in channels['channels']:
                if channel['state']['state_name'] == 'CHANNEL_READY':
                    peer_id = channel['peer_id']
                    if peer_id not in peers:
                        print(f"connect {key} not found {peer_id}")
                        if peer_id_map[peer_id] == None:
                            print(f"connect {key} not found {peer_id} in peer_id_map")
                            continue
                        fiber.connect_peer({
                            'address':peer_id_map[peer_id],
                        })
                        print(f"connect {key} to {peer_id} success")
        except Exception as e:
            print(f"connect {key} failed:",e)