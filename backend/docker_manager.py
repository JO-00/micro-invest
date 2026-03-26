import docker
import logging,sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)] # Force output to Docker logs
)


logger = logging.getLogger("blockchain.spawner")
client = docker.from_env()

def spawn_container(name: str, is_miner: bool):
    """The trigger that actually starts the physical container"""
    
    container_name = f"node_{name.lower().replace(' ', '_')}"
    
    # 1. Log the intent
    logger.info(f"🚀 Attempting to spawn container: {container_name} (Miner: {is_miner})")
    
    env_vars = {
        "NODE_NAME": name,
        "IS_MINER": str(is_miner).lower(),
        "REDIS_HOST": "redis_container",
        "PYTHONUNBUFFERED": "1" 
    }

    try:
        #cant afford to have duplicate containers here
        try:
            old = client.containers.get(container_name)
            logger.warning(f"⚠️ Container {container_name} already exists in state: {old.status}. Removing it...")
            old.remove(force=True)
        except docker.errors.NotFound:
            pass

        container = client.containers.run(
            image="blockchain_member",
            name=container_name,
            detach=True,
            environment=env_vars,
            network="blockchain_network", 
            restart_policy={"Name": "on-failure"} 
        )


        container.reload()
        logger.info(f"✅ Spawned {container_name}. ID: {container.short_id} | Status: {container.status}")
        
        if container.status == "exited":
            logger.error(f"❌ {container_name} exited immediately! Check 'docker logs {container_name}'")
            
        return container.id

    except Exception as e:
        logger.error(f"💥 Docker Spawn Failed for {container_name}: {str(e)}") #mostly error because of dupplicate containers or absent image
        return None