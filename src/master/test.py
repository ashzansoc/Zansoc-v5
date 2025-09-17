# distributed_toy_transformer.py
"""
Distributed toy transformer (pipeline parallelism) across Ray worker nodes.
Master runs this script. Worker nodes only need ray + numpy.
- Splits N transformer blocks across available workers (excluding head).
- Each worker stores its shard's params and exposes a forward() RPC.
- Master coordinates the forward pass for a single prompt and prints tokens/sec + active nodes.

This is a proof-of-concept SLM (tiny) to demonstrate single-request
model-parallel execution across Raspberry Pi worker nodes.

Run:
  # on master (ray head already running and workers joined):
  python3 distributed_toy_transformer.py
"""

import ray
import numpy as np
import time
import itertools
import argparse
import sys

# ----------------------------
# Simple model hyperparameters
# ----------------------------
EMBED_DIM = 128       # embedding dim (small)
VOCAB_SIZE = 10000    # toy vocab
NUM_BLOCKS = 12       # total transformer blocks
HEADS = 4
MLP_DIM = 4 * EMBED_DIM
MAX_LEN = 128

# ----------------------------
# Simple tokenizer (toy)
# ----------------------------
def simple_tokenize(text, max_len=MAX_LEN):
    # whitespace tokenization and hash to small vocab
    toks = [abs(hash(t)) % VOCAB_SIZE for t in text.strip().split()][:max_len]
    if len(toks) == 0:
        toks = [0]
    return np.array(toks, dtype=np.int32)

def simple_detokenize(indices):
    # just join token ids as text for demonstration
    return " ".join([f"<t{i}>" for i in indices.tolist()])

# ----------------------------
# Utility: create small init params
# ----------------------------
def init_linear(in_dim, out_dim):
    return {
        "W": np.random.randn(in_dim, out_dim).astype(np.float32) * (1.0 / np.sqrt(in_dim)),
        "b": np.zeros((out_dim,), dtype=np.float32)
    }

def linear(x, params):
    return x @ params["W"] + params["b"]

def gelu(x):
    return 0.5 * x * (1 + np.tanh(np.sqrt(2/np.pi) * (x + 0.044715 * x**3)))

# ----------------------------
# Transformer block (toy) - implemented on worker side
# ----------------------------
def block_forward(x, params):
    # x: [seq, dim]
    # Self-attention (vanilla, unoptimized)
    q = linear(x, params["q"])
    k = linear(x, params["k"])
    v = linear(x, params["v"])
    # split heads
    seq, dim = q.shape
    head_dim = dim // HEADS
    qh = q.reshape(seq, HEADS, head_dim)
    kh = k.reshape(seq, HEADS, head_dim)
    vh = v.reshape(seq, HEADS, head_dim)
    # scaled dot-product
    scores = np.einsum("shd,thd->sht", qh, kh) / np.sqrt(head_dim)
    # softmax across keys (t axis)
    probs = np.exp(scores - np.max(scores, axis=2, keepdims=True))
    probs = probs / (np.sum(probs, axis=2, keepdims=True) + 1e-9)
    # attention
    att = np.einsum("sht,thd->shd", probs, vh)
    att = att.reshape(seq, dim)
    att_out = linear(att, params["o"])
    x = x + att_out  # residual
    # MLP
    mlp_out = linear(gelu(linear(x, params["mlp1"])), params["mlp2"])
    x = x + mlp_out
    return x

# ----------------------------
# Ray actor that holds some blocks
# ----------------------------
@ray.remote
class ShardWorker:
    def __init__(self, shard_id: int, blocks_idx: list, embed_dim=EMBED_DIM):
        np.random.seed(42 + shard_id)
        self.shard_id = shard_id
        self.blocks_idx = blocks_idx  # list of block indices this worker holds
        # create params per block
        self.params = {}
        for i in blocks_idx:
            self.params[i] = {
                "q": init_linear(embed_dim, embed_dim),
                "k": init_linear(embed_dim, embed_dim),
                "v": init_linear(embed_dim, embed_dim),
                "o": init_linear(embed_dim, embed_dim),
                "mlp1": init_linear(embed_dim, MLP_DIM),
                "mlp2": init_linear(MLP_DIM, embed_dim)
            }

    def forward_blocks(self, start_block, x_np):
        """
        Process blocks starting from start_block up to the worker's last block (if included).
        x_np: numpy array [seq, dim]
        returns: processed activation (numpy)
        """
        x = x_np.astype(np.float32)
        # process only the intersection: blocks from start_block upward that this worker owns
        for b in sorted(self.blocks_idx):
            if b < start_block:
                continue
            # run block
            x = block_forward(x, self.params[b])
        # return activations
        return x

    def get_info(self):
        return {"shard_id": self.shard_id, "blocks": self.blocks_idx}

