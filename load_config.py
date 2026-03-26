import os
import redis
import json
import sys
from dotenv import load_dotenv

def load():
    # Load .env if it exists
    load_dotenv()
    redis_raw = os.getenv("REDIS_ENDPOINT") or f"{os.getenv('REDIS_HOST', 'redis_container')}:{os.getenv('REDIS_PORT', '6379')}"
    
    endpoint = os.getenv("NETWORK_ENDPOINT") or "http://brain:8000"
    

    contract_raw = os.getenv("CONTRACT") or '{"mechanism": "proof-of-work", "difficulty": 4}'
    
    try:

        parts = redis_raw.split(":")
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 6379
        

        contract = json.loads(contract_raw)
        
        # to create one single global connection for everyone
        r = redis.Redis(host=host, port=port, socket_timeout=3, decode_responses=True)
        r.ping()
        
        return endpoint, r, contract

    except redis.ConnectionError:
        sys.stderr.write(f"❌ Redis unreachable at {redis_raw}. Check container name/network.\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"💥 Config Load Failed: {e}\n")
        sys.exit(1)

# Global variables exported for the rest of the app
endpoint, r, contract = load()