from concurrent.futures import ThreadPoolExecutor


class MonitoredThreadPoolExecutor(ThreadPoolExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._running_workers = 0

    def submit(self, *args, **kwargs):
        future = super().submit(*args, **kwargs)
        self._running_workers += 1
        future.add_done_callback(self._worker_is_done)
        return future

    def _worker_is_done(self, future):
        self._running_workers -= 1

    def get_pool_usage(self):
        return self._running_workers