# ----------------------------
# Master-side model head & embeddings
# ----------------------------
class MasterModel:
    def __init__(self, workers, blocks_per_worker):
        # create embedding & lm head locally
        self.embed_W = np.random.randn(VOCAB_SIZE, EMBED_DIM).astype(np.float32) * 0.02
        self.pos_embed = np.random.randn(MAX_LEN, EMBED_DIM).astype(np.float32) * 0.01
        self.lm_head = np.random.randn(EMBED_DIM, VOCAB_SIZE).astype(np.float32) * 0.02
        self.workers = workers
        self.blocks_per_worker = blocks_per_worker

    def embed(self, token_ids):
        seq = len(token_ids)
        emb = self.embed_W[token_ids] + self.pos_embed[:seq]
        return emb  # [seq, dim]

    def decode_logits(self, x):
        # x: [seq, dim] -> use last token embedding to get logits
        last = x[-1]  # [dim]
        logits = last @ self.lm_head
        # greedy decode index
        idx = int(np.argmax(logits))
        return idx, logits

# ----------------------------
# Orchestration: run single forward across shards
# ----------------------------
def orchestrate_forward(master_model: MasterModel, token_ids, shard_actors, blocks_map):
    # 1) master embedding
    emb = master_model.embed(token_ids)  # [seq, dim]
    x = emb
    # 2) pipeline through each worker in order
    for worker_idx, actor in enumerate(shard_actors):
        # determine the next block index to start from
        # compute smallest block index in that worker
        start_block = min(blocks_map[worker_idx])
        # call worker.forward_blocks with current activation
        # convert to list for ray compatibility
        # remote call
        x = ray.get(actor.forward_blocks.remote(start_block, x))
    # 3) master decodes logits
    idx, logits = master_model.decode_logits(x)
    return idx, logits

# ----------------------------
# Main: initialize cluster, shards, run interactive loop
# ----------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", default="auto", help="ray address (auto when running on head)")
    parser.add_argument("--num_blocks", type=int, default=NUM_BLOCKS)
    parser.add_argument("--embed_dim", type=int, default=EMBED_DIM)
    args = parser.parse_args()

    # connect to ray
    ray.init(address=args.address)
    nodes = [n for n in ray.nodes() if n["Alive"]]
    # exclude head node (master) by detecting head resource if present, otherwise assume first is head
    # We'll create shards on non-head nodes only.
    workers_nodes = []
    for n in nodes:
        # node["Resources"] often contains "node:<ip>" or "CPU"
        if "head" in n["Resources"]:
            continue
        # include nodes with CPU > 0, and that are not head
        workers_nodes.append(n)

    if len(workers_nodes) == 0:
        print("No worker nodes discovered (excluding head). Exiting.")
        sys.exit(1)

    # Determine how to split blocks across workers
    num_workers = len(workers_nodes)
    num_blocks = args.num_blocks
    blocks = list(range(num_blocks))
    # roughly even split
    blocks_per_worker = [blocks[i::num_workers] for i in range(num_workers)]

    # create one shard actor per worker (use placement to prefer remote nodes)
    shard_actors = []
    blocks_map = {}
    for i, b_indices in enumerate(blocks_per_worker):
        # create actor (no explicit node placement here — Ray will place them on workers)
        actor = ShardWorker.remote(i, b_indices)
        shard_actors.append(actor)
        blocks_map[i] = b_indices

    # create master model
    master_model = MasterModel(shard_actors, blocks_per_worker)

    print(f"Created {len(shard_actors)} shard actors. Blocks per worker: {blocks_per_worker}")
    print("Interactive mode. Type a prompt. Type 'quit' to exit.")

    while True:
        prompt = input("\nPrompt> ")
        if prompt.strip().lower() in ("quit", "exit"):
            break
        token_ids = simple_tokenize(prompt)
        t0 = time.time()
        idx, logits = orchestrate_forward(master_model, token_ids, shard_actors, blocks_map)
        t1 = time.time()
        elapsed = t1 - t0
        tps = (len(token_ids) / elapsed) if elapsed > 0 else 0.0
        response = simple_detokenize(np.array([idx]))
        print("\n--- Response (toy) ---")
        print(response)
        print(f"[Stats] Tokens processed: {len(token_ids)} | Elapsed: {elapsed:.3f}s | TPS: {tps:.2f}")
        print(f"Active shards: {len(shard_actors)} | Blocks map: {blocks_map}")

    # cleanup
    ray.shutdown()

if __name__ == "__main__":
    main()
