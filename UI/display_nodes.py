from pydantic import BaseModel
import streamlit as st
from load_config import endpoint
import requests,logging,sys,time
from Actors.node import Node 
class Node_Simplified(BaseModel):
    uid:str = None
    name : str = None
    balance: int=0
    private_key_hex: str = None
    public_key_hex : str = None
    is_miner: bool = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr, #dump it to stderr cuz stdout not reliable for logs
    force=True
)

POST = lambda api,data : requests.post(endpoint+api,json=data)
GET = lambda api: requests.get(endpoint+api)



def pad():
    for _ in range(9):
        st.write("")


def show_sidebar():
    logger = logging.getLogger("streamlit")
    

    try:
        node_list = GET("/list_nodes").json()
        current_count = len(node_list)
    except:
        current_count = 0

    # Sync prev_nodes to reality
    if "prev_nodes" not in st.session_state:
        st.session_state.prev_nodes = current_count
    
    # Force sync if reality shifted
    if st.session_state.prev_nodes != current_count:
        st.session_state.prev_nodes = current_count

    prev = st.session_state.prev_nodes

    with st.sidebar:
        
        nodes = st.number_input(
            "Nodes in network", 
            min_value=0, max_value=10, 
            value=current_count,
            disabled=st.session_state.get("processing", False) # Disable the input if we are already processing a request
        )
        
        if nodes > prev:
            st.info(f"Adding {nodes - prev} node(s)")
            with st.popover("Configure Next Node", use_container_width=True):
                name = st.text_input("Node Name", key="input_node_name")
                balance = st.number_input("Initial Balance", value=0)
                is_miner = st.checkbox("Miner Role")
                
                if st.button("Launch Node", disabled=st.session_state.processing):
                    if not name:
                        st.error("Name required")
                    else:
                        
                        st.session_state.processing = True 
                        logger.info(f"🚀 [UI] 'Launch' clicked for {name}. Processing set to TRUE.")
                        
                        with st.spinner(f"Spawning {name}..."):
                            try:
                                '''
                                given a name, we create a node and generate its keys and call /add_node 
                                to register it to redis and add a new container for it!
                                '''
                                logic_node = Node(name)
                                logic_node._generate_keys()
                                
                                '''
                                logically, sending a private key to the network means introducting a trusted third
                                party breaking decentralization, but we need it to simulate transactions and to make
                                a transaction we must use the node's privkey to sign
                                '''

                                payload = Node_Simplified(
                                    uid=f"{name}_{int(time.time())}", 
                                    name=name,
                                    balance=balance,
                                    is_miner=is_miner,
                                    public_key_hex=logic_node.public_key_hex,
                                    private_key_hex=""
                                )
                                
                                resp = POST("/add_node", payload.model_dump())
                                
                                if resp.status_code == 200:
                                    # 4. SAVE KEYS
                                    logger.info(f"🔑 [UI] Registering keys for {name}...")
                                    if POST(f"/save_key/{name}", {"private_key_hex": logic_node.private_key_hex}).status_code == 200:
                                        logger.info("key successfully saved")
                                    else:
                                        logger.info("unable to save key")
                                    
                                    # release lock and update nodes
                                    st.session_state.prev_nodes = nodes
                                    st.session_state.processing = False 
                                    
                                    st.success(f"✅ {name} launched successfully!")
                                    logger.info(f"🏁 [UI] Success. Unlocking and rerunning.")
                                    
                                    #tiny pause so user sees success message
                                    time.sleep(1.2)
                                    st.rerun()
                                else:
                                    logger.error(f"❌ [UI] Brain Error: {resp.text}")
                                    st.error(f"Brain Error: {resp.text}")
                                    st.session_state.processing = False

                            except Exception as e:
                                logger.error(f"💥 [UI] Critical Crash: {str(e)}")
                                st.error(f"UI Crash: {str(e)}")
                                st.session_state.processing = False


def render_node_list():
    logger = logging.getLogger("streamlit")
    st.subheader("Network Nodes")
    
    try:
        names = GET("/list_nodes").json()
        nodes_info = [GET(f"/info_node/{name}").json() for name in names]
    except Exception as e:
        logger.error(f"LIST RENDER FAILED: {str(e)}")
        st.error("Connection to network lost.")
        return

    pending = st.session_state.get("pending_block") #need this to know whether we add "mine" button or not

    for idx, node in enumerate(nodes_info):
        with st.container(border=True):
            c1, c2 = st.columns([2, 1])
            
            with c1:
                icon = "⛏️" if node.get('is_miner') else "👤"
                st.markdown(f"### {icon} {node['name']}")
                st.caption(f"Wallet Balance")
                st.markdown(f"**{node.get('balance', 0)}** units")
                
            with c2:
                if node.get('is_miner'):
                    pad()

                    if st.button("Mine", key=f"mine_{node['name']}_{idx}", use_container_width=True):
                        logger.info(f"ACTION: Mining triggered by {node['name']}")
                        mine_resp = POST("/trigger_mining", {"miner_name": node['name']})
                        
                        if mine_resp.status_code == 200:
                            st.session_state.pending_block = False
                            st.toast(f"✅ {node['name']} mined!")
                            time.sleep(0.8)
                            st.rerun() # refresh to show new balances!
                        else:
                            st.error(f"Mining failed: {mine_resp.text}")
                else:
                    st.write("") 
                    st.caption("Standard Node")

    st.divider()
    btn_left, btn_right = st.columns(2)

    with btn_left:
        with st.popover("Generate Transaction", use_container_width=True):
            src = st.selectbox("From", options=names, key="tx_src")
            dst = st.selectbox("To", options=names, key="tx_dst")
            amount = st.number_input("Amount", min_value=1, key="tx_amount")
            
            if st.button("Broadcast", key="btn_broadcast_main", use_container_width=True):
                logger.info(f"ACTION: Broadcast Clicked: {src} -> {dst} ({amount})")
                key_resp = GET(f"/load_key/{src}")
                
                if key_resp.status_code == 200:

                    data = key_resp.json()
                    pk_hex = None

                    #to debug
                    if isinstance(data, dict):
                        pk_hex = data.get("private_key_hex")
                    elif isinstance(data, list) and len(data) > 0:
                        pk_hex = data[0].get("private_key_hex") if isinstance(data[0], dict) else data[0]
                    else:
                        pk_hex = data

                    if not pk_hex:
                        logger.error(f"❌ KEY IS EMPTY for {src}. Data received: {data}")
                        st.error(f"Private key for {src} is missing or null!")
                    else:
                        try:
                            logger.info(f"KEY RECOVERY: Recovered key for {src}. Proceeding to sign.")
                            sender_node = Node(src)
                            sender_node.private_key_hex = str(pk_hex) # Force string
                            
                            response = sender_node.broadcast_transaction(dst, amount)
                            
                            if response.status_code == 200:
                                st.toast(f"✅ Transaction Sent!")
                                st.session_state.pending_block = True
                                time.sleep(0.8)
                                st.rerun()
                            else:
                                st.error(f"Broadcast Failed: {response.text}")
                        except Exception as e:
                            logger.error(f"SIGNING CRASH: {str(e)}")
                            st.error(f"Signing failed: {e}")
                else:
                    st.error(f"Could not load key for {src}")
    with btn_right:
        if pending:
            if st.button("Mine All", type="primary", use_container_width=True, key="btn_mine_all"):
                logger.info("ACTION: Mine All clicked.")
                # button doesnt really work, will be fixed in the future with a new endpoint /mine_all
                st.session_state.pending_block = None
                st.rerun()

                