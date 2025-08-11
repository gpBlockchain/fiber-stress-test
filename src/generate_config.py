import random
import toml
from collections import defaultdict


# CORE_CAPACITY_RANGE = (1_000_000, 2_000_000)   # CKB
# RELAY_CAPACITY_RANGE = (10_000, 15_000)    # CKB
# EDGE_CAPACITY_RANGE = (10_000, 20_000)        # CKB


CORE_CAPACITY_RANGE = (3_000, 5_000)   # CKB
RELAY_CAPACITY_RANGE = (1000, 2_000)    # CKB
EDGE_CAPACITY_RANGE = (100, 500)        # CKB

# ====== 生成节点数量 ======
num_core = 20
num_relay = 40
num_edge = 240

core_nodes = [f"core_{i}" for i in range(num_core)]
relay_nodes = [f"relay_{i}" for i in range(num_relay)]
edge_nodes = [f"edge_{i}" for i in range(num_edge)]

# 存储节点连接信息
connections_map = defaultdict(list)

# ====== 核心节点：彼此高度互联 ======
for node in core_nodes:
    peer_count = random.randint(int(num_core * 0.6), int(num_core * 0.8))
    peers = random.sample([n for n in core_nodes if n != node], k=peer_count)
    for p in peers:
        capacity = random.randint(*CORE_CAPACITY_RANGE)
        connections_map[node].append((p, capacity))

# ====== 中继节点：连接核心 + 一些中继 ======
for node in relay_nodes:
    core_peers = random.sample(core_nodes, k=random.randint(2, 5))
    other_relays = [r for r in relay_nodes if r != node]
    relay_peer_count = max(1, int(len(other_relays) * random.uniform(0.1, 0.3)))
    relay_peers = random.sample(other_relays, k=relay_peer_count)
    all_peers = core_peers + relay_peers
    for p in all_peers:
        capacity = random.randint(*RELAY_CAPACITY_RANGE)
        connections_map[node].append((p, capacity))

# ====== 边缘节点：连接 1~2 个核心或中继 ======
upper_nodes = core_nodes + relay_nodes
for node in edge_nodes:
    peers = random.sample(upper_nodes, k=random.choice([1, 2]))
    for p in peers:
        capacity = random.randint(*EDGE_CAPACITY_RANGE)
        connections_map[node].append((p, capacity))

# ====== 转换为 [[connect_to]] 格式 ======
connect_to_blocks = []
for node_id, conns in connections_map.items():
    targets = [t for t, _ in conns]
    capacities = [c for _, c in conns]
    connect_to_blocks.append({
        "id": node_id,
        "targets": targets,
        "capacitys": capacities,
        "udt":'{ code_hash = "0x102583443ba6cfe5a3ac268bbb4475fb63eb497dce077f126ad3b148d4f4f8f8", hash_type = "type", args = "0x32e555f3ff8e135cece1351a6a2971518392c1e30375c1e006ad0ce8eac07947" }'
           })

# ====== 保存为 TOML 文件 ======
output_path = "fiber_topology_custom_format.toml"
with open(output_path, "w") as f:
    f.write(toml.dumps({"connect_to": connect_to_blocks}))

print(f"✅ 拓扑文件已生成: {output_path}")
print(f"核心节点: {num_core}, 中继节点: {num_relay}, 边缘节点: {num_edge}")
