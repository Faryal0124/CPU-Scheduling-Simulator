#scheduler.py
from collections import deque #nsertion/removal from BOTH ends efficiently.

class Scheduler:
    def __init__(self):
        self.current_algorithm = "FCFS"
        self.time_quantum = 4
        self.num_mlfq_queues = 3
        self.mlfq_time_quanta = [2, 4, 8]
        self.aging_threshold = 20 #Used to PREVENT STARVATION.
        self.aging_amount = 1
        self.mlfq_queues = [deque() for _ in range(self.num_mlfq_queues)] #Creates separate queue for each MLFQ level.
        self.mlfq_priorities = list(range(self.num_mlfq_queues))
        self.rr_queue = deque()
        self.current_process = None
        self.current_time = 0

    # ── Configuration ────────────────────────────────────────────────────────

    def reconfigure_mlfq(self, num_queues=None, time_quanta=None,
                          aging_threshold=None, aging_amount=None): #dynamically updates the MLFQ configuration while preserving existing processes.”
        if num_queues is not None and num_queues != self.num_mlfq_queues:
            all_procs = [p for q in self.mlfq_queues for p in q]
            self.num_mlfq_queues = num_queues
            self.mlfq_queues = [deque() for _ in range(num_queues)]
            self.mlfq_priorities = list(range(num_queues))
            self.mlfq_time_quanta = (time_quanta or [2**i for i in range(num_queues)])[:num_queues] #If user gives custom quanta:use them.Otherwise:automatically generate
            for p in all_procs:
                lvl = min(getattr(p, 'current_queue_level', 0), num_queues - 1)
                p.current_queue_level = lvl
                p.waiting_since = self.current_time
                self.mlfq_queues[lvl].append(p)
        elif time_quanta is not None:
            for i in range(min(len(time_quanta), self.num_mlfq_queues)):
                self.mlfq_time_quanta[i] = time_quanta[i]
        if aging_threshold and aging_threshold > 0:
            self.aging_threshold = aging_threshold
        if aging_amount and aging_amount > 0:
            self.aging_amount = aging_amount

    def get_mlfq_config(self):
        return {
            'num_queues': self.num_mlfq_queues,
            'time_quanta': self.mlfq_time_quanta.copy(),
            'priorities': self.mlfq_priorities.copy(),
            'aging_threshold': self.aging_threshold,
            'aging_amount': self.aging_amount,
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    def get_ready_processes(self, processes, current_time): #returns processes ready for execution.
        return [p for p in processes
                if p.arrival_time <= current_time
                and p.remaining_time > 0
                and p.state == "Ready"]

    # ── Preemption check ─────────────────────────────────────────────────────

    def should_preempt(self, algorithm, current_process, ready_processes):
        if not current_process or not ready_processes:
            return False, None
        if algorithm == "SRTF (Preemptive)":
            best = min(ready_processes, key=lambda p: p.remaining_time)
            if best.remaining_time < current_process.remaining_time:
                return True, best
        elif algorithm == "Priority (Preemptive)":
            best = min(ready_processes, key=lambda p: p.priority)
            if best.priority < current_process.priority:
                return True, best
        return False, None

    # ── Per-algorithm selection ──────────────────────────────────────────────

    def get_next_process_fcfs(self, processes, t):
        ready = self.get_ready_processes(processes, t)
        return min(ready, key=lambda p: p.arrival_time) if ready else None

    def get_next_process_sjf(self, processes, t, preemptive=False):
        ready = self.get_ready_processes(processes, t)
        if not ready:
            return None
        key = (lambda p: p.remaining_time) if preemptive else (lambda p: p.burst_time)
        return min(ready, key=key)

    def get_next_process_priority(self, processes, t, preemptive=False):
        ready = self.get_ready_processes(processes, t)
        return min(ready, key=lambda p: p.priority) if ready else None

    def get_next_process_rr(self, processes, t):
        ready = self.get_ready_processes(processes, t)
        for p in ready:
            if p not in self.rr_queue and p != self.current_process:
                self.rr_queue.append(p)
        return self.rr_queue.popleft() if self.rr_queue else None

    # ── MLFQ ─────────────────────────────────────────────────────────────────

    def _apply_aging(self, current_time):
        for lvl in range(1, self.num_mlfq_queues):
            q = self.mlfq_queues[lvl]
            for p in list(q):
                p.waiting_since = getattr(p, 'waiting_since', current_time)
                if current_time - p.waiting_since >= self.aging_threshold:
                    q.remove(p)
                    target = max(0, lvl - self.aging_amount)
                    p.current_queue_level = target
                    p.waiting_since = current_time
                    self.mlfq_queues[target].append(p)

    def get_next_process_mlfq(self, processes, t):
        # Initialise waiting_since for queued processes
        for lvl, q in enumerate(self.mlfq_queues):
            for p in q:
                if not hasattr(p, 'waiting_since'):
                    p.waiting_since = t
        self._apply_aging(t)
        # Enqueue new arrivals in Q0
        in_queues = {p for q in self.mlfq_queues for p in q}
        for p in self.get_ready_processes(processes, t):
            if p not in in_queues and p != self.current_process:
                p.current_queue_level = 0
                p.waiting_since = t
                self.mlfq_queues[0].append(p)
        # Pick from highest-priority non-empty queue
        for i, q in enumerate(self.mlfq_queues):
            if q:
                p = q.popleft()
                p.current_queue_level = i
                if not hasattr(p, 'quantum_used'):
                    p.quantum_used = 0
                p.waiting_since = t
                return p
        return None

    # ── Main dispatch ────────────────────────────────────────────────────────

    def get_next_process(self, processes, current_time, algorithm, current_process=None):
        self.current_process = current_process
        self.current_time = current_time
        dispatch = {
            "FCFS":                   lambda: self.get_next_process_fcfs(processes, current_time),
            "SJF (Non-Preemptive)":   lambda: self.get_next_process_sjf(processes, current_time),
            "SRTF (Preemptive)":      lambda: self.get_next_process_sjf(processes, current_time, True),
            "Priority (Non-Preemptive)": lambda: self.get_next_process_priority(processes, current_time),
            "Priority (Preemptive)":  lambda: self.get_next_process_priority(processes, current_time, True),
            "Round Robin":            lambda: self.get_next_process_rr(processes, current_time),
            "MLFQ":                   lambda: self.get_next_process_mlfq(processes, current_time),
        }
        return dispatch.get(algorithm, lambda: None)()

    def reset(self):
        self.mlfq_queues = [deque() for _ in range(self.num_mlfq_queues)]
        self.rr_queue = deque()
        self.current_process = None