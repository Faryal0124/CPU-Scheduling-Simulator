#main.py
import tkinter as tk
from tkinter import messagebox
from collections import deque
from process import Process
from scheduler import Scheduler
from visualization import Visualization
from adaptive_intelligence import AdaptiveIntelligence


class SchedulingSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced CPU Scheduling Simulator")
        self.root.geometry("800x1200")

        self.processes = []
        self.original_processes = []
        self.current_time = 0
        self.running = False
        self.paused = True
        self.current_process = None
        self.gantt_data = []
        self.stats = {}
        self.simulation_completed = False
        self.process_quantum_used = {}
        self.completion_order = []

        self.scheduler = Scheduler()
        self.ai_engine = AdaptiveIntelligence()
        self._ai_tick_counter = 0
        self._ai_analysis_interval = 5

        self.viz = Visualization(root, self.handle_callback, self)
        self.add_sample_processes()
        self.save_original_processes()
        self.update_all_displays()

    # ── Process helpers ───────────────────────────────────────────────────────

    def _make_copy(self, p):
        return Process(p.pid, p.arrival_time, p.burst_time, p.priority, p.is_io_bound)

    def save_original_processes(self):
        self.original_processes = [self._make_copy(p) for p in self.processes]

    def restore_original_processes(self):
        self.processes = [self._make_copy(p) for p in self.original_processes]
        self.viz.reset_selection()

    def add_sample_processes(self):
        for pid, arrival, burst, priority, ptype in [
            ("P1", 0, 10, 3, "CPU-bound"),
            ("P2", 2,  4, 1, "CPU-bound"),
            ("P3", 5,  8, 2, "I/O-bound"),
        ]:
            self.processes.append(Process(pid, arrival, burst, priority, ptype == "I/O-bound"))

    # ── Callback dispatcher ───────────────────────────────────────────────────

    def handle_callback(self, action, data=None):
        handlers = {
            'start': self.start_simulation,
            'pause': self.pause_simulation,
            'resume': self.resume_simulation,
            'reset': self.reset_simulation,
            'change_algorithm': self.change_algorithm,
            'set_quantum': lambda: self.set_time_quantum(data),
            'add_process': lambda: self.add_process_during_simulation(data),
            'edit_process': self.edit_process_during_simulation,
            'remove_process': self.remove_process_during_simulation,
        }
        handlers.get(action, lambda: None)()

    # ── Queue helpers ─────────────────────────────────────────────────────────

    def _remove_from_queues(self, process):
        if process in self.scheduler.rr_queue:
            self.scheduler.rr_queue.remove(process)
        for q in self.scheduler.mlfq_queues:
            if process in q:
                q.remove(process)

    def _add_to_queue(self, process):
        alg = self.scheduler.current_algorithm
        if alg == "Round Robin":
            self.scheduler.rr_queue.append(process)
        elif alg == "MLFQ":
            lvl = getattr(process, 'current_queue_level', 0)
            process.current_queue_level = lvl
            self.scheduler.mlfq_queues[lvl].append(process)

    def _start_process(self, process, t):
        process.start_time = t
        if process.response_time == -1:
            process.response_time = t - process.arrival_time
        process.state = "Running"
        self.current_process = process

    # ── Dynamic process management ────────────────────────────────────────────

    def add_process_during_simulation(self, data):
        try:
            pid     = data['pid'] or f"P{len(self.processes)+1}"
            burst   = data['burst']
            priority = data['priority']
            is_io   = data['is_io']
            arrival = int(self.current_time) if (self.running or (self.paused and self.current_time > 0)) else data['arrival']

            if arrival != data['arrival'] and not (self.running or (self.paused and self.current_time > 0)):
                pass
            elif arrival == int(self.current_time) and data['arrival'] != arrival:
                self.viz.add_feedback(f"🕐 Arrival auto-set to {arrival} for {pid}")

            if any(p.pid == pid for p in self.processes):
                messagebox.showerror("Error", f"Process {pid} already exists!")
                return

            process = Process(pid, arrival, burst, priority, is_io)
            if self.running and not self.paused and arrival <= self.current_time:
                process.state = "Ready"
                self.viz.add_feedback(f"🟢 {pid} added to READY QUEUE at t={self.current_time:.1f}")
            else:
                process.state = "New"
                self.viz.add_feedback(f"🟢 {pid} added (arrives at {arrival})")

            self.processes.append(process)
            self.processes.sort(key=lambda p: p.arrival_time)

            if process.state == "Ready":
                self._add_to_queue(process)

            self.update_all_displays()
            if self.running and not self.paused and process.state == "Ready":
                self.check_for_immediate_preemption()
        except Exception as e:
            messagebox.showerror("Error", f"Invalid input: {e}")

    def edit_process_during_simulation(self):
        pid = self.viz.get_selected_process()
        if not pid:
            messagebox.showwarning("Warning", "Please select a process to edit")
            return
        process = next((p for p in self.processes if p.pid == pid), None)
        if not process:
            return

        def save_changes(pid, new_arrival, new_burst, new_priority, new_is_io):
            p = next((x for x in self.processes if x.pid == pid), None)
            if not p:
                return
            was_running_proc = (self.current_process == p)
            was_ready = (p.state == "Ready")
            if was_ready:
                self._remove_from_queues(p)
            p.modify_process(new_arrival, new_burst, new_priority)
            p.is_io_bound = new_is_io
            if was_running_proc:
                p.state = "Running"
                self.current_process = p
            elif was_ready or (new_arrival <= self.current_time and self.running and not self.paused):
                p.state = "Ready"
                self._add_to_queue(p)
            else:
                p.state = "New"
            self.viz.add_feedback(f"✏️ MODIFIED: {pid} (Burst→{new_burst}, Pri→{new_priority})")
            self.processes.sort(key=lambda x: x.arrival_time)
            self.update_all_displays()
            if self.running and not self.paused:
                self.check_for_immediate_preemption()

        self.viz.show_edit_dialog(process, save_changes)

    def remove_process_during_simulation(self):
        pid = self.viz.get_selected_process()
        if not pid:
            messagebox.showwarning("Warning", "Please select a process to remove")
            return
        if pid in [p.pid for p in self.original_processes]:
            messagebox.showwarning("Warning", f"Cannot remove original process {pid}.")
            return
        process = next((p for p in self.processes if p.pid == pid), None)
        if not process:
            return
        if not messagebox.askyesno("Confirm Delete", f"Remove process {pid}?"):
            return

        if self.current_process == process:
            self.gantt_data.append((process.pid, process.start_time, self.current_time))
            self.current_process = None
            self.viz.add_feedback(f"❌ REMOVED running process {pid} at t={self.current_time:.1f}")
        elif process.state == "Ready":
            self._remove_from_queues(process)
            self.viz.add_feedback(f"❌ REMOVED {pid} from ready queue at t={self.current_time:.1f}")
        else:
            self.viz.add_feedback(f"❌ REMOVED {pid} (state: {process.state})")

        self.processes = [p for p in self.processes if p.pid != pid]
        self.completion_order = [c for c in self.completion_order if c[0] != pid]
        self.update_all_displays()

        if self.running and not self.paused and not self.current_process:
            self._schedule_next()

    # ── Scheduling helpers ────────────────────────────────────────────────────

    def _schedule_next(self):
        nxt = self.scheduler.get_next_process(
            self.processes, self.current_time, self.scheduler.current_algorithm)
        if nxt:
            self._remove_from_queues(nxt)
            self._start_process(nxt, self.current_time)
            self.viz.add_feedback(f"▶️ {nxt.pid} scheduled at t={self.current_time:.1f}")
            self.update_all_displays()

    def check_for_immediate_preemption(self):
        if not self.running or self.paused or not self.current_process:
            return
        alg = self.scheduler.current_algorithm
        if alg not in ("SRTF (Preemptive)", "Priority (Preemptive)"):
            return
        ready = self.get_ready_processes()
        preempt, better = self.scheduler.should_preempt(alg, self.current_process, ready)
        if preempt and better and better != self.current_process:
            self._do_preempt(better, alg)

    def _do_preempt(self, better_process, algorithm):
        self.gantt_data.append((self.current_process.pid, self.current_process.start_time, self.current_time))
        self.current_process.state = "Ready"
        self._add_to_queue(self.current_process)
        self._remove_from_queues(better_process)
        self._start_process(better_process, self.current_time)
        self.viz.add_feedback(f"⚠️ PREEMPTION: {better_process.pid} preempted at t={self.current_time:.1f}")
        self.update_all_displays()

    # ── Display ───────────────────────────────────────────────────────────────

    def update_all_displays(self):
        self.viz.update_process_table(self.processes, self.current_process, self.current_time, self.running, self.paused)
        self.viz.update_ready_queue_display(
            self.scheduler.current_algorithm, self.scheduler.mlfq_queues,
            self.scheduler.rr_queue, self.processes, self.current_time, self.current_process)
        self.viz.update_gantt_chart(self.gantt_data)
        self.calculate_metrics()
        self.viz.update_metrics(self.stats)

    def get_ready_processes(self):
        return [p for p in self.processes
                if p.arrival_time <= self.current_time
                and p.remaining_time > 0
                and p.state == "Ready"]

    def update_waiting_times(self, dt):
        for p in self.get_ready_processes():
            if p != self.current_process:
                p.waiting_time += dt

    def calculate_metrics(self):
        done = [p for p in self.processes if p.state == "Terminated"]
        if not done:
            return
        n = len(done)
        avg_wait = sum(p.waiting_time for p in done) / n
        avg_ta   = sum(p.turnaround_time for p in done) / n
        resp     = [p for p in done if p.response_time >= 0]
        avg_resp = sum(p.response_time for p in resp) / len(resp) if resp else 0
        total_burst = sum(p.burst_time for p in self.processes)
        cpu_util = min((total_burst / self.current_time) * 100, 100) if self.current_time > 0 else 0
        throughput = n / self.current_time if self.current_time > 0 else 0
        self.stats = {
            "Avg Waiting Time": avg_wait, "Avg Turnaround Time": avg_ta,
            "CPU Utilization": cpu_util, "Throughput": throughput,
            "Avg Response Time": avg_resp,
        }

    # ── Arrivals & completion ─────────────────────────────────────────────────

    def handle_arrivals(self):
        for p in self.processes:
            if p.arrival_time <= self.current_time and p.state == "New":
                p.state = "Ready"
                self.viz.add_feedback(f"📥 {p.pid} arrived at t={self.current_time:.1f}")
                self._add_to_queue(p)
                if (self.scheduler.current_algorithm == "MLFQ"
                        and self.current_process
                        and not self.paused):
                    lvl = getattr(self.current_process, 'current_queue_level', 0)
                    if lvl > 0:
                        self.root.after(1, self._force_mlfq_preemption_check)

    def _force_mlfq_preemption_check(self):
        if not self.current_process or self.paused or not self.running:
            return
        cur_lvl = getattr(self.current_process, 'current_queue_level', 0)
        for hi in range(cur_lvl):
            if self.scheduler.mlfq_queues[hi]:
                better = self.scheduler.mlfq_queues[hi][0]
                prev = self.current_process
                self.gantt_data.append((prev.pid, prev.start_time, self.current_time))
                prev.state = "Ready"
                self.scheduler.mlfq_queues[cur_lvl].append(prev)
                self.scheduler.mlfq_queues[hi].remove(better)
                self._start_process(better, self.current_time)
                self.viz.add_feedback(
                    f"⚠️ MLFQ PREEMPTION: {better.pid}(Q{hi}) preempted {prev.pid}(Q{cur_lvl}) at t={self.current_time:.1f}")
                self.update_all_displays()
                break

    def is_simulation_complete(self):
        if self.current_process:
            return False
        active = [p for p in self.processes if p.remaining_time > 0 and p.state != "Terminated"]
        future = [p for p in self.processes if p.arrival_time > self.current_time and p.state != "Terminated"]
        if not active and not future:
            if not self.simulation_completed:
                self._run_final_analysis()
                self.simulation_completed = True
            return True
        return False

    # ── AI analysis ───────────────────────────────────────────────────────────

    def _run_live_analysis(self):
        try:
            for level, msg, suggestion in self.ai_engine.analyze_live(
                    self.processes, self.current_time,
                    self.scheduler.current_algorithm, self.current_process):
                icon = {'warn': '⚠️', 'info': '💡', 'critical': '🔴'}.get(level, '📢')
                self.viz.add_feedback(f"{icon} {msg}")
                if suggestion:
                    self.viz.add_feedback(f"   → Try: {suggestion}")
        except Exception:
            pass

    def _run_final_analysis(self):
        try:
            self.calculate_metrics()
            recs = self.ai_engine.analyze_final(
                self.processes, self.current_time, self.scheduler.current_algorithm)
            self.viz.add_feedback("\n" + "="*60)
            self.viz.add_feedback("📊 SIMULATION COMPLETE - PERFORMANCE ANALYSIS")
            self.viz.add_feedback("="*60)
            if recs:
                for level, msg, suggestion in recs:
                    icon = {'warn': '⚠️', 'info': '💡', 'critical': '🔴'}.get(level, '📢')
                    self.viz.add_feedback(f"{icon} {msg}")
                    if suggestion:
                        self.viz.add_feedback(f"   → {suggestion}")
            else:
                self.viz.add_feedback("✅ Current algorithm performed adequately.")

            done = [p for p in self.processes if p.state == "Terminated"]
            if done:
                avg_w  = sum(p.waiting_time for p in done) / len(done)
                avg_ta = sum(p.turnaround_time for p in done) / len(done)
                resp   = [p for p in done if p.response_time >= 0]
                avg_r  = sum(p.response_time for p in resp) / len(resp) if resp else 0
                self.viz.add_feedback(f"\n📈 Performance Summary:")
                self.viz.add_feedback(f"   Algorithm: {self.scheduler.current_algorithm}")
                self.viz.add_feedback(f"   Avg Wait: {avg_w:.2f}  |  Avg TAT: {avg_ta:.2f}  |  Avg Resp: {avg_r:.2f}")
                self.viz.add_feedback(f"   Completed: {len(done)} processes")
                if self.completion_order:
                    self.viz.add_feedback("\n📋 Completion Order:")
                    for i, (pid, t) in enumerate(self.completion_order, 1):
                        self.viz.add_feedback(f"   {i}. {pid} (t={t:.1f})")
                if avg_w > 20:
                    self.viz.add_feedback(f"\n💡 High wait time ({avg_w:.1f}). Try SJF or RR.")
            self.viz.add_feedback("="*60)
        except Exception as e:
            self.viz.add_feedback(f"⚠️ Analysis error: {e}")

    # ── Simulation loop ───────────────────────────────────────────────────────

    def run_simulation_step(self):
        if self.paused or not self.running:
            return
        if self.is_simulation_complete():
            self.running = False
            self.paused = True
            self.update_all_displays()
            return

        self.handle_arrivals()
        alg = self.scheduler.current_algorithm

        # ── Preemption (SRTF / Priority-P) ─────────────────────────────────
        if alg in ("SRTF (Preemptive)", "Priority (Preemptive)") and self.current_process:
            ready = self.get_ready_processes()
            preempt, better = self.scheduler.should_preempt(alg, self.current_process, ready)
            if preempt and better and better != self.current_process:
                self._do_preempt(better, alg)
                self.root.after(50, self.run_simulation_step)
                return

        # ── MLFQ higher-priority preemption ────────────────────────────────
        elif alg == "MLFQ" and self.current_process:
            cur_lvl = getattr(self.current_process, 'current_queue_level', 0)
            for hi in range(cur_lvl):
                if self.scheduler.mlfq_queues[hi]:
                    better = self.scheduler.mlfq_queues[hi][0]
                    prev = self.current_process
                    self.gantt_data.append((prev.pid, prev.start_time, self.current_time))
                    prev.state = "Ready"
                    self.scheduler.mlfq_queues[cur_lvl].append(prev)
                    self.scheduler.mlfq_queues[hi].remove(better)
                    self._start_process(better, self.current_time)
                    self.viz.add_feedback(
                        f"⚠️ MLFQ: {better.pid}(Q{hi}) preempted {prev.pid}(Q{cur_lvl}) t={self.current_time:.1f}")
                    self.update_all_displays()
                    self.root.after(50, self.run_simulation_step)
                    return

        # ── Schedule if CPU idle ────────────────────────────────────────────
        if not self.current_process:
            nxt = self.scheduler.get_next_process(
                self.processes, self.current_time, alg, None)
            if nxt:
                self._remove_from_queues(nxt)
                self._start_process(nxt, self.current_time)
                self.viz.add_feedback(f"▶️ {nxt.pid} started at t={self.current_time:.1f}")

        # ── Execute one tick ────────────────────────────────────────────────
        if self.current_process:
            self.current_process.remaining_time -= 1
            self.update_waiting_times(1)

            if alg == "Round Robin":
                self.process_quantum_used[self.current_process.pid] = \
                    self.process_quantum_used.get(self.current_process.pid, 0) + 1
            if alg == "MLFQ":
                self.current_process.quantum_used = getattr(self.current_process, 'quantum_used', 0) + 1

            # Completion
            if self.current_process.remaining_time <= 0:
                t_end = self.current_time + 1
                self.gantt_data.append((self.current_process.pid, self.current_process.start_time, t_end))
                self.current_process.completion_time = t_end
                self.current_process.turnaround_time = t_end - self.current_process.arrival_time
                self.current_process.state = "Terminated"
                self.completion_order.append((self.current_process.pid, t_end))
                self.viz.add_feedback(f"🏁 {self.current_process.pid} completed at t={t_end:.1f}")
                self.process_quantum_used.pop(self.current_process.pid, None)
                self.current_process = None

            # RR quantum expiry
            elif alg == "Round Robin":
                used = self.process_quantum_used.get(self.current_process.pid, 0)
                if used >= self.scheduler.time_quantum:
                    self.process_quantum_used[self.current_process.pid] = 0
                    self.gantt_data.append(
                        (self.current_process.pid, self.current_process.start_time, self.current_time + 1))
                    self.current_process.state = "Ready"
                    self.scheduler.rr_queue.append(self.current_process)
                    self.current_process = None
                    self.viz.add_feedback("⏱️ Time quantum expired")
                    self.current_time += 1
                    self.update_all_displays()
                    self.root.after(50, self.run_simulation_step)
                    return

            # MLFQ quantum expiry / demotion
            elif alg == "MLFQ" and self.current_process:
                lvl = getattr(self.current_process, 'current_queue_level', 0)
                quantum = (self.scheduler.mlfq_time_quanta[lvl]
                           if lvl < len(self.scheduler.mlfq_time_quanta) else 2 ** lvl)
                if self.current_process.quantum_used >= quantum:
                    self.current_process.quantum_used = 0
                    nxt_lvl = min(self.scheduler.num_mlfq_queues - 1, lvl + 1)
                    self.current_process.current_queue_level = nxt_lvl
                    self.gantt_data.append(
                        (self.current_process.pid, self.current_process.start_time, self.current_time + 1))
                    self.current_process.state = "Ready"
                    self.scheduler.mlfq_queues[nxt_lvl].append(self.current_process)
                    self.viz.add_feedback(f"⏱️ Quantum expired → Q{nxt_lvl}")
                    self.current_process = None
                    self.current_time += 1
                    self.update_all_displays()
                    self.root.after(50, self.run_simulation_step)
                    return

            self.current_time += 1
        else:
            self.current_time += 1

        self.update_all_displays()
        self._ai_tick_counter += 1
        if self._ai_tick_counter >= self._ai_analysis_interval:
            self._ai_tick_counter = 0
            self._run_live_analysis()

        if not self.is_simulation_complete():
            self.root.after(100, self.run_simulation_step)
        else:
            self.running = False
            self.paused = True
            self.update_all_displays()

    # ── Sim control ───────────────────────────────────────────────────────────

    def start_simulation(self):
        if self.simulation_completed:
            self.viz.add_feedback("Auto-resetting for new simulation...")
            self.reset_simulation()
        if self.current_time == 0:
            self.viz.clear_feedback()
            for p in self.processes:
                p.state = "New"
                p.remaining_time = p.burst_time
            self.scheduler.rr_queue.clear()
            self.scheduler.mlfq_queues = [deque() for _ in range(self.scheduler.num_mlfq_queues)]
            self.process_quantum_used.clear()
            self.completion_order.clear()
        else:
            for p in self.processes:
                if p.state not in ("Terminated", "New", "Ready", "Running"):
                    p.state = "New"
        self.paused = False
        self.running = True
        self.simulation_completed = False
        self.viz.add_feedback(f"🚀 Started with {self.scheduler.current_algorithm}")
        self.run_simulation_step()

    def resume_simulation(self):
        if self.simulation_completed:
            self.viz.add_feedback("Simulation done. Use Start for a new run.")
            return
        if not self.paused:
            return
        self.paused = False
        self.running = True
        self.viz.add_feedback("▶️ Resumed")
        self.run_simulation_step()

    def pause_simulation(self):
        if not self.paused:
            self.paused = True
            self.running = False
            self.viz.add_feedback("⏸️ Paused")
            self.update_all_displays()

    def reset_simulation(self):
        self.paused = True
        self.running = False
        self.simulation_completed = False
        self.current_time = 0
        self.current_process = None
        self.gantt_data = []
        self.process_quantum_used = {}
        self.stats = {}
        self.completion_order = []
        self.restore_original_processes()
        self.scheduler.reset()
        self.ai_engine.reset()
        self._ai_tick_counter = 0
        for p in self.processes:
            p.reset()
            p.state = "New"
        self.viz.clear_feedback()
        self.update_all_displays()
        self.viz.add_feedback("🔄 Reset — dynamically added processes removed")

    def change_algorithm(self):
        was_running = self.running and not self.paused
        if was_running:
            self.pause_simulation()
        old = self.scheduler.current_algorithm
        new = self.viz.get_algorithm()
        if old == new:
            if was_running:
                self.resume_simulation()
            return
        self.scheduler.current_algorithm = new
        ready = [p for p in self.processes if p.state == "Ready" and p != self.current_process]
        self.scheduler.rr_queue.clear()
        self.scheduler.mlfq_queues = [deque() for _ in range(self.scheduler.num_mlfq_queues)]
        if new == "Round Robin":
            for p in sorted(ready, key=lambda p: p.arrival_time):
                self.scheduler.rr_queue.append(p)
        elif new == "MLFQ":
            for p in sorted(ready, key=lambda p: p.arrival_time):
                p.current_queue_level = 0
                p.waiting_since = self.current_time
                self.scheduler.mlfq_queues[0].append(p)
        self.process_quantum_used = {}
        if self.current_process and hasattr(self.current_process, 'quantum_used'):
            self.current_process.quantum_used = 0
        self.viz.add_feedback(f"🔄 Algorithm: {old} → {new} (t={self.current_time:.1f}, {len(ready)} processes preserved)")
        self.update_all_displays()
        if was_running:
            self.resume_simulation()

    def set_time_quantum(self, value):
        try:
            q = int(value)
            if q <= 0:
                raise ValueError
            self.scheduler.time_quantum = q
            self.viz.add_feedback(f"⏲️ Time quantum set to {q}")
        except Exception:
            messagebox.showerror("Error", "Invalid time quantum value")


def main():
    root = tk.Tk()
    SchedulingSimulator(root)
    root.mainloop()


if __name__ == "__main__":
    main()