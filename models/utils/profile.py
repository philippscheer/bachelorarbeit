import time
import threading
import tracemalloc

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
def profile(sampling_interval=0.01):
    """
    Context manager to measure execution time and memory usage precisely.

    Returns a ProfileResult object with statistics.
    """
    result = ProfileResult()
    tracemalloc.start()
    start_time = time.perf_counter()

    mem_stats = []

    # Sample memory usage until code block is finished
    stop_event = {"stop": False}

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

        result.mem_peak = peak
        result.mem_measurements = mem_stats
        result.time_elapsed = end_time - start_time
