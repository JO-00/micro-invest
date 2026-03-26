from node import Node
import requests,uuid,json,logging,sys,traceback,hashlib,time
from load_config import endpoint,r


logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                stream=sys.stderr,
                force=True  # This forces reconfiguration even if already configured
            )
logger = logging.getLogger()





class Miner(Node):
    def __init__(self, name):
        super().__init__(name)

    def sign_up(self):
        logger.info(f"🛰️ NODE {self.name}: Starting sign_up sequence...")
        
        try:
            target_url = endpoint + "/add_node"
            generated_id = str(uuid.uuid4())
            logger.info(f"URL set to {target_url}")
            
            payload = {
                "name": self.name,
                "uid": generated_id,
                "public_key_hex": self.public_key_hex,
                "balance": 0,
                "is_miner": True,
                "private_key_hex": self.private_key_hex
            }

            resp = requests.post(target_url, json=payload, timeout=5)
            
            if resp.status_code == 200:
                logger.info(f"✅ NODE {self.name}: Registered successfully.")
                return True
            else:
                logger.warning(f"❌ Rejected: {resp.status_code} - {resp.text}")
                
        except NameError as ne:
            logger.error(f"🔥 CRITICAL NAME ERROR: {ne}")
            
            logger.error(traceback.format_exc())
        except Exception as e:
            logger.warning(f"❌ Connection failed: {type(e).__name__} -> {e}")
        
        return False
    def listen_for_jobs(self):
            pubsub = r.pubsub()
            pubsub.subscribe("mining_tunnel", f"direct_order:{self.name}")
            
            for message in pubsub.listen():
                logger.info("new message")
                if message['type'] == 'message':
                    
                    self.mine(json.loads(message['data']))
    
    def mine(self, block_raw):
            

            # 1. Prepare
            tx_list = block_raw.get("transactions", [])
            data_string = json.dumps(tx_list, sort_keys=True)
            index = block_raw.get("index")
            prev_hash = block_raw.get("previous_hash")
            difficulty = block_raw.get("difficulty", 4)
            prefix = '0' * difficulty
            nonce = 0
            
            
            print(f"⛏️  [MINER {self.name}] Starting work on Block {index}...", flush=True)

            # 2. Loop
            while True:
                check_str = data_string + str(nonce)
                guess_hash = hashlib.sha256(check_str.encode()).hexdigest()
                if guess_hash.startswith(prefix):
                    break
                nonce += 1

            # mined_block follows the exact Block pydantic structure here!
            mined_block = {
                "index": index,
                "timestamp": time.time(),
                "data": data_string,
                "previous_hash": prev_hash,
                "hash": guess_hash,
                "nonce": nonce,
                "miner_name": self.name
            }
            logger.info(f"💎 [MINER {self.name}] FOUND BLOCK {index}!")
            try:
                brain_url = endpoint + "/add_block"
                response = requests.post(brain_url, json=mined_block)
                
                if response.status_code == 200:
                    print(f"🚀 [MINER {self.name}] Brain accepted block {index}!", flush=True)
                else:
                    print(f"❌ [MINER {self.name}] Brain rejected block: {response.text}", flush=True)
            except Exception as e:
                print(f"🔥 [MINER {self.name}] Connection Error: {e}", flush=True)


