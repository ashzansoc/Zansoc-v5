import ray
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import torch
import time

MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# Configuration for 4-bit quantization
QUANTIZATION_CONFIG = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=False,
)

@ray.remote
class TinyLlamaActor:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.tokenizer = None
        self.model = None

    def load_model(self):
        if self.model is None or self.tokenizer is None:
            print("TinyLlamaActor: Starting model and tokenizer download...")
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
                self.model = AutoModelForCausalLM.from_pretrained(
                    MODEL_NAME,
                    quantization_config=QUANTIZATION_CONFIG,
                    device_map={" ": 0},  # all layers on Cuda 0
                )
                print(f"TinyLlamaActor: TinyLlama model and tokenizer loaded on {self.device}")
            except Exception as e:
                print(f"TinyLlamaActor: Error loading model: {e}")
                raise e

    @ray.method(num_returns=1)
    def generate_response(self, prompt: str, max_new_tokens: int = 50) -> str:
        print(f"TinyLlamaActor: Generating response for prompt: {prompt[:50]}...")
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            start_time = time.time()
            outputs = self.model.generate(**inputs, max_new_tokens=max_new_tokens, pad_token_id=self.tokenizer.eos_token_id)
        except Exception as e:
            print(f"TinyLlamaActor: Error during response generation: {e}")
            return "Error generating response.", 0
        end_time = time.time()
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Calculate tokens per second
        input_tokens = inputs.input_ids.shape[1]
        output_tokens = outputs.shape[1] - input_tokens
        duration = end_time - start_time
        tps = output_tokens / duration if duration > 0 else 0
        
        print(f"TinyLlamaActor: Response generated in {duration:.2f} seconds, TPS: {tps:.2f}")
        return response, tps

if __name__ == "__main__":
    if not ray.is_initialized():
        pass

    # In a real scenario, the model would be put into the object store by a driver script
    # and its object references passed to the actors.
    # For this example, we simulate that logic within the actor for demonstration purposes.
    # However, a better approach is to have a centralized function to put objects into store.
    
    # Example usage (commented out as it's typically driven by a separate script)
    # actor_handle = TinyLlamaActor.remote()
    # prompt = "Once upon a time,"
    # response, tps = ray.get(actor_handle.generate_response.remote(prompt))
    # print(f"Prompt: {prompt}")
    # print(f"Response: {response}")
    # print(f"Tokens per second: {tps:.2f}")

    # ray.shutdown() # Don't shutdown if other parts of the system rely on Ray