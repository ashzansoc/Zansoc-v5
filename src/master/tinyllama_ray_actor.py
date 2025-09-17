import ray
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import time

@ray.remote
class TinyLlamaActor:
    def __init__(self):
        self.model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        print(f"TinyLlama model loaded on {self.device}")

    def generate_response(self, prompt, max_new_tokens=50):
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        start_time = time.time()
        outputs = self.model.generate(**inputs, max_new_tokens=max_new_tokens, pad_token_id=self.tokenizer.eos_token_id)
        end_time = time.time()
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Calculate tokens per second
        input_tokens = inputs.input_ids.shape[1]
        output_tokens = outputs.shape[1] - input_tokens
        duration = end_time - start_time
        tps = output_tokens / duration if duration > 0 else 0
        
        return response, tps

if __name__ == "__main__":
    # This part is for local testing/demonstration of the actor
    # In a real Ray cluster, the actor would be initialized by ray.remote().remote()
    # and its methods called directly.
    pass
    # Ray should be initialized by the master application. Uncomment if running tinyllama_ray_actor.py standalone.

    # Example of how to create and use the actor
    # actor_handle = TinyLlamaActor.remote()
    # prompt = "Once upon a time,"
    # response, tps = ray.get(actor_handle.generate_response.remote(prompt))
    # print(f"Prompt: {prompt}")
    # print(f"Response: {response}")
    # print(f"Tokens per second: {tps:.2f}")

    # ray.shutdown()