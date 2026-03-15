from data_structures import *
from actors import *
import pickle
if __name__ == "__main__":
    print("Configuring blockchain rules")
    zeroes = int(input("Enter number of leading zeroes required for mining: "))
    price = int(input("Enter mining reward (in coins): "))
    genesis_data = json.dumps({"zeroes": zeroes, "price": price})
    print("Starting blockchain simulation...\n")
    blockchain = Blockchain(genesis_data)
    print(f"Genesis block created with rules: {blockchain.rules}\n")

    miner1 = Miner("Miner1", blockchain)
    miner2 = Miner("Miner2", blockchain)
    alice = Node("Alice", blockchain)
    bob = Node("Bob", blockchain)

    nodes = {
        "Miner1": miner1,
        "Miner2": miner2,
        "Alice": alice,
        "Bob": bob
    }
    with open('nodes.pkl', 'wb') as f:
        pickle.dump(nodes, f)

    async def main():
        Blockchain.update()  # Load blockchain nodes from file
        tx1 = {"from": "Alice", "to": "Bob", "amount": 10}
        await alice.broadcast_transaction(tx1)

        print("\nBalances after mining:")
        for n in Blockchain.nodes.values():
            print(f"{n.name}: {n.balance}")

    asyncio.run(main())