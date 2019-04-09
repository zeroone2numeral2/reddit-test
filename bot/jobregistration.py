import logging
from importlib import import_module
from collections import namedtuple

from .updater import job_queue
from .registration import Registration

logger = logging.getLogger(__name__)


Job = namedtuple('Job', ['runner', 'callback', 'args', 'kwargs'])


class RUNNERS:
    run_once = 'run_once'
    run_repeating = 'run_repeating'
    run_daily = 'run_daily'


class Jobs(Registration):
    list = []
    job_queue = None

    @classmethod
    def hook(cls, dispatcher, job_queue):
        cls.dispatcher = dispatcher
        cls.job_queue = job_queue

    @staticmethod
    def _fetch_valid_callbacks(import_path, callbacks_whitelist=None):
        valid_jobs = list()

        try:
            module = import_module(import_path)
            names_list = list(vars(module).keys()) if callbacks_whitelist is None else callbacks_whitelist
            # logger.info('functions to test from %s: %s', import_path, ', '.join(names_list))
            for name in names_list:
                jobs_tuple_list = getattr(module, name)  # lista perchè @Plugin.add() genera una lista (stack di decorators)
                if isinstance(jobs_tuple_list, list):
                    for job_tuple in jobs_tuple_list:
                        if isinstance(job_tuple, Job):
                            logger.info('job %s.%s will be loaded', import_path, job_tuple.callback.__name__)
                            valid_jobs.append(job_tuple)
                        else:
                            logger.info('job %s.%s skipped because not an instance of Job', import_path, type(job_tuple).__name__)
        except Exception as e:
            logger.error('error while loading jobs from %s: %s', import_path, str(e), exc_info=False)

        return valid_jobs

    @staticmethod
    def add(runner, *args, **kwargs):
        def decorator(func):
            return_list = list()
            if isinstance(func, list):
                # in caso vengano usati più decorator @Jobs.add() alla stessa funzione
                return_list.extend(func)
                func = func[0].callback  # ricava la callback, è la stessa per ogni elemento nella lista

            logger.info('converting function "%s" to job "%s" (decorators stack depth: %d)', func.__name__, runner, len(return_list))

            job_tuple = Job(runner=runner, callback=func, args=args, kwargs=kwargs)
            return_list.append(job_tuple)

            return return_list

        return decorator

    @classmethod
    def register(cls):
        if not cls.dispatcher or not cls.job_queue:
            raise ValueError('a dispatcher and a job_queue must be set first with Jobs.hook()')

        for job_tuple in cls.list:
            if job_tuple.runner == RUNNERS.run_once:
                job_queue.run_once(callback=job_tuple.callback, *job_tuple.args, **job_tuple.kwargs)
            elif job_tuple.runner == RUNNERS.run_repeating:
                job_queue.run_repeating(callback=job_tuple.callback, *job_tuple.args, **job_tuple.kwargs)
            elif job_tuple.runner == RUNNERS.run_daily:
                job_queue.run_daily(callback=job_tuple.callback, *job_tuple.args, **job_tuple.kwargs)
