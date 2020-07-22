class JobResult:
    def __init__(self, posted_messages=0, posted_bytes=0.0):
        self.posted_messages = posted_messages
        self.posted_bytes = posted_bytes

    def inc_messages(self, posted_messages=1):
        self.posted_messages += posted_messages

    def inc_bytes(self, posted_bytes):
        self.posted_bytes += posted_bytes

    def increment(self, posted_messages=0, posted_bytes=0.0):
        self.posted_messages += posted_messages
        self.posted_bytes += posted_bytes

    def sum(self, job_result):
        self.posted_messages += job_result.posted_messages
        self.posted_bytes += job_result.posted_bytes

    def __add__(self, other):
        return JobResult(
            posted_messages=self.posted_messages + other.posted_messages,
            posted_bytes=self.posted_bytes + other.posted_bytes,
        )
