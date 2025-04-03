import multiprocessing
import time
import threading
import codecs
from datetime import datetime


def log_entry(message, log_file):
    with open(log_file, 'a') as f:
        f.write(message + '\n')


def process_a(queue_ab, pipe_ab, exit_event, log_file):
    while not exit_event.is_set():
        if not queue_ab.empty():
            message = queue_ab.get()
            timestamp = datetime.now().strftime('%H:%M:%S')
            if message == "exit":
                log_entry(f"[A][{timestamp}] exit", log_file)
                exit_event.set()
                break

            log_entry(f"[A][{timestamp}] delivered: {message}", log_file)
            processed_message = message.lower()
            time.sleep(5)
            pipe_ab.send(processed_message)
            log_entry(f"[A][{timestamp}] sent to B: {processed_message}", log_file)


def process_b(pipe_ab, queue_ba, exit_event, log_file):
    while not exit_event.is_set():
        if pipe_ab.poll(timeout=1):
            message = pipe_ab.recv()
            timestamp = datetime.now().strftime('%H:%M:%S')
            if message == "exit":
                log_entry(f"[B][{timestamp}] exit", log_file)
                exit_event.set()
                break

            encoded_message = codecs.encode(message, 'rot13')
            print(f"[B][{timestamp}] {encoded_message}")
            log_entry(f"[B][{timestamp}] Sent: {encoded_message}", log_file)
            queue_ba.put(encoded_message)


def main():
    log_file = "log.txt"
    open(log_file, 'w').close()

    queue_main_to_a = multiprocessing.Queue()
    queue_b_to_main = multiprocessing.Queue()
    pipe_a_to_b, pipe_b_to_a = multiprocessing.Pipe()
    exit_event = multiprocessing.Event()

    proc_a = multiprocessing.Process(
        target=process_a,
        args=(queue_main_to_a, pipe_a_to_b, exit_event, log_file)
    )
    proc_b = multiprocessing.Process(
        target=process_b,
        args=(pipe_b_to_a, queue_b_to_main, exit_event, log_file)
    )

    proc_a.start()
    proc_b.start()

    def read_from_b():
        while not exit_event.is_set():
            if not queue_b_to_main.empty():
                message = queue_b_to_main.get()
                timestamp = datetime.now().strftime('%H:%M:%S')
                log_entry(f"[main][{timestamp}] get from B: {message}", log_file)
                print(f"[main][{timestamp}] Get message: {message}")

    reader_thread = threading.Thread(target=read_from_b, daemon=True)
    reader_thread.start()

    try:
        while True:
            user_input = input(f"[main][{datetime.now().strftime('%H:%M:%S')}] Input: ")
            timestamp = datetime.now().strftime('%H:%M:%S')
            log_entry(f"[main][{timestamp}] Input: {user_input}", log_file)
            queue_main_to_a.put(user_input)

            if user_input == "exit":
                log_entry(f"[main][{timestamp}] exit", log_file)
                exit_event.set()
                break
    except KeyboardInterrupt:
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry(f"[main][{timestamp}] (Ctrl+C)", log_file)
        exit_event.set()

    proc_a.join(timeout=2)
    proc_b.join(timeout=2)

    if proc_a.is_alive():
        proc_a.terminate()
    if proc_b.is_alive():
        proc_b.terminate()

    log_entry(f"[main][{datetime.now().strftime('%H:%M:%S')}] End", log_file)

if __name__ == "__main__":
    main()