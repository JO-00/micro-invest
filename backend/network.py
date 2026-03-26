from fastapi import FastAPI
from dotenv import load_dotenv as load_dotenv
from contextlib import asynccontextmanager
import uvicorn,time,json,backend.routers.manipulate_blocks,backend.routers.manipulate_nodes,sys,logging
from hashlib import sha256
from load_config import r,endpoint


logger = logging.getLogger("uvicorn")

def calculate_hash(block_dict):
    block_string = json.dumps(block_dict, sort_keys=True).encode()
    return sha256(block_string).hexdigest()




@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"second attempt endpoint = {endpoint}")
    #before the server starts we initialize the chain inside the redis db with this wrapper
    
    print("Initializing Blockchain State...")
    if not r.get("block_latest"): #in case we want to use previous blocks from the redis db


        genesis_data = {
            "index": 0,
            "timestamp": time.time(),
            "data": "Genesis Block: Modular System Initialized.",
            "previous_hash": "0" * 64,
            "nonce": 0 # Starting nonce
        }
        genesis_data["hash"] = calculate_hash(genesis_data)
        
      
        block_json = json.dumps(genesis_data)
        r.set("block:0", block_json)
        r.set("block_latest", block_json)
        r.rpush("chain", 0)
        print(f"genesis Generated: {genesis_data['hash'][:16]}...")
    
    yield
    print("Stopping network...")



from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
app = FastAPI(lifespan=lifespan)
app.include_router(backend.routers.manipulate_nodes.Nodes)
app.include_router(backend.routers.manipulate_blocks.Blocks)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"ValidationError: {exc.errors()}") # any errors pop up here
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


if __name__ == "__main__":
    logger.info(f"first attempt endpoint = {endpoint}")
    uvicorn.run(
        app,
        host = endpoint.split(":")[0],
        port = endpoint.split(":")[1]
    )

