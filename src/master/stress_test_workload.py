import ray
import time
import math

@ray.remote
def cpu_intensive_task(duration_seconds):
    start_time = time.time()
    while True:
        # Perform a computationally intensive operation
        _ = [math.sqrt(i) for i in range(1_000_000)]
        if time.time() - start_time >= duration_seconds:
            break
    return f"CPU intensive task completed in {duration_seconds} seconds."

if __name__ == "__main__":
    if not ray.is_initialized():
        ray.init(address='auto', dashboard_port=8265, ignore_reinit_error=True)
    print("Ray initialized successfully for stress testing.")

    # Number of tasks to launch (can be adjusted to scale the load)
    num_tasks = 200
    # Duration for each CPU intensive task in seconds
    task_duration = 10 # Each task will run for 10 seconds

    print(f"Launching {num_tasks} CPU intensive tasks, each running for {task_duration} seconds.")

    # Launch multiple tasks in parallel
    results = [cpu_intensive_task.remote(task_duration) for _ in range(num_tasks)]

    print("Tasks launched. Monitoring Ray Dashboard for CPU utilization.")
    print("Waiting for tasks to complete...")

    # Retrieve results to ensure tasks complete (this will block until all are done)
    for i, result in enumerate(ray.get(results)):
        print(f"Task {i+1}: {result}")

    print("All CPU intensive tasks completed.")

    # Keep the script running for a bit to allow monitoring before shutdown, or remove if not needed.
    # time.sleep(5) 

    # Uncomment the following line if you want to shut down Ray after the test
    # ray.shutdown()