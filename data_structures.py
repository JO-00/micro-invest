
import hashlib
import time
import json
import asyncio
from ecdsa import SigningKey, SECP256k1
import pickle
class Block:
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash

    def compute_hash(self):
        block_string = f"{self.index}{self.timestamp}{self.data}{self.previous_hash}"
        return hashlib.sha256(block_string.encode()).hexdigest()

class Blockchain:
    nodes = {}
    def __init__(self, genesis_data):
        self.chain = []
        self.create_genesis_block(genesis_data)
        self.rules = json.loads(self.chain[0].data)
        self.lock = asyncio.Lock()  # ensure only one miner appends at a time

    def create_genesis_block(self, genesis_data):
        self.chain.append(Block(0, time.time(), genesis_data, "0"))

    async def add_block(self, new_block, miner_name):
        async with self.lock:
            # Prevent duplicate mining
            if new_block.previous_hash != self.chain[-1].compute_hash():
                return False
            self.chain.append(new_block)

            Blockchain.nodes[miner_name].balance += self.rules['price']
            with open('nodes.pkl', 'wb') as f:
                pickle.dump(Blockchain.nodes, f)
            # process transactions
            data = json.loads(new_block.data)
            for tx in data.get("transactions", []):
                sender = tx["from"]
                receiver = tx["to"]
                amount = tx["amount"]
                if Blockchain.nodes[sender].balance >= amount:
                    Blockchain.nodes[sender].balance -= amount
                    Blockchain.nodes[receiver].balance += amount
                    print(f"{sender} paid {amount} coins to {receiver}")
                else:
                    print(f"Transaction failed: {sender} has insufficient balance")
            return True
    @staticmethod
    def update():
        with open('nodes.pkl', 'rb') as f:
            Blockchain.nodes = pickle.load(f)