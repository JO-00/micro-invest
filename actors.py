
import asyncio
from data_structures import *
import time
import json
from ecdsa import SigningKey, SECP256k1

class Node:

    def __init__(self, name, blockchain):
        self.name = name
        self.blockchain = blockchain
        self.balance = 100
        self.private_key = SigningKey.generate(curve=SECP256k1)
        self.public_key = self.private_key.get_verifying_key()

    def sign_transaction(self, transaction):
        tx_bytes = json.dumps(transaction).encode()
        return self.private_key.sign(tx_bytes)

    async def broadcast_transaction(self, transaction):
        print(f"{self.name} is broadcasting transaction: {transaction}")
        signature = self.sign_transaction(transaction)
        for node in Blockchain.nodes.values():
            await node.detect_broadcast(transaction, signature, self.public_key)

    async def detect_broadcast(self, transaction, signature, sender_pubkey):
        tx_bytes = json.dumps(transaction).encode()
        print(f"{self.name} received transaction from {transaction['from']}")

        try:
            sender_pubkey.verify(signature, tx_bytes)
        except:
            print(f"{self.name} detected invalid transaction from {transaction['from']}")
            return
        if isinstance(self, Miner):
            await self.mine([transaction])
    




class Miner(Node):
    def __init__(self, name, blockchain):
        super().__init__(name, blockchain)

    async def mine(self, transactions):
        zeroes = self.blockchain.rules['zeroes']
        price = self.blockchain.rules['price']
        prefix_str = '0' * zeroes
        
        block_content = {
            "miner": self.name,
            "reward": price,
            "transactions": transactions
        }

        while True:
            
            new_block = Block(
                len(self.blockchain.chain),
                time.time(),
                json.dumps(block_content),
                self.blockchain.chain[-1].compute_hash()
            )
            if new_block.previous_hash != self.blockchain.chain[-1].compute_hash():
                print(f"{self.name} detected a new block mined by another miner. Stopping mining.")
                return

            new_hash = new_block.compute_hash()
            if new_hash.startswith(prefix_str):
                Blockchain.update()
                success = await self.blockchain.add_block(new_block, self.name)
                if success:
                    print(f"Block mined by {self.name}: {new_hash}")
                break
            await asyncio.sleep(0)  # yield to event loop
