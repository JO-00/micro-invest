from fastapi import APIRouter,HTTPException
from pydantic import BaseModel
import json,logging,time
from load_config import r
from backend import docker_manager

class Node_Simplified(BaseModel):
    name: str
    uid: str           
    public_key_hex: str = None
    balance: int = 0     
    is_miner: bool = False
    private_key_hex :str = None



Nodes = APIRouter()


@Nodes.post("/delete_nodes")
def delete_nodes(nodes : list[str] = None):
    results = []
    for node in nodes:
        results.append((node,r.delete(node)))
        r.lrem("nodes", 0, node)
    if all([res[1] for res in results]):
        print("All existing nodes deleted")
    else:
        print(results)



@Nodes.post("/add_node")
def add_node(node: Node_Simplified = None):
    logger = logging.getLogger(__name__)
    logger.info(f"--- [BRAIN] START ADD_NODE FOR: {node.name} ---")
    
    if not node:
        logger.error("[BRAIN] No node payload received")
        return {"error": "No node provided"}
    
    try:
        # identical names causes many bugs for this app
        existing_info = r.get(node.name)
        if existing_info:
            logger.warning(f"[BRAIN] Node {node.name} already exists in Redis. Skipping spawn.")
            return {"status": "success", "message": "already_exists"}

     
        logger.info(f"[BRAIN] Writing {node.name} to Redis...")
        r.set(node.name, node.model_dump_json())

        #the quick part here, just add node to redis
        existing_list = r.lrange("nodes", 0, -1)
        if node.name not in existing_list:
            r.rpush("nodes", node.name)
            logger.info(f"[BRAIN] Added {node.name} to 'nodes' list.")

        # the slow part, a seperate container for the node
        logger.info(f"[BRAIN] Calling Docker to spawn {node.name}...")
        start_docker = time.time()
        container_id = docker_manager.spawn_container(node.name, node.is_miner)
        docker_duration = time.time() - start_docker
        
        logger.info(f"[BRAIN] Docker finished in {docker_duration:.2f}s. ID: {container_id}")

        if not container_id:
            logger.error("[BRAIN] Docker failed to return a container ID")
            raise Exception("Docker failed to spawn container")

        logger.info(f"--- [BRAIN] SUCCESS FOR {node.name} ---")
        return {
            "status": "success", 
            "container_id": container_id
        }

    except Exception as e:
        logger.error(f"[BRAIN] CRITICAL FAILURE: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@Nodes.get("/list_nodes",response_model = list[str])
def list_nodes():
    return r.lrange("nodes", 0, -1)

@Nodes.get("/info_node/{node_name}",response_model=Node_Simplified)
def info_node(node_name):
    raw_data = r.get(node_name)
    if not raw_data:
        raise HTTPException(status_code=404, detail="Node not found")
    return json.loads(raw_data)



@Nodes.post("/save_key/{name}")
async def save_key(name: str, key_data: dict):
    # key_data = {"private_key_hex": "..."}
    priv_hex = key_data.get("private_key_hex")
    if not priv_hex:
        return {"error": "No key provided"}, 400
    
    # Store in Redis: node:privkey:Alice
    r.set(f"node:privkey:{name}", priv_hex)
    return {"status": "Key saved to Vault"}

@Nodes.get("/load_key/{name}")
async def load_key(name: str):
    #just for debugging
    redis_key = f"node:privkey:{name}"
    print(f"DEBUG : Looking for key -> '{redis_key}'")
    
    val = r.get(redis_key)
    if not val:
        print(f"DEBUG : key not found : '{redis_key}'")
        return {"error": f"Key {redis_key} not found in Redis"}, 404
    return {"private_key_hex": val}