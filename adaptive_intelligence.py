
# adaptive_intelligence.py - AI engine that monitors the simulation and gives recommendations.
# Uses a two-phase approach:
#   - LIVE  : only fires critical starvation alerts during simulation (low noise)
#   - FINAL : algorithm suggestions + performance warnings shown at end-of-simulation

class AdaptiveIntelligence:
    def __init__(self):
        self.starving_processes = set()         # PIDs currently flagged as starving
        self.last_recommendation_time = -15     # throttles how often we collect suggestions
        self.stored_suggestions = []            # suggestions accumulated during simulation

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze_live(self, processes, current_time, current_algorithm, current_process):
        """Called every N ticks during simulation. Only returns critical starvation alerts
        to avoid flooding the feedback panel with noise."""
        if not processes:
            return []
        recs = []
        starving = self._check_starvation(processes, current_process)
        if starving:
            recs.append(('critical', starving, 'Round Robin or MLFQ'))
        # Quietly collect algorithm suggestions in the background for final report
        self._collect_suggestions(processes, current_algorithm, current_time)
        return recs

    def analyze_final(self, processes, current_time, current_algorithm):
        """Called once when simulation completes. Returns performance warnings
        and the best algorithm suggestion based on the full completed workload."""
        if not processes:
            return []
        recs = []
        warn = self._check_poor_performance(processes, current_algorithm)
        if warn:
            recs.append(('warn', warn, None))
        # Prefer a suggestion based on the final completed workload; fall back to live suggestion
        suggestion = self._get_best_final_suggestion(processes, current_algorithm)
        if not suggestion:
            suggestion = self._suggest_better_algorithm(processes, current_algorithm)
        if suggestion:
            recs.append(('info', suggestion, None))
        return recs

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _collect_suggestions(self, processes, current_algorithm, current_time):
        
        """Throttled: stores a suggestion at most once every 30 time units."""
        if current_time - self.last_recommendation_time >= 30:
            s = self._suggest_better_algorithm(processes, current_algorithm)
            
            if s and s not in self.stored_suggestions:
                self.stored_suggestions.append(s)
                
                if len(self.stored_suggestions) > 5:    # keep only the 5 most recent
                    self.stored_suggestions.pop(0)
            self.last_recommendation_time = current_time

    def _get_best_final_suggestion(self, processes, current_algorithm):
        """Picks the most appropriate algorithm based on the final completed workload mix."""
        done = [p for p in processes if p.state == "Terminated"]
        if not done:
            return None
        cpu = sum(1 for p in done if not p.is_io_bound)
        io  = sum(1 for p in done if p.is_io_bound)
        total = cpu + io
        if not total:
            return None
        io_ratio = io / total

        if io_ratio < 0.3:
            # Mostly CPU-bound: pick SJF vs SRTF based on burst time variance
            bursts = [p.burst_time for p in done]
            variance = max(bursts) / min(bursts) if min(bursts) > 0 else 1
            algo = "SJF" if variance < 3 else "SRTF"
            return f"Based on final workload ({cpu} CPU, {io} I/O) → {algo} recommended"
        if io_ratio <= 0.7:
            return f"Based on final mixed workload ({io} I/O, {cpu} CPU) → MLFQ recommended"
        return f"Based on final I/O-bound workload ({io_ratio*100:.0f}% I/O) → Round Robin (quantum 2-4) recommended"

    def _check_starvation(self, processes, current_process):
        """Returns a starvation message if any ready process has waited too long."""
        for p in processes:
            if p.state == "Ready" and p.waiting_time > 0:
                if p.waiting_time >= 40 and p.pid not in self.starving_processes:
                    self.starving_processes.add(p.pid)
                    return f"Process {p.pid} is STARVING (waited {p.waiting_time:.0f} units!)"
                elif p.waiting_time >= 20:
                    self.starving_processes.add(p.pid)
                    return f"{p.pid} waiting too long ({p.waiting_time:.0f} units)"
                else:
                    self.starving_processes.discard(p.pid)  # process recovered
        return None

    def _check_poor_performance(self, processes, current_algorithm):
        """Warns if average wait time is more than 2x the average burst time."""
        done = [p for p in processes if p.state == "Terminated"]
        if len(done) < 2:
            return None
        avg_wait  = sum(p.waiting_time for p in done) / len(done)
        avg_burst = sum(p.burst_time   for p in done) / len(done)
        if avg_wait > avg_burst * 2:
            return f"High avg wait ({avg_wait:.1f}) — {current_algorithm} may not suit this workload"
        return None

    def _suggest_better_algorithm(self, processes, current_algorithm):
        """Suggests a better algorithm based on current active workload mix and wait times."""
        active = [p for p in processes if p.state != "Terminated" and p.remaining_time > 0]
        if not active:
            return None
        cpu = sum(1 for p in active if not p.is_io_bound)
        io  = sum(1 for p in active if p.is_io_bound)
        io_ratio = io / (cpu + io)
        # Only suggest if there are actually processes suffering (waiting_time > 10)
        waiting = [p for p in active if p.state == "Ready" and p.waiting_time > 10]

        if io_ratio < 0.3 and current_algorithm not in ("SJF (Non-Preemptive)", "SRTF (Preemptive)") and waiting:
            bursts = [p.burst_time for p in active]
            variance = max(bursts) / min(bursts) if min(bursts) > 0 else 1
            algo = "SJF" if variance < 3 else "SRTF"
            return f"Mostly CPU-bound ({cpu} CPU, {io} I/O) → {algo} would minimize wait time"
        if 0.3 <= io_ratio <= 0.7 and current_algorithm != "MLFQ" and waiting:
            return f"Mixed workload ({io} I/O, {cpu} CPU) → MLFQ might perform better"
        if io_ratio > 0.7 and current_algorithm not in ("Round Robin", "MLFQ") and waiting:
            return f"Mostly I/O-bound ({io_ratio*100:.0f}%) → Round Robin (quantum 2-4)"
        return None

    def reset(self):
        """Clear all state between simulation runs."""
        self.starving_processes.clear()
        self.last_recommendation_time = -15
        self.stored_suggestions = []