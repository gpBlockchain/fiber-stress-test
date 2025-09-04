import asyncio
import aiohttp
import json
import logging
import random
import time

LOGGER = logging.getLogger(__name__)

CKB_UNIT = 100000000
CKB_CELL_RETAIN = 62 * 100000000

class AsyncFiberRPCClient:
    def __init__(self, url, other_params={}, try_count=200):
        self.url = url
        self.other_params = other_params
        self.try_count = try_count
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def call(self, method, params):
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        for i in range(self.try_count):
            try:
                data = {
                    "id": 42,
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params,
                    **self.other_params
                }
                headers = {'Content-Type': 'application/json'}
                if 'Authorization' in self.other_params:
                    headers['Authorization'] = self.other_params['Authorization']
                
                async with self.session.post(
                    self.url,
                    json=data,
                    headers=headers
                ) as response:
                    response_text = await response.text()
                    response_data = json.loads(response_text)
                    
                    if "error" in response_data:
                        error_message = response_data["error"].get("message", "Unknown error")
                        raise Exception(f"Error: {error_message}")
                    
                    return response_data.get("result", None)
            except aiohttp.ClientConnectionError as e:
                LOGGER.debug(e)
                LOGGER.debug("request too quickly, wait 2s")
                await asyncio.sleep(2)
                continue
        raise Exception("request time out")

    async def send_btc(self, btc_pay_req):
        return await self.call("send_btc", [btc_pay_req])

    async def build_router(self, param):
        return await self.call("build_router", [param])

    async def send_payment_with_router(self, param):
        return await self.call("send_payment_with_router", [param])

    async def abandon_channel(self, param):
        return await self.call("abandon_channel", [param])

    async def open_channel(self, param):
        return await self.call("open_channel", [param])

    async def list_channels(self, param):
        return await self.call("list_channels", [param])

    async def update_channel(self, param):
        return await self.call("update_channel", [param])

    async def accept_channel(self, param):
        return await self.call("accept_channel", [param])

    async def add_tlc(self, param):
        return await self.call("add_tlc", [param])

    async def remove_tlc(self, param):
        return await self.call("remove_tlc", [param])

    async def shutdown_channel(self, param):
        return await self.call("shutdown_channel", [param])

    async def new_invoice(self, param):
        return await self.call("new_invoice", [param])

    async def parse_invoice(self, param):
        return await self.call("parse_invoice", [param])

    async def connect_peer(self, param):
        return await self.call("connect_peer", [param])

    async def cancel_invoice(self, param):
        return await self.call("cancel_invoice", [param])

    async def get_invoice(self, param):
        return await self.call("get_invoice", [param])

    async def disconnect_peer(self, param):
        return await self.call("disconnect_peer", [param])

    async def send_payment(self, param):
        return await self.call("send_payment", [param])

    async def get_payment(self, param):
        return await self.call("get_payment", [param])

    async def node_info(self):
        return await self.call("node_info", [{}])

    async def graph_nodes(self, param={}):
        return await self.call("graph_nodes", [param])

    async def graph_channels(self, param={}):
        return await self.call("graph_channels", [param])

    async def list_peers(self, param={}):
        return await self.call("list_peers", [param])


async def open_channel_async(fiber1, fiber2, capacity, udt=None):
    """
    异步打开一个通道
    确认通道创建成功
    """
    fiber2_node_info = await fiber2.node_info()
    await fiber1.connect_peer({"address": fiber2_node_info["addresses"][0]})
    await asyncio.sleep(2)
    fiber2_peer_id = fiber2_node_info["addresses"][0].split("/")[-1]
    open_channel_config = {
        "peer_id": fiber2_peer_id,
        "funding_amount": hex(capacity*CKB_UNIT),
        "tlc_fee_proportional_millionths": hex(1000),
        "public": True,
        "funding_udt_type_script": udt,
    }
    try:
        await fiber1.open_channel(open_channel_config)
        await asyncio.sleep(2)
        await wait_for_channel_state_async(fiber1, fiber2_peer_id, "CHANNEL_READY", timeout=60)
    except Exception as e:
        LOGGER.error(f"open channel failed:{e}")
    try:
        await send_payment_async(fiber1, fiber2, int(capacity*CKB_UNIT/2), udt=udt)
    except Exception as e:
        LOGGER.error(f"send payment failed:{e}")


