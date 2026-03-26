from fastapi import APIRouter,HTTPException
from load_config import r,contract
import json,ecdsa,logging,hashlib
from pydantic import BaseModel,field_validator

logger = logging.getLogger("uvicorn")


class Block(BaseModel):
    index: int
    timestamp: float
    data: str
    previous_hash: str
    hash: str = None
    nonce : int = 0
    miner_name:str="unknown"
class Transaction(BaseModel):
    sender : str
    receiver : str
    amount : int
    signature : str
    @field_validator("amount")
    def check_positive(cls,amount):
        if amount < 0:
            raise ValueError ("Can't send negative amount")
        return amount
    

def verify_signature(public_key_hex: str, signature_hex: str, tx_data) -> bool:
    try:
        if isinstance(tx_data, str):
            import json
            tx_data = json.loads(tx_data)

        #copy in order to safely remove signature
        data_to_verify = tx_data.copy()
        data_to_verify.pop("signature", None) 


        public_key_bytes = bytes.fromhex(public_key_hex)
        vk = ecdsa.VerifyingKey.from_string(public_key_bytes, curve=ecdsa.SECP256k1)

        #sorting is very very important, for deterministic signatures
        message = json.dumps(data_to_verify, sort_keys=True).encode()
        signature_bytes = bytes.fromhex(signature_hex)

        return vk.verify(signature_bytes, message)

    except (ecdsa.BadSignatureError, Exception) as e:
        print(f"Verification failed: {e}")
        return False
    




Blocks = APIRouter()



@Blocks.post("/add_block")
def add_block(block: Block):
    if r.exists(f"block:{block.index}"):
        logger.warning(f"⚠️ Block {block.index} already exists.")
        return {"status": "Ignored"}

    check_str = block.data + str(block.nonce)
    calculated_hash = hashlib.sha256(check_str.encode()).hexdigest()
    if calculated_hash != block.hash:
        raise HTTPException(status_code=400, detail="Invalid Hash! Data/Nonce mismatch.")

    # did a miner actually do the work?
    required_prefix = "0" * contract.get("difficulty", 4)
    if not calculated_hash.startswith(required_prefix):
        logger.error(f"🚫 Proof of Work failed! Hash {calculated_hash} doesn't meet difficulty {contract.get('difficulty', 4)}")
        raise HTTPException(status_code=400, detail="Insufficient Proof of Work!")

   #exxtracting transaction info
    try:
        tx_data = json.loads(block.data)
        tx = tx_data[0] if isinstance(tx_data, list) else tx_data
        sender_name = tx.get("sender")
        receiver_name = tx.get("receiver")
        amount = int(tx.get("amount", 0))
    except Exception as e:
        logger.error(f"💥 Data Error: {e}")
        raise HTTPException(status_code=400, detail="Malformed Tx")
    miner_name = getattr(block, 'miner_name', None)
    REWARD_AMOUNT = contract["reward"]


    '''
    this updates dictionary is crucial to avoid race conditions because we'll submit it to a redis pipeline
    meaning: a miner receives or sends money and gets rewarded for mining that block
    result : one update overwrites the other
    solution: instead of locks (that concern processes on one machine) we're gonna use pipelines (cuz many containers)
    '''
    updates = {} 

    def get_node_obj(name):
        if name not in updates:
            raw = r.get(name)
            if raw:
                updates[name] = json.loads(raw)
        return updates.get(name)

    sender_obj = get_node_obj(sender_name)
    receiver_obj = get_node_obj(receiver_name)
    miner_obj = get_node_obj(miner_name) if miner_name else None

    if sender_obj and receiver_obj:
        if sender_obj["balance"] >= amount:
            sender_obj["balance"] -= amount
            receiver_obj["balance"] += amount
            logger.info(f"💸 Transfer: {sender_name} -> {receiver_name} ({amount})")
        else:
            logger.warning(f"⚠️ Insufficient funds for {sender_name}")

    if miner_obj:
        miner_obj["balance"] += REWARD_AMOUNT
        logger.info(f"💰 Reward: {miner_name} +{REWARD_AMOUNT} (Total: {miner_obj['balance']})")

    #one atomic save for concurrency
    pipe = r.pipeline()
    for name, obj in updates.items():
        pipe.set(name, json.dumps(obj))

    # Save Block Data
    block_json = block.model_dump_json()
    pipe.set(f"block:{block.index}", block_json)
    pipe.set("block_latest", block_json)
    pipe.rpush("chain", block.index)
    pipe.delete("pending_block_data")
    
    pipe.execute()
    
    return {"status": "Success", "miner": miner_name, "amount_sent": amount}

@Blocks.get("/get_chain", response_model=list[Block])
def get_chain():
    try:
        
        indices = r.lrange("chain", 0, -1)
        chain = []
        for idx in indices:
            block_data = r.get(f"block:{idx}")
            if block_data:
                chain.append(json.loads(block_data))
        return chain
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@Blocks.get("/latest_block", response_model=Block)
def latest_block():
    
    last_idx = r.lindex("chain", -1)
    if last_idx is None:
        raise HTTPException(status_code=404, detail="Blockchain is empty")
    return json.loads(r.get(f"block:{last_idx}"))



@Blocks.post("/broadcast")
def broadcast(tx: Transaction):
    sender_raw = r.get(tx.sender)
    receiver_raw = r.get(tx.receiver)

    if not sender_raw or not receiver_raw:
        raise HTTPException(status_code=404, detail="Nodes do not exist")

    sender_data = json.loads(sender_raw)
    
    # verifications of: balance & sig
    if sender_data["balance"] < tx.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    tx_payload = json.dumps({"sender": tx.sender, "receiver": tx.receiver, "amount": tx.amount}, sort_keys=True)
    if not verify_signature(sender_data["public_key_hex"], tx.signature, tx_payload):
        raise HTTPException(status_code=401, detail="Signature mismatch")
    

    # Get Last Block to build the new one + create job
    last_block_raw = r.get("block_latest")
    last_block = json.loads(last_block_raw)

    new_job = {
        "index": last_block["index"] + 1,
        "transactions": [{"sender": tx.sender, "receiver": tx.receiver, "amount": tx.amount}],
        "previous_hash": last_block["hash"],
        "difficulty": contract["difficulty"]
    }

    # this is exactly where the miners listen
    r.set("pending_block_data", json.dumps(new_job))
    
    
    return {"status": "Transaction broadcasted and saved to pending pool."}


#this is totally against nature of blockchai, but for testing we try to give a block to a specific miner for him to mine
@Blocks.post("/trigger_mining")
def trigger_mining(payload: dict):
    miner_name = payload.get("miner_name")
    logger.info(f"🎯 [BRAIN] Attempting to trigger miner: {miner_name}")
    
    block_data = r.get("pending_block_data") 
    
    if not block_data:
        logger.error("❌ [BRAIN] FAILED: 'pending_block_data' is EMPTY in Redis!")
        return {"status": "error", "message": "No pending block found!"}
    

    try:
        receivers = r.publish(f"direct_order:{miner_name}", block_data)
        logger.info(f"📢 [BRAIN] Published to channel direct_order:{miner_name}. Listeners reached: {receivers}")
        
        if receivers == 0:
            logger.warning(f"⚠️ [BRAIN] Published, but ZERO miners were listening on direct_order:{miner_name}")
            
        return {"status": "success", "listeners": receivers}
    except Exception as e:
        logger.error(f"💥 [BRAIN] Publish failed: {str(e)}")
        return {"status": "error", "message": str(e)}