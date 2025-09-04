import asyncio
from src.fiber_rpc_async import AsyncFiberRPCClient

class AsyncFibersConfig:
    def __init__(self, config: dict[str, any]):
        self.config = config
        self.fibersMap = {}
        self.typeCount = {}
        # 将 config 中的 fibers 信息转换为 fibersMap
        for fiber in config['fibers']:
            fiber_type = fiber['type']
            for i in range(len(fiber['urls'])):
                fiber_id = f"{fiber_type}_{i}"
                self.fibersMap[fiber_id] = AsyncFiberRPCClient(
                    fiber['urls'][i], 
                    other_params=config.get('fiber_rpc', {})
                )
            self.typeCount[fiber_type] = len(fiber['urls'])
    
    async def close_all_sessions(self):
        """关闭所有 RPC 客户端的会话"""
        close_tasks = []
        for client in self.fibersMap.values():
            if client.session:
                close_tasks.append(client.session.close())
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)