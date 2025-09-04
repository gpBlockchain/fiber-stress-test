import asyncio
import logging
from src.config_async import AsyncFibersConfig
from src.fiber_rpc_async import wait_payment_state_async

LOGGER = logging.getLogger(__name__)

async def balance_channels_async(config):
    # 查询channels 
    fibers_config = AsyncFibersConfig(config)
    try:
        for key in fibers_config.fibersMap.keys():
            LOGGER.info(f"current key:{key}")
            fiber = fibers_config.fibersMap[key]
            try:
                list_peers = await fiber.list_peers()
                chanels = await fiber.list_channels({})
            except Exception as e:
                LOGGER.error(f"key:{key} list channels failed: {e}")
                continue
            
            for channel in chanels['channels']:
                if channel['remote_balance'] == "0x0":
                    LOGGER.info(f"key:{key} channel id:{channel['channel_id']}")
                    peer_id = channel['peer_id']
                    pubkey = None
                    for peer in list_peers['peers']:
                        if peer['peer_id'] == peer_id:
                            pubkey = peer['pubkey']
                            break
                    
                    if pubkey is None:
                        LOGGER.error(f"Error: key:{key} channel id:{channel['channel_id']} - peer_id {peer_id} not found in peers list")
                        continue
                    
                    try:
                        payment = await fiber.send_payment({
                            "target_pubkey": pubkey,
                            "amount": hex(int(int(channel['local_balance'], 16)/2)),
                            "keysend": True,
                            "udt_type_script": channel['funding_udt_type_script'],
                        })
                        
                        # 等待支付完成
                        await wait_payment_state_async(
                            fiber, 
                            payment['payment_hash'], 
                            "Success", 
                            timeout=120
                        )
                        LOGGER.info(f"Successfully balanced channel {channel['channel_id']}")
                        
                    except Exception as e:
                        LOGGER.error(f"Error balancing channel {channel['channel_id']}: {e}")
                        continue
    
    finally:
        # 确保关闭所有会话
        await fibers_config.close_all_sessions()