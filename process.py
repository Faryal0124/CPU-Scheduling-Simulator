
# process.py - Defines the Process data model used throughout the simulator
import random

class Process:
    def __init__(self, pid, arrival_time, burst_time, priority=0, is_io_bound=False):
        # Core scheduling attributes
        self.pid = pid
        self.arrival_time = arrival_time
        self.burst_time = burst_time
        self.original_burst_time = burst_time   # kept so reset() can restore original
        self.remaining_time = burst_time
        self.priority = priority
        self.is_io_bound = is_io_bound

        # Metrics accumulated during simulation
        self.waiting_time = 0
        self.turnaround_time = 0
        self.response_time = -1     # -1 means "not yet responded"
        self.completion_time = 0
        self.start_time = -1        # -1 means "not yet started"

        # State tracking
        self.state = "Waiting"      # Waiting | New | Ready | Running | Terminated
        self.last_arrival_update = arrival_time
        self.io_remaining = 0 if not is_io_bound else random.randint(2, 6)
        self.in_ready_queue = False

    def __lt__(self, other):
        # Allows priority-queue comparisons; lower number = higher priority
        return self.priority < other.priority

    def modify_process(self, arrival_time=None, burst_time=None, priority=None):
        """Dynamically update process parameters during a running simulation."""
        if arrival_time is not None and arrival_time >= 0:
            self.arrival_time = arrival_time
            self.last_arrival_update = arrival_time
        if burst_time is not None and burst_time > 0:
            self.burst_time = burst_time
            self.original_burst_time = burst_time
            if self.state != "Completed":
                self.remaining_time = burst_time    # apply new burst immediately
        if priority is not None:
            self.priority = priority

    def reset(self):
        """Restore process to its pre-simulation state (called on simulator reset)."""
        self.remaining_time = self.burst_time
        self.waiting_time = 0
        self.turnaround_time = 0
        self.response_time = -1
        self.completion_time = 0
        self.start_time = -1
        self.state = "Waiting"
        self.in_ready_queue = False
        self.__dict__.pop('quantum_used', None)     # remove MLFQ quantum tracker if present
