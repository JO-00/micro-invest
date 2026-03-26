# 🛸 Mini Blockchain: Distributed Orchestrator

Beginner-friendly simulation of a blockchain with mining, signed transactions, and dynamic node orchestration

Nodes are added via dynamic container spawning in a docker isolated network

---

## 🏗️ The Architecture
This is a bit similar to a **microservices ecosystem**, we have :

* **The Brain (FastAPI):** resource allocation, Docker spawning, responding to node needs etc
* **The database (Redis):** manages the chain of blocks, node balances, and private keys.
* **The Members (Docker):** Independent containers spawned on-the-fly to simulate live network nodes.
* **The UI (Streamlit):** Real-time command center for monitoring the network and broadcasting transactions and mining them

---

## ✨ Main Features
- **Dynamic Container Spawning**: Nodes aren't just objects; they are isolated Linux environments launched via the Docker SDK.
- **Atomic Accounting**: Uses Redis pipelines to prevent race conditions during block rewards (**aka** balances are updated atomically in a transaction)
- **ECDSA Security**: Real cryptographic signing and verification for all transactions using SECP256k1.
- **Configurable Consensus**: you may configure difficulty of work and the mining reward easily

---

## 🚀 Launching the Network

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)

### 1. Build & Boot the Core
>Make sure that before rerunning, you remove all stopped containers that acted as nodes or miners if you ran the app before, as I'm working on fixing that bug in the future

>(use ```docker rm -f <container_id1> <container_id2> ...``` for that)
```bash
docker pull djo007/mini-blockchain:brain
docker pull djo007/mini-blockchain:ui
docker pull djo007/mini-blockchain:member
docker-compose up --build
```

### 2. Summon the Nodes
Open the UI at `localhost:8501`, use the interface to "Add Node," and watch as the Brain physically spawns new containers to join the `blockchain_network`.

---

## 🛠️ Tech Stack
| Component | Tech |
| :--- | :--- |
| **Backend** | Python / FastAPI |
| **State** | Redis |
| **Orchestration** | Docker SDK |
| **UI** | Streamlit |
| **Crypto** | ECDSA (SECP256k1) |

---

## 🏗️ Technical Details
- **Atomic Accounting**: Implements Redis Pipelines to handle race conditions when a miner is also a transaction participant
- **Proof-of-Work**: Miners perform SHA-256 hashing to meet a dynamic difficulty prefix (e.g., `0000`) (u can configure that in .env if you want)
- **Logging**: I'm forcing logs into ```sys.stderr``` to debug for now

---
### 📂 Project Structure

```text
.
├── Actors
│   ├── miner.py            # solving Proof-of-Work
│   ├── node.py             # handles keys, balances, and signing
│   └── run_container.py    # Entrypoint script that boots the Node inside Docker
|
├── backend
│   ├── docker_manager.py   # Orchestrator using Docker SDK to spawn/kill Node containers
│   ├── network.py          # FastAPI "Brain" setup and main API entrypoint
|   |
│   └── routers
│       ├── manipulate_blocks.py  # Logic for block validation, mining, and chain state
│       └── manipulate_nodes.py   # Logic for node registration and lookups
|
|
├── UI
│   ├── main_ui.py          # streamlit dashboard to monitor
│   └── display_nodes.py    # a few helper functions for that main_ui.py
|
├── docker-compose.yml      # configs for the main 3 containers that build the initial network
├── global_dockerfile       # Dockerfile for the Brain and UI services
├── member_dockerfile       # Dockerfile only for those dynamically spawned nodes (less dependencies)
├── load_config.py          # fetch env vars
├── requirements.txt        # Python dependencies
└── README.md               # the file you're currently reading ;)
