import os
import json
import time
import threading
import tracemalloc

from pathlib import Path
from contextlib import contextmanager


class ProfileResult:
    def __init__(self):
        self.time_elapsed = 0
        self.mem_peak = 0
        self.mem_measurements = []

    def __str__(self):
        return (
            f"ProfileResult(time_elapsed={self.time_elapsed}, "
            f"mem_peak={self.mem_peak}, "
            f"mem_measurements={self.mem_measurements})"
        )


@contextmanager
def profile(constraint_file_path: str, num_runs: str, sampling_interval=0.01):
    """
    Context manager to measure execution time and memory usage precisely.

    Returns a ProfileResult object with statistics.
    """
    result = ProfileResult()
    mem_stats = []
    start_time = time.perf_counter()

    results = []
    constraint_file_path: Path = Path(constraint_file_path)
    output_file_path = (
        constraint_file_path.parent
        / f"{constraint_file_path.stem}_difficulty_{num_runs}_result.json"
    )

    if os.path.isfile(output_file_path):
        with open(output_file_path, "r") as f:
            results = json.load(f)

    # Sample memory usage until code block is finished
    stop_event = {"stop": False}

    tracemalloc.start()

    def sampler():
        while not stop_event["stop"]:
            current, _ = tracemalloc.get_traced_memory()
            mem_stats.append(current)
            time.sleep(sampling_interval)

    t = threading.Thread(target=sampler)
    t.start()

    try:
        yield result  # result object becomes available after code block is finished
    finally:
        end_time = time.perf_counter()
        stop_event["stop"] = True
        t.join()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results.append(
            {
                "mem_peak": peak,
                "mem_measurements": mem_stats,
                "time_elapsed": end_time - start_time,
            }
        )

        with open(output_file_path, "w") as f:
            json.dump(results, f)

        result.mem_peak = peak
        result.mem_measurements = mem_stats
        result.time_elapsed = end_time - start_time
