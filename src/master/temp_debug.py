import ray
import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def test_ray_env():
    logger.info("Attempting to initialize Ray...")
    if ray.is_initialized():
        ray.shutdown()

    base_path = Path(__file__).parent.parent.parent
    site_packages_path = os.path.join(base_path, 'venv', 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
    requirements_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../requirements.txt"))

    runtime_env = {"pip": requirements_path, "env_vars": {"PYTHONPATH": site_packages_path}}
    logger.info(f"Using runtime_env: {runtime_env}")

    ray.init(address='auto', runtime_env=runtime_env)
    logger.info("Ray initialized successfully with custom runtime_env.")

    @ray.remote
    class TorchTestActor:
        def __init__(self):
            self.torch_available = False
            try:
                import torch
                self.torch_available = True
                logger.info(f"Torch version on worker: {torch.__version__}")
            except ImportError as e:
                logger.error(f"Torch not found on worker: {e}")
            except Exception as e:
                logger.error(f"Other error importing torch on worker: {e}")

        def check_torch(self):
            return self.torch_available

    logger.info("Creating TorchTestActor...")
    actor = TorchTestActor.remote()
    logger.info("Calling check_torch on actor...")
    torch_status = ray.get(actor.check_torch.remote())
    logger.info(f"Torch available on worker: {torch_status}")

    ray.shutdown()
    logger.info("Ray shutdown.")

if __name__ == '__main__':
    test_ray_env()