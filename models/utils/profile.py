import json
import time
import threading
import tracemalloc
import pynvml

from pathlib import Path
from contextlib import contextmanager


class ProfileResult:
    def __init__(self, file_path: str):
        self.results = []
        self.file_path = file_path

    def add_result(self, result_entry):
        self.results.append(result_entry)

    def write_results(self, is_valid: bool, score: float):
        if self.results:
            self.results[-1]["is_valid"] = is_valid
            self.results[-1]["score"] = score
        with open(self.file_path, "w") as f:
            json.dump(self.results, f, indent=4)


@contextmanager
def profile(
    constraint_file_path: str, num_runs: str, sampling_interval=0.01, vram=False
):
    """
    Context manager to measure execution time, RAM, and optionally VRAM usage.
    """
    constraint_file_path = Path(constraint_file_path)
    output_file_path = (
        constraint_file_path.parent
        / f"{constraint_file_path.stem}_difficulty_{num_runs}_result.json"
    )

    result = ProfileResult(output_file_path)

    # Existing results loading logic
    if output_file_path.exists():
        try:
            with open(output_file_path, "r") as f:
                result.results = json.load(f)
        except json.JSONDecodeError:
            result.results = []

    # Sampling storage
    mem_stats = []
    vram_stats = []
    stop_event = threading.Event()

    # Initialize NVML if VRAM tracking is requested
    nvml_handles = []
    if vram:
        try:
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            for i in range(device_count):
                nvml_handles.append(pynvml.nvmlDeviceGetHandleByIndex(i))
        except Exception as e:
            print(f"Warning: Could not initialize NVML for VRAM profiling: {e}")
            vram = False

    tracemalloc.start()
    start_time = time.perf_counter()

    def sampler():
        while not stop_event.is_set():
            loop_start = time.perf_counter()

            # Sample System RAM
            current, _ = tracemalloc.get_traced_memory()
            mem_stats.append(current)

            # Sample VRAM (Sum of all GPUs)
            if vram:
                total_used = 0
                for handle in nvml_handles:
                    info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    total_used += info.used
                vram_stats.append(total_used)

            # Precise timing for 0.01s interval
            elapsed = time.perf_counter() - loop_start
            time.sleep(max(0, sampling_interval - elapsed))

    t = threading.Thread(target=sampler, daemon=True)
    t.start()

    try:
        yield result
    finally:
        stop_event.set()
        t.join()

        end_time = time.perf_counter()
        _, peak_ram = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Compile metrics for this specific run
        run_data = {
            "time_elapsed": end_time - start_time,
            "mem_peak": peak_ram,
            "mem_measurements": mem_stats,
        }

        if vram:
            run_data["vram_peak"] = max(vram_stats) if vram_stats else 0
            run_data["vram_measurements"] = vram_stats
            pynvml.nvmlShutdown()

        result.add_result(run_data)
