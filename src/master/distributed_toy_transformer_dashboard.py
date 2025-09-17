import ray
import time
import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from transformers import AutoTokenizer
import subprocess

# -------------------------------
# Setup Ray
# -------------------------------
ray.init(address="auto")  # connect to existing Ray cluster

# -------------------------------
# Worker Actor: runs llama.cpp binary
# -------------------------------
@ray.remote(num_cpus=2)
class LlamaWorker:
    def __init__(self, worker_id, model_path):
        self.worker_id = worker_id
        self.model_path = model_path
        self.tokenizer = AutoTokenizer.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    
    def generate(self, prompt: str, max_tokens: int = 64):
        start = time.time()

        # call llama.cpp binary on worker (assuming it's on each worker node)
        # Example (replace with actual binary path):
        cmd = [
            "./llama.cpp/main",
            "-m", self.model_path,
            "-p", prompt,
            "-n", str(max_tokens),
            "--temp", "0.7"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout.strip()

        duration = time.time() - start
        tps = max_tokens / duration if duration > 0 else 0
        return {"worker": self.worker_id, "output": output, "tps": tps}

# -------------------------------
# Deploy Workers
# -------------------------------
MODEL_PATH = "/home/pi/models/TinyLlama-1.1B-q4.bin"
workers = [LlamaWorker.remote(i, MODEL_PATH) for i in range(3)]  # adjust number of workers

# -------------------------------
# Master: Distribute prompts
# -------------------------------
async def distributed_generate(prompt: str, max_tokens: int = 64):
    # Run prompt on all workers in parallel
    results = await asyncio.gather(*[w.generate.remote(prompt, max_tokens) for w in workers])

    # Aggregate results (naive: concat outputs)
    outputs = [r["output"] for r in results]
    avg_tps = sum(r["tps"] for r in results) / len(results)
    return {
        "outputs": outputs,
        "combined": "\n---\n".join(outputs),
        "avg_tps": avg_tps,
        "num_nodes": len(results)
    }

# -------------------------------
# Dashboard with FastAPI
# -------------------------------
app = FastAPI()

@app.get("/")
def index():
    return HTMLResponse("""
    <html>
    <head><title>Distributed TinyLlama Dashboard</title></head>
    <body>
        <h1>Distributed TinyLlama</h1>
        <form action="/chat" method="get">
            <input type="text" name="q" placeholder="Ask me anything" style="width:300px"/>
            <button type="submit">Send</button>
        </form>
        <div id="response"></div>
    </body>
    </html>
    """)

@app.get("/chat")
async def chat(q: str):
    result = await distributed_generate(q, max_tokens=64)
    return {
        "answer": result["combined"],
        "nodes": result["num_nodes"],
        "avg_tokens_per_sec": result["avg_tps"]
    }

# -------------------------------
# Run
# -------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