async def send_payment_async(fiber1, fiber2, amount, wait=True, udt=None, try_count=5):
    for i in range(try_count):
        try:
            node_info = await fiber2.node_info()
            payment = await fiber1.send_payment(
                {
                    "target_pubkey": node_info["node_id"],
                    "amount": hex(amount),
                    "keysend": True,
                    "allow_self_payment": True,
                    "udt_type_script": udt,
                }
            )
            if wait:
                await wait_payment_state_async(
                    fiber1, payment["payment_hash"], "Success", 600, 0.05
                )
            return payment["payment_hash"]
        except Exception as e:
            await asyncio.sleep(1)
            continue
    
    # 最后一次尝试
    node_info = await fiber2.node_info()
    payment = await fiber1.send_payment(
        {
            "target_pubkey": node_info["node_id"],
            "amount": hex(amount),
            "keysend": True,
            "allow_self_payment": True,
            "udt_type_script": udt,
        }
    )
    if wait:
        await wait_payment_state_async(
            fiber1, payment["payment_hash"], "Success", 600, 0.1
        )
    return payment["payment_hash"]


async def send_invoice_payment_async(
     fiber1, fiber2, amount, wait=True, udt=None, try_count=5
):
    invoice = await fiber2.new_invoice(
        {
            "amount": hex(amount),
            "currency": "Fibt",
            "description": "test invoice generated by node2",
            "payment_preimage": generate_random_preimage(),
            "hash_algorithm": "sha256",
            "udt_type_script": udt,
            "allow_mpp": True,
        }
    )
    for i in range(try_count):
        try:
            payment = await fiber1.send_payment(
                {
                    "invoice": invoice["invoice_address"],
                    "allow_self_payment": True,
                    "max_parts": "0x40",
                }
            )
            if wait:
                await wait_payment_state_async(fiber1, payment["payment_hash"], "Success")
            return payment["payment_hash"]
        except Exception as e:
            await asyncio.sleep(1)
            continue
    
    # 最后一次尝试
    payment = await fiber1.send_payment(
        {
            "invoice": invoice["invoice_address"],
            "allow_self_payment": True,
            "max_parts": "0x40",
        }
    )
    if wait:
        await wait_payment_state_async(fiber1, payment["payment_hash"], "Success")
    return payment["payment_hash"]


async def wait_payment_state_async(
     client, payment_hash, status="Success", timeout=360, interval=0.1
):
    for i in range(timeout):
        result = await client.get_payment({"payment_hash": payment_hash})
        if result["status"] == status:
            return
        if result['status'] == 'Success' or result['status'] == 'Failed':
            break
        await asyncio.sleep(interval)
    raise TimeoutError(
        f"Payment {payment_hash} did not reach status {status} within {timeout} seconds"
    )


async def wait_for_channel_state_async(
    client, peer_id, status="CHANNEL_READY", timeout=360, interval=1
):
    for i in range(timeout):
        try:
            channels = await client.list_channels({"peer_id": peer_id})
            for channel in channels["channels"]:
                if channel["peer_id"] == peer_id:
                    if channel["state"]["state_name"] == status:
                        return
        except Exception as e:
            LOGGER.debug(f"Error checking channel state: {e}")
        await asyncio.sleep(interval)
    raise TimeoutError(
        f"Channel with peer {peer_id} did not reach status {status} within {timeout} seconds"
    )


def generate_random_preimage():
    """
    生成一个随机的32字节preimage
    """
    return "0x" + "".join([f"{random.randint(0, 255):02x}" for _ in range(32)])