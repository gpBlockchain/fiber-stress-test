from src.config import FibersConfig

def connect_channel_nodes(config):
    fibers_config = FibersConfig(config)
    # map[pubkey] = address
    pubkey_map = {}
    for key in fibers_config.fibersMap.keys():
        try:
            node_info = fibers_config.fibersMap[key].node_info()
            pubkey_map[node_info["pubkey"]] = node_info['addresses'][0]
            print(f"cur id:{key} url:{fibers_config.fibersMap[key].url} pubkey:{node_info['pubkey']}")
        except Exception as e:
            print(f"cur id:{key},url:{fibers_config.fibersMap[key].url} failed:",e)
    for key in fibers_config.fibersMap.keys():
        fiber = fibers_config.fibersMap[key]
        try:
            channels = fiber.list_channels({})
            list_peers = fiber.list_peers()
            # linked 
            pubkey_set = set()
            for channel in channels['channels']:
                pubkey_set.add(channel['pubkey'])
            print(f"connect {key} channels:{len(channels['channels'])},pubkey_set:{len(pubkey_set)},list_peers:{len(list_peers['peers'])}")

            peers = []
            for peer in list_peers['peers']:
                peers.append(peer['pubkey'])
            for channel in channels['channels']:
                if channel['state']['state_name'] == 'CHANNEL_READY':
                    pubkey = channel['pubkey']
                    if pubkey not in peers:
                        print(f"connect {key} not found {pubkey}")
                        if pubkey_map.get(pubkey) == None:
                            print(f"connect {key} not found {pubkey} in pubkey_map")
                            continue
                        fiber.connect_peer({
                            'address':pubkey_map[pubkey],
                        })
                        print(f"connect {key} to {pubkey} success")
        except Exception as e:
            print(f"connect {key} failed:",e)