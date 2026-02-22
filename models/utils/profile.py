import os
import json
import time
import threading
import tracemalloc

from pathlib import Path
from contextlib import contextmanager


class ProfileResult:
    def __init__(self, file_path: str):
        self.time_elapsed = 0
        self.mem_peak = 0
        self.mem_measurements = []
        self.results = []
        self.file_path = file_path

    def __str__(self):
        return (
            f"ProfileResult(time_elapsed={self.time_elapsed}, "
            f"mem_peak={self.mem_peak}, "
            f"mem_measurements={self.mem_measurements})"
        )

    def add_result(self, result):
        self.results.append(result)

    def write_results(self, is_valid: bool, score: float):
        self.results[-1]["is_valid"] = is_valid
        self.results[-1]["score"] = score
        with open(self.file_path, "w") as f:
            json.dump(self.results, f)


@contextmanager
def profile(constraint_file_path: str, num_runs: str, sampling_interval=0.01):
    """
    Context manager to measure execution time and memory usage precisely.

    Returns a ProfileResult object with statistics.
    """
    constraint_file_path: Path = Path(constraint_file_path)
    output_file_path = (
        constraint_file_path.parent
        / f"{constraint_file_path.stem}_difficulty_{num_runs}_result.json"
    )

    result = ProfileResult(output_file_path)
    mem_stats = []
    start_time = time.perf_counter()

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

        result.add_result(
            {
                "mem_peak": peak,
                "mem_measurements": mem_stats,
                "time_elapsed": end_time - start_time,
            }
        )
