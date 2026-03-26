import logging
import sys
import os
import time
import traceback

# 1. IMMEDIATE LOGGING SETUP (Critical for Docker)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr, # 👈 Force logs to stderr to avoid the "trash"
    force=True
)
logger = logging.getLogger("blockchain.node")

try:
    logger.info("🚀 Container starting phase: Environment check...")
    
    # Check if we can see the variables
    node_name = os.getenv("NODE_NAME")
    is_miner_str = os.getenv("IS_MINER", "false")
    logger.info(f"📋 ENV RECEIVED: NODE_NAME={node_name}, IS_MINER={is_miner_str}")

    if not node_name:
        logger.error("❌ NODE_NAME is missing! Exiting...")
        sys.exit(1)

    # 2. DELAYED IMPORTS (Catching the 'split' error here)
    logger.info("🚀 Container phase: Importing Miner/Node modules...")
    from miner import Miner
    from node import Node
    
    is_miner_mode = is_miner_str.lower() == "true"

    if is_miner_mode:
        logger.info(f"⛏️ Creating Miner actor for: {node_name}")
        actor = Miner(node_name)
    else:
        logger.info(f"💎 Creating Standard Node actor for: {node_name}")
        actor = Node(node_name)

    logger.info(f"📡 Registering {node_name} on the network...")
    actor.sign_up()

    if is_miner_mode:
        logger.info(f"🛠️ Starting Miner listener loop for {node_name}...")
        actor.listen_for_jobs()
    else:
        logger.info(f"💤 Node {node_name} entering idle wait state...")
        while True:
            time.sleep(10)

except Exception as e:
    # 3. THE TRAP: Capture the 'NoneType' Split error here
    logger.error("💥 CRITICAL FATAL ERROR ENCOUNTERED")
    # This sends the full stack trace to stderr
    logger.error(traceback.format_exc()) 
    
    # 4. PREVENT EXIT: Keep container alive so you can inspect it
    logger.info("⏸️ Container held open for 10 minutes for manual debugging...")
    time.sleep(600)