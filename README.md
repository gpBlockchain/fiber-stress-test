# Fiber Stress Test

This project is a stress testing tool designed to simulate and test the performance and stability of a network of nodes, referred to as "fibers". It allows for configuring a network topology, establishing connections, running transaction loads, and cleaning up resources in a controlled manner.

## Project Structure

```
.
├── config.yml         # Main configuration file for the test scenarios.
├── main.py            # Entry point to run the stress test commands.
├── requirements.txt   # Python dependencies.
└── src/
    ├── cleanup.py       # Handles shutting down nodes.
    ├── config.py        # Configuration parsing and management.
    ├── fiber_rpc.py     # RPC client for communicating with fiber nodes.
    ├── preparation.py   # Handles node connection and channel setup.
    └── transact.py      # Handles transaction simulation.
```

## Configuration (`config.toml`)

The `config.toml` file is the core of the test setup. It uses the TOML format. Here's a breakdown of its structure:

```toml
[[fibers]]
type = "center"
urls = ["http://127.0.0.1:9000"]

[[fibers]]
type = "edge"
urls = ["http://127.0.0.1:9001", "http://127.0.0.1:9002"]


[[connect_to]]
id = "core_0"
targets = [ "core_1", "core_2","core_1","core_2"]
capacitys = [ 1955540, 1120394, 1442728, 1776792]

[[transfer]]
from = "edge"
to = "edge"
amount = 1000
user = 5
duration = 10
```

- **`[[fibers]]`**: Defines a group of nodes of the same type. The script will generate indexed names based on the `type` and the list of `urls` (e.g., `edge_0`, `edge_1`).
    - `type`: The type of the fibers (e.g., `center`,`relay`, `edge`).
    - `urls`: A list of RPC endpoint URLs for each node in this group.

- **`[[connect_to]]`**: Defines a group of channels to be opened from a single source node to multiple targets.
    - `id` (string): The identifier of the source node (e.g., `"core_0"`).
    - `targets` (array of strings): A list of target node identifiers to connect to.
    - `capacitys` (array of integers): A list of channel capacities, corresponding to each target in the `targets` list. The length must match the `targets` array.

- **`[[transfer]]`**: An array of tables, where each table defines a concurrent transaction scenario.
    - `from` (string): The source of the transactions. Can be a specific node identifier (e.g., `"edge_0"`) or a node type (e.g., `"edge"`). If a type is specified, a random node of that type will be selected for each transaction.
    - `to` (string): The destination of the transactions. Can also be a specific node identifier or a node type.
    - `amount` (integer): The amount to be sent in each individual transaction.
    - `user` (integer): The number of concurrent threads to execute this transaction scenario.
    - `duration` (integer): The total time in seconds that this scenario will run for.

## How to Run

1.  **Install Dependencies**

    ```bash
    pip install -r requirements.txt
    ```

2.  **Run Commands**

    The `main.py` script is the entry point for all operations. It requires the configuration file path and a command as arguments.

    - **Connect Nodes and Open Channels**:

      ```bash
      python main.py config.toml connect_to
      ```
      This command reads the `fibers` and `connections` sections of the config file to establish connections and open payment channels.

    - **Check Channel Status**:

      ```bash
      python main.py config.toml check_connect
      ```
      Verifies that the channels specified in the `connections` section have been successfully opened.

    - **Send Transactions**:

      ```bash
      python main.py config.toml transfer
      ```
      Executes the transaction scenarios defined in the `transfer` section of the configuration. It will print periodic status updates.

    - **Shutdown Nodes**:

      ```bash
      python main.py config.toml shutdown
      ```
      Cleans up by shutting down all the nodes defined in the `fibers` section.

### Example Workflow

A typical workflow would be to run the commands in sequence:

```bash
# 1. Setup connections
python main.py config.toml connect_to

# 2. Verify connections
python main.py config.toml check_connect

# 3. Run the transaction load test
python main.py config.toml transfer

# 4. Cleanup
python main.py config.toml shutdown
```

### TODO
- [ ] Add check balance
- [ ] Add support transfer ckb  and udt transfer
- [ ] Add support for udt