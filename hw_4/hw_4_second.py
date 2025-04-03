import math
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from multiprocessing import cpu_count
from functools import partial

def compute_part(f, a, step, start, partial_iter):
    local_a = a + start * step
    local_b = local_a + partial_iter * step
    acc = 0
    for i in range(partial_iter):
        x = local_a + i * step
        acc += f(x) * step
    return acc

def integrate(f, a, b, *, n_jobs=1, n_iter=10000000):
    step = (b - a) / n_iter
    partial_iter = n_iter // n_jobs

    worker = partial(compute_part, f, a, step, partial_iter=partial_iter)

    with (ThreadPoolExecutor if n_jobs == 1 else ProcessPoolExecutor)(max_workers=n_jobs) as executor:
        futures = []
        for start in range(0, n_iter, partial_iter):
            futures.append(executor.submit(worker, start))
        total = sum(f.result() for f in futures)

    return total

if __name__ == "__main__":
    cpu_num = cpu_count()
    n_jobs_list = list(range(1, cpu_num * 2 + 1))
    results = []

    for n_jobs in n_jobs_list:
        start = time.time()
        integrate(math.cos, 0, math.pi / 2, n_jobs=n_jobs)
        thread_time = time.time() - start

        start = time.time()
        integrate(math.cos, 0, math.pi / 2, n_jobs=n_jobs)
        process_time = time.time() - start

        results.append((n_jobs, thread_time, process_time))

    with open("integrate.txt", "w") as f:
        f.write("n_jobs\tThreadPoolExecutor\tProcessPoolExecutor\n")
        for n_jobs, thread_time, process_time in results:
            f.write(f"{n_jobs}\t{thread_time:.4f}\t\t\t{process_time:.4f}\n")