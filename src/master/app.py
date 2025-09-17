import os
import sys
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import ray
from distributed_tinyllama_actor import TinyLlamaActor
import time
import threading
import yaml

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!' # Replace with a strong secret key in production
socketio = SocketIO(app, cors_allowed_origins="*") # Allow all origins for development

# Global list to store actor handles
llama_actors = []
current_actor_idx = 0
master_config = {}

def load_config(config_path):
    """Load the master node configuration from YAML"""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        print(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        return {}

def init_ray_actors():
    global llama_actors, master_config

    # Load configuration
    config_path = os.path.join(os.path.dirname(__file__), '../../config/master.yaml')
    master_config = load_config(config_path)
    num_llama_actors = master_config.get('model_config', {}).get('num_llama_actors', 1)

    print(f"Attempting to create {num_llama_actors} TinyLlamaActor instances.")

    # Ray should be initialized by start_master.py. If running app.py standalone, uncomment the following line:
    if not ray.is_initialized():
        ray.init(address='auto', ignore_reinit_error=True, log_to_driver=True)

    try:
        print("Ray initialized for TinyLlama actors.")
        for i in range(num_llama_actors):
            actor = TinyLlamaActor.options(runtime_env={
                "pip": [
                    "ray[default]>=2.45.0",
                    "pyarrow>=14.0.1",
                    "protobuf>=4.25.1",
                    "torch>=2.1.0",
                    "transformers>=4.36.0",
                    "sentencepiece>=0.1.99",
                    "numpy>=1.24.0",
                    "pandas>=2.1.0",
                    "tqdm>=4.66.1",
                    "requests>=2.31.0",
                    "netifaces",
                    "Flask>=2.3.0",
                    "Flask-SocketIO>=5.3.0",
                    "gevent>=21.12.0",
                    "wandb>=0.16.0",
                    "loguru>=0.7.2",
                ]
            }).remote()
            llama_actors.append(actor)
            print(f"TinyLlamaActor {i+1}/{num_llama_actors} created.")
        
        # Load models for all actors
        ray.get([actor.load_model.remote() for actor in llama_actors])

    except Exception as e:
        print(f"Error creating TinyLlamaActors: {e}")

# Initialize Ray actors in a separate thread to avoid blocking Flask app startup
init_thread = threading.Thread(target=init_ray_actors)
init_thread.daemon = True  # Allow the main program to exit even if the thread is still running
init_thread.start()

# Wait for all actors to be initialized before allowing connections
while not llama_actors or any(ray.get(actor.__ray_ready__.remote()) is False for actor in llama_actors):
    print("Waiting for TinyLlamaActors to initialize...")
    time.sleep(1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stress_test')
def stress_test_page():
    return render_template('stress_test.html')

@socketio.on('connect')
def test_connect():
    emit('my response', {'data': 'Connected'})
    print('Client connected')

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')

@socketio.on('message')
def handle_message(data):
    print('received message: ' + str(data))
    emit('my response', {'data': data['data']})

@app.route('/api/ray_nodes', methods=['GET'])
def get_ray_nodes():
    if not ray.is_initialized():
        return jsonify({"error": "Ray is not initialized"}), 500
    nodes = ray.nodes()
    return jsonify([node for node in nodes])

@app.route('/api/run_stress_test', methods=['POST'])
def run_stress_test():
    if not ray.is_initialized():
        return jsonify({"error": "Ray is not initialized"}), 500
    try:
        # Run the stress test workload as a Ray task
        @ray.remote
        def run_workload_task():
            import subprocess
            import sys
            script_path = os.path.join(os.path.dirname(__file__), 'stress_test_workload.py')
            # Ensure the virtual environment is activated before running the script
            command = f"source {sys.prefix}/bin/activate && python3 {script_path}"
            process = subprocess.run(command, shell=True, capture_output=True, text=True, executable='/bin/zsh')
            return {"stdout": process.stdout, "stderr": process.stderr, "returncode": process.returncode}

        # Start the task asynchronously
        task_ref = run_workload_task.remote()
        return jsonify({"message": "Stress test started", "task_id": str(task_ref)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@socketio.on('chat_message')
def handle_chat_message(message):
    global llama_actors, current_actor_idx
    print(f"Received chat message: {message['data']}")
    prompt = message['data']

    if not llama_actors:
        emit('response', {'text': 'TinyLlama models are still loading. Please try again in a moment.'})
        return

    try:
        # Round-robin distribution of requests to actors
        current_actor = llama_actors[current_actor_idx]
        current_actor_idx = (current_actor_idx + 1) % len(llama_actors)

        # Asynchronously call the Ray actor and get the result
        response, tps = ray.get(current_actor.generate_response.remote(prompt))

        active_nodes = 0
        try:
            # Get cluster resources to determine active nodes more reliably
            cluster_resources = ray.cluster_resources()
            # Count nodes that have 'node:1' resource, which indicates an active node
            active_nodes = sum(1 for resource_name in cluster_resources if resource_name.startswith('node:'))
        except Exception as resource_e:
            print(f"Error getting cluster resources: {resource_e}")
            # Fallback or log error if resources cannot be retrieved

        
        emit('response', {'text': response})
        emit('tps_update', {'tps': f"{tps:.2f}", 'nodes': active_nodes})
        print(f"Response: {response}")
        print(f"TPS: {tps:.2f}, Nodes: {active_nodes}")
    except Exception as e:
        print(f"Error generating response: {e}")
        emit('response', {'text': f"Error: {e}"})

if __name__ == '__main__':
    # In a production environment, use a more robust WSGI server like Gunicorn with gevent worker
    # Example: gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 app:app -b 0.0.0.0:5000
    socketio.run(app, debug=False, host='0.0.0.0', port=8000)