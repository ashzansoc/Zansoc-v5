import ray
import time

@ray.remote
def sample_task(x):
    time.sleep(1) # Simulate some work
    return x * x

if __name__ == "__main__":
    # ray.init(address="auto") # Connect to the existing Ray cluster - Ray should be initialized by the master application.

    # Submit a series of tasks
    results = []
    for i in range(100):
        results.append(sample_task.remote(i))

    # Get and print the results
    output = ray.get(results)
    print("Sample workload results:", output)

    # You can also check the Ray dashboard (usually at http://<master-ip>:8265) to see load distribution.