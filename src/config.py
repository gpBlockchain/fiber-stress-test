
import threading

from src.fiber_rpc import FiberRPCClient

### ckb 单位定义
CKB_UNIT = 100000000

CKB_CELL_RETAIN = 62 * 100000000

class FibersConfig:
    def __init__(self, config: dict[str, any]):
        self.config = config
        self.fibersMap = {}
        self.fiber_locks = {}
        self.typeCount = {}
        # self.ckbClient = CkbClient(config['ckb']['url'])
        # 将 config 中的 fibers 信息转换为 fibersMap
        for fiber in config['fibers']:
            fiber_type = fiber['type']
            for i in range(len(fiber['urls'])):
                fiber_id = f"{fiber_type}_{i}"
                self.fibersMap[fiber_id] = FiberRPCClient(fiber['urls'][i])
                self.fiber_locks[fiber_id] = threading.Lock()
            self.typeCount[fiber_type] = len(fiber['urls'])