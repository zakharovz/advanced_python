import time
import threading
import multiprocessing

def fib(n):
    if n <= 1:
        return n
    else:
        return fib(n - 1) + fib(n - 2)

def run_sync(n, times=10):
    start = time.time()
    for _ in range(times):
        fib(n)
    end = time.time()
    return end - start

def run_threads(n, times=10):
    threads = []
    start = time.time()
    for _ in range(times):
        thread = threading.Thread(target=fib, args=(n,))
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    end = time.time()
    return end - start

def run_processes(n, times=10):
    processes = []
    start = time.time()
    for _ in range(times):
        process = multiprocessing.Process(target=fib, args=(n,))
        process.start()
        processes.append(process)
    for process in processes:
        process.join()
    end = time.time()
    return end - start

if __name__ == "__main__":
    n = 35
    times = 10

    sync_time = run_sync(n, times)
    threads_time = run_threads(n, times)
    processes_time = run_processes(n, times)

    with open("fibonacci.txt", "w") as f:
        f.write(f"Синхронный запуск (10 раз): {sync_time:.2f} сек\n")
        f.write(f"Запуск в 10 потоках: {threads_time:.2f} сек\n")
        f.write(f"Запуск в 10 процессах: {processes_time:.2f} сек\n")