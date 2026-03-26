import requests
from load_config import endpoint
import uuid,ecdsa,json

class Node:
    def __init__(self, name):
        self.name = name
        self.private_key_hex = None
        self.public_key_hex = None
        self.uid = None


    def _generate_keys(self):
        # 1. Generate the raw ECDSA keys
        sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
        vk = sk.get_verifying_key()
        
        # 2. Convert Private Key to Hex string
        # .to_string() gets the bytes, .hex() converts bytes to 'abc123...'
        self.private_key_hex = sk.to_string().hex()
        
        # 3. Convert Public Key to Hex string
        self.public_key_hex = vk.to_string().hex()

    def sign_up(self): 
        self._generate_keys()
        self.uid = str(uuid.uuid4())

        payload = {
            "name": self.name,
            "uid": self.uid,
            "public_key_hex": self.public_key_hex,
            "balance": 100,
            "is_miner":False,
            "private_key_hex" : self.private_key_hex
        }

        response = requests.post(endpoint+"/add_node", json=payload)
        if response.status_code == 200:
            print(f"✅ {self.name} Registered. KEEP YOUR UID SAFE: {self.uid}")
        else:
            print(f"❌ Registration failed: {response.text}")



    def sign_in(self, uid):
        response = requests.get(endpoint + "/info_node/{self.name}")
        if response.status_code == 200:
            data = response.json()
            if data['uid'] == uid:
                self.uid = uid
                self.public_key_hex = data['public_key_hex']
                print(f"🔓 {self.name} signed in successfully.")
            else:
                print("🚫 UID Mismatch!")
        else:
            print("❌ Node not found.")

    def sign_transaction(self, tx_data):
        # deterministic JSON message signing
        message = json.dumps(tx_data, sort_keys=True).encode()
        sk = ecdsa.SigningKey.from_string(
            bytes.fromhex(self.private_key_hex), 
            curve=ecdsa.SECP256k1
        )
        signature = sk.sign(message)
        

        return signature.hex()

    def broadcast_transaction(self, receiver, amount):
        tx_data = {
            "sender": self.name,
            "receiver": receiver,
            "amount": amount
        }
        # Add the signature to the payload
        tx_data["signature"] = self.sign_transaction(tx_data)
        
        return requests.post(endpoint + "/broadcast", json=tx_data)

                



                
        