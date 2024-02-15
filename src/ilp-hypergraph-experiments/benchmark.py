import time
from tqdm import tqdm


def mean(values):
    return 1.0 * sum(values) / len(values)


def var(values):
    m = mean(values)
    return sum((xi - m) ** 2 for xi in values) / len(values)


def benchmark(func: callable, *func_args, n: int = 10, **func_kwargs):
    print("Benchmark", func.__name__)
    times: list[int] = []
    for _ in tqdm(range(n)):
        tic = time.perf_counter()
        func(*func_args, **func_kwargs)
        toc = time.perf_counter()
        times.append(toc - tic)
    m = mean(times)
    variance = var(times)
    return f"Benchmarked function '{func.__name__}'. Mean: {m}, Variance: {variance}, Range: {min(times)}-{max(times)}"
