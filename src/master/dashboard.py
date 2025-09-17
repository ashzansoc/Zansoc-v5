import ray
import os
import time
import streamlit as st
from distributed_tinyllama_actor import TinyLlamaActor

# Ensure Ray is initialized
if not ray.is_initialized():
    ray.init(address="auto", namespace="default", runtime_env={
        "pip": [
            "torch>=2.1.0",
            "transformers>=4.36.0",
            "bitsandbytes==0.42.0"
        ]
    })

def get_worker_nodes_count():
    """Gets the number of active worker nodes in the Ray cluster."""
    nodes = ray.nodes()
    # Exclude the head node (master) from the count
    worker_nodes = [node for node in nodes if not node.get("is_head", False)]
    return len(worker_nodes)

st.set_page_config(layout="wide", page_title="TinyLlama Ray Chatbot")
st.title("TinyLlama Ray Chatbot")

# Sidebar for status
st.sidebar.header("Cluster Status")
worker_count_placeholder = st.sidebar.empty()

# Initialize actors (once per session)
if 'actors' not in st.session_state:
    st.session_state.actors = []
    num_workers = get_worker_nodes_count()
    if num_workers == 0:
        st.sidebar.warning("No Ray workers detected. Please ensure your Ray cluster is running.")
    else:
        st.sidebar.info(f"Initializing {num_workers} TinyLlama actors...")
        for _ in range(num_workers):
            actor = TinyLlamaActor.remote()
            ray.get(actor.load_model.remote()) # Load model on each actor
            st.session_state.actors.append(actor)
        st.sidebar.success(f"{num_workers} TinyLlama actors ready.")

# Update worker count in sidebar
worker_count_placeholder.metric("Active Worker Nodes", get_worker_nodes_count())

# Chat interface
if 'messages' not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Say something..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not st.session_state.actors:
            st.error("No active TinyLlama actors to process the request.")
        else:
            message_placeholder = st.empty()
            full_response = ""
            total_tps = 0
            actor_responses = []

            # Distribute prompt to actors (e.g., round-robin or broadcast)
            # For simplicity, let's use the first actor for now.
            # In a real-world scenario, you might use a more sophisticated load balancing.
            selected_actor = st.session_state.actors[0]
            
            with st.spinner("Generating response..."):
                response, tps = ray.get(selected_actor.generate_response.remote(prompt))
                actor_responses.append((response, tps))

            # Aggregate responses (if multiple actors were used for one prompt)
            full_response = actor_responses[0][0]
            total_tps = actor_responses[0][1]
            
            message_placeholder.markdown(full_response)
            st.sidebar.metric("Tokens Per Second (TPS)", f"{total_tps:.2f}")

    st.session_state.messages.append({"role": "assistant", "content": full_response})