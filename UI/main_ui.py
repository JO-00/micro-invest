import streamlit as st

from display_nodes import *
if "processing" not in st.session_state:
    st.session_state.processing = False
if "pending_block" not in st.session_state:
    st.session_state.pending_block = None



show_sidebar()
col_left, col_right = st.columns([1, 1])

if "trigger_mine" in st.session_state:
    st.session_state.pending_block = None 
    del st.session_state.trigger_mine

with col_left:
    "will add a history of transactions here in the future..."
    pass
        
with col_right:
    render_node_list()



