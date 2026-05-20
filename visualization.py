#visualization.py    
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from datetime import datetime


class Visualization:
    def __init__(self, root, callback_handler, simulator=None):
        self.root = root
        self.callback_handler = callback_handler
        self.simulator = simulator
        self.edit_window = None
        self.setup_ui()

    def get_scheduler(self):
        return self.simulator.scheduler if self.simulator else None

    # ── Layout ────────────────────────────────────────────────────────────────

    def setup_ui(self):
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw",
                                  width=self.canvas.winfo_reqwidth())
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind("<MouseWheel>",
                         lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(1, width=e.width))
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.build_ui()

    def build_ui(self):
        sf = self.scrollable_frame
        sf.grid_columnconfigure(0, weight=1)

        # ── Control Panel ────────────────────────────────────────────────────
        ctrl = ttk.LabelFrame(sf, text="Control Panel", padding=10)
        ctrl.grid(row=0, column=0, sticky="ew", pady=(0, 10), padx=10)

        ttk.Label(ctrl, text="Algorithm:").grid(row=0, column=0, padx=5, pady=5)
        self.algo_var = tk.StringVar(value="FCFS")
        self.algo_combo = ttk.Combobox(ctrl, textvariable=self.algo_var, state="readonly", width=25,
            values=["FCFS", "SJF (Non-Preemptive)", "SRTF (Preemptive)",
                    "Priority (Non-Preemptive)", "Priority (Preemptive)", "Round Robin", "MLFQ"])
        self.algo_combo.grid(row=0, column=1, padx=5, pady=5)
        self.algo_combo.bind('<<ComboboxSelected>>', lambda e: self.callback_handler('change_algorithm'))

        ttk.Label(ctrl, text="Time Quantum:").grid(row=0, column=2, padx=5, pady=5)
        self.quantum_var = tk.StringVar(value="4")
        ttk.Entry(ctrl, textvariable=self.quantum_var, width=10).grid(row=0, column=3, padx=5, pady=5)
        ttk.Button(ctrl, text="Set",
                   command=lambda: self.callback_handler('set_quantum', self.quantum_var.get())
                   ).grid(row=0, column=4, padx=5, pady=5)

        btn_f = ttk.Frame(ctrl)
        btn_f.grid(row=0, column=5, columnspan=5, padx=20, pady=5)
        for label, action in [("Start","start"),("Pause","pause"),("Resume","resume"),("Reset","reset")]:
            ttk.Button(btn_f, text=label,
                       command=lambda a=action: self.callback_handler(a)).pack(side=tk.LEFT, padx=2)

        ttk.Button(ctrl, text="⚙️ MLFQ Config",
                   command=self.show_mlfq_config_dialog).grid(row=0, column=10, padx=5, pady=5)

        # ── Process Management ───────────────────────────────────────────────
        pm = ttk.LabelFrame(sf, text="Process Management", padding=10)
        pm.grid(row=1, column=0, sticky="ew", pady=(0, 10), padx=10)
        pm.grid_columnconfigure(0, weight=1)

        form = ttk.Frame(pm)
        form.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.pid_var     = tk.StringVar()
        self.arrival_var = tk.StringVar(value="0")
        self.burst_var   = tk.StringVar(value="5")
        self.priority_var = tk.StringVar(value="0")
        self.type_var    = tk.StringVar(value="CPU-bound")

        for col, (lbl, var, w) in enumerate([
            ("PID:", self.pid_var, 8), ("Arrival:", self.arrival_var, 8),
            ("Burst:", self.burst_var, 8), ("Priority:", self.priority_var, 8)
        ]):
            ttk.Label(form, text=lbl).grid(row=0, column=col*2, padx=5, pady=5)
            ttk.Entry(form, textvariable=var, width=w).grid(row=0, column=col*2+1, padx=5, pady=5)

        ttk.Label(form, text="Type:").grid(row=0, column=8, padx=5, pady=5)
        ttk.Combobox(form, textvariable=self.type_var, values=["CPU-bound","I/O-bound"],
                     width=10).grid(row=0, column=9, padx=5, pady=5)

        ttk.Button(form, text="Add Process",
                   command=lambda: self.callback_handler('add_process', self.get_process_data())
                   ).grid(row=0, column=10, padx=5, pady=5)
        ttk.Button(form, text="Edit Selected",
                   command=lambda: self.callback_handler('edit_process')
                   ).grid(row=0, column=11, padx=5, pady=5)
        ttk.Button(form, text="Remove Selected",
                   command=lambda: self.callback_handler('remove_process')
                   ).grid(row=0, column=12, padx=5, pady=5)

        cols = ("PID","Arrival","Burst","Remaining","Priority","Type","Waiting","Turnaround","State")
        widths = dict(PID=55,Arrival=65,Burst=55,Remaining=75,Priority=55,Type=50,Waiting=65,Turnaround=75,State=70)
        self.process_tree = ttk.Treeview(pm, columns=cols, show="headings", height=8, selectmode="browse")
        for c in cols:
            self.process_tree.heading(c, text=c)
            self.process_tree.column(c, width=widths.get(c, 70))
        tree_sb = ttk.Scrollbar(pm, orient=tk.VERTICAL, command=self.process_tree.yview)
        self.process_tree.configure(yscrollcommand=tree_sb.set)
        self.process_tree.grid(row=1, column=0, sticky="nsew")
        tree_sb.grid(row=1, column=1, sticky="ns")

        # ── Gantt + Ready Queue ──────────────────────────────────────────────
        split = ttk.Frame(sf)
        split.grid(row=2, column=0, sticky="ew", pady=(0, 10), padx=10)
        split.grid_columnconfigure(0, weight=7)
        split.grid_columnconfigure(1, weight=3)

        gantt_f = ttk.LabelFrame(split, text="📊 Gantt Chart", padding=10)
        gantt_f.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        gantt_f.grid_columnconfigure(0, weight=1)
        self.fig = Figure(figsize=(9, 5), dpi=80)
        self.gantt_ax = self.fig.add_subplot(111)
        self.canvas_widget = FigureCanvasTkAgg(self.fig, master=gantt_f)
        self.canvas_widget.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        rq_f = ttk.LabelFrame(split, text="📋 Ready Queue", padding=10)
        rq_f.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        rq_f.grid_columnconfigure(0, weight=1)
        self.ready_queue_text = tk.Text(rq_f, height=15, font=("Courier", 9), wrap=tk.WORD)
        self.ready_queue_text.grid(row=0, column=0, sticky="nsew")
        rq_sb = ttk.Scrollbar(rq_f, orient=tk.VERTICAL, command=self.ready_queue_text.yview)
        rq_sb.grid(row=0, column=1, sticky="ns")
        self.ready_queue_text.configure(yscrollcommand=rq_sb.set)

        # ── Metrics + Feedback ───────────────────────────────────────────────
        bottom = ttk.Frame(sf)
        bottom.grid(row=3, column=0, sticky="ew", pady=(0, 10), padx=10)
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_columnconfigure(1, weight=1)

        metrics_f = ttk.LabelFrame(bottom, text="📈 Performance Metrics", padding=10)
        metrics_f.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.metrics_labels = {}
        for metric, default in [("Avg Waiting Time","0.00"),("Avg Turnaround Time","0.00"),
                                  ("CPU Utilization","0.00%"),("Throughput","0.00"),("Avg Response Time","0.00")]:
            f = ttk.Frame(metrics_f)
            f.pack(fill=tk.X, pady=8)
            ttk.Label(f, text=f"{metric}:", font=("Arial",10,"bold")).pack(side=tk.LEFT, padx=5)
            lbl = ttk.Label(f, text=default, font=("Arial",10,"bold"), foreground="blue")
            lbl.pack(side=tk.RIGHT, padx=5)
            self.metrics_labels[metric] = lbl

        fb_f = ttk.LabelFrame(bottom, text="💬 Simulation Feedback", padding=10)
        fb_f.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        fb_f.grid_columnconfigure(0, weight=1)
        self.feedback_text = scrolledtext.ScrolledText(fb_f, height=8, font=("Arial",9), wrap=tk.WORD)
        self.feedback_text.grid(row=0, column=0, sticky="nsew")

        ttk.Frame(sf, height=20).grid(row=4, column=0)
        self._welcome()

    def _welcome(self):
        for msg in ["🎉 Welcome to CPU Scheduling Simulator!",
                    "Select an algorithm and click Start to begin simulation",
                    "You can add/edit/remove processes dynamically during simulation",
                    "💡 For MLFQ, click '⚙️ MLFQ Config' to adjust queues and aging settings"]:
            self.add_feedback(msg)

    # ── MLFQ config dialog ────────────────────────────────────────────────────

    def show_mlfq_config_dialog(self):
        scheduler = self.get_scheduler()
        if not scheduler:
            return
        config = scheduler.get_mlfq_config()
        win = tk.Toplevel(self.root)
        win.title("MLFQ Configuration")
        win.geometry("600x650")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        nb = ttk.Notebook(win)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Queue tab
        qf = ttk.Frame(nb, padding=15)
        nb.add(qf, text="Queue Configuration")
        ttk.Label(qf, text="Number of Queues:", font=("Arial",10,"bold")).grid(row=0, column=0, sticky="w", pady=10)
        num_q_var = tk.IntVar(value=config['num_queues'])
        ttk.Spinbox(qf, from_=1, to=5, textvariable=num_q_var, width=10).grid(row=0, column=1, sticky="w", padx=10)
        ttk.Label(qf, text="Time Quantum per Queue:", font=("Arial",10,"bold")).grid(row=1, column=0, columnspan=2, sticky="w", pady=(10,5))

        qc = tk.Canvas(qf, height=150)
        qsb = ttk.Scrollbar(qf, orient=tk.VERTICAL, command=qc.yview)
        qi = ttk.Frame(qc)
        qi.bind("<Configure>", lambda e: qc.configure(scrollregion=qc.bbox("all")))
        qc.configure(yscrollcommand=qsb.set)
        qc.create_window((0, 0), window=qi, anchor="nw")
        qc.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        qsb.grid(row=2, column=2, sticky="ns")

        quanta_entries = []
        for i, q in enumerate(config['time_quanta']):
            ttk.Label(qi, text=f"Queue {i+1}:").grid(row=i, column=0, padx=5, pady=5)
            e = ttk.Entry(qi, width=15)
            e.insert(0, str(q))
            e.grid(row=i, column=1, padx=5, pady=5)
            quanta_entries.append(e)

        def update_entries(*_):
            new_n = num_q_var.get()
            cur = len(quanta_entries)
            if new_n > cur:
                for i in range(cur, new_n):
                    ttk.Label(qi, text=f"Queue {i+1}:").grid(row=i, column=0, padx=5, pady=5)
                    e = ttk.Entry(qi, width=15)
                    e.insert(0, str(config['time_quanta'][i] if i < len(config['time_quanta']) else 2**i))
                    e.grid(row=i, column=1, padx=5, pady=5)
                    quanta_entries.append(e)
            elif new_n < cur:
                for i in range(new_n, cur):
                    for w in qi.grid_slaves(row=i):
                        w.destroy()
                del quanta_entries[new_n:]
            qc.configure(scrollregion=qc.bbox("all"))

        num_q_var.trace_add('write', update_entries)

        # Aging tab
        af = ttk.Frame(nb, padding=15)
        nb.add(af, text="Aging Configuration")
        aging_t_var = tk.IntVar(value=config['aging_threshold'])
        aging_a_var = tk.IntVar(value=config['aging_amount'])
        for row, (label, var, lo, hi) in enumerate([
            ("Aging Threshold (cycles):", aging_t_var, 1, 100),
            ("Aging Amount (priority levels):", aging_a_var, 1, 10),
        ]):
            ttk.Label(af, text=label, font=("Arial",10,"bold")).grid(row=row, column=0, sticky="w", pady=10)
            ttk.Spinbox(af, from_=lo, to=hi, textvariable=var, width=10).grid(row=row, column=1, padx=10)

        # Info tab
        inf = ttk.Frame(nb, padding=15)
        nb.add(inf, text="Info")
        ttk.Label(inf, text=(
            "MLFQ: Higher priority queues have smaller quanta.\n"
            "Processes use their full quantum then move to a lower queue.\n"
            "Aging promotes long-waiting processes to prevent starvation.\n\n"
            f"Current: {config['num_queues']} queues, quanta={config['time_quanta']}\n"
            f"Aging threshold={config['aging_threshold']}, amount={config['aging_amount']}"
        ), justify=tk.LEFT, wraplength=550).pack(pady=10)

        # Buttons
        bf = ttk.Frame(win)
        bf.pack(pady=15)

        def apply():
            try:
                n = num_q_var.get()
                quanta = []
                for e in quanta_entries:
                    v = int(e.get())
                    if v <= 0:
                        raise ValueError("Quantum must be positive")
                    quanta.append(v)
                while len(quanta) < n:
                    quanta.append(2 ** len(quanta))
                quanta = quanta[:n]
                scheduler.reconfigure_mlfq(num_queues=n, time_quanta=quanta,
                                            aging_threshold=aging_t_var.get(),
                                            aging_amount=aging_a_var.get())
                self.add_feedback(f"⚙️ MLFQ reconfigured: {n} queues, quanta={quanta}")
                win.destroy()
            except ValueError as e:
                messagebox.showerror("Error", str(e))

        ttk.Button(bf, text="Apply Changes", command=apply).pack(side=tk.LEFT, padx=5)
        ttk.Button(bf, text="Cancel", command=win.destroy).pack(side=tk.LEFT, padx=5)

    # ── Data helpers ──────────────────────────────────────────────────────────

    def reset_selection(self):
        for item in self.process_tree.selection():
            self.process_tree.selection_remove(item)

    def get_process_data(self):
        return {
            'pid': self.pid_var.get(),
            'arrival': float(self.arrival_var.get()),
            'burst': float(self.burst_var.get()),
            'priority': int(self.priority_var.get()),
            'is_io': (self.type_var.get() == "I/O-bound"),
        }

    def get_selected_process(self):
        sel = self.process_tree.selection()
        return self.process_tree.item(sel[0], 'values')[0] if sel else None

    def get_algorithm(self):
        return self.algo_var.get()

    def get_time_quantum(self):
        try:
            return int(self.quantum_var.get())
        except Exception:
            return 4

    def get_mlfq_time_quantum(self, level):
        s = self.get_scheduler()
        if s and hasattr(s, 'mlfq_time_quanta') and level < len(s.mlfq_time_quanta):
            return s.mlfq_time_quanta[level]
        return 2 ** level

    # ── Update methods ────────────────────────────────────────────────────────

    def update_process_table(self, processes, current_process, current_time, running, paused):
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)
        for p in processes:
            state = p.state
            if current_process and current_process.pid == p.pid and not paused and running:
                state = "Running"
            elif p.remaining_time <= 0:
                state = "Completed"
            item = self.process_tree.insert("", tk.END, values=(
                p.pid, p.arrival_time, p.burst_time, round(p.remaining_time, 2),
                p.priority, "I/O" if p.is_io_bound else "CPU",
                round(p.waiting_time, 2), round(p.turnaround_time, 2), state))
            tag = {'Running': 'running', 'Completed': 'completed', 'Ready': 'waiting'}.get(state)
            if tag:
                bg = {'running': '#90EE90', 'completed': '#D3D3D3', 'waiting': '#FFF3B0'}[tag]
                self.process_tree.tag_configure(tag, background=bg)
                self.process_tree.item(item, tags=(tag,))

    def update_ready_queue_display(self, algorithm, mlfq_queues, rr_queue, processes, current_time, current_process):
        t = self.ready_queue_text
        t.delete(1.0, tk.END)
        t.insert(tk.END, f"{'═'*40}\n  ALGORITHM: {algorithm}\n  TIME: {current_time:.1f}\n{'═'*40}\n\n")

        if algorithm == "MLFQ":
            for i, q in enumerate(mlfq_queues):
                label = f"Q{i+1} (Pri={i}, Q={self.get_mlfq_time_quantum(i)})"
                content = [p.pid for p in q] if q else "Empty"
                t.insert(tk.END, f"📌 {label}:\n   {content}\n\n")
        elif algorithm == "Round Robin":
            content = [p.pid for p in rr_queue] if rr_queue else "Empty"
            t.insert(tk.END, f"🔄 Round Robin Queue (Q={self.get_time_quantum()}):\n   {content}\n\n")
        else:
            ready = sorted([p for p in processes
                            if p.arrival_time <= current_time and p.remaining_time > 0 and p.state == "Ready"],
                           key=lambda p: p.arrival_time)
            pids = [p.pid for p in ready] if ready else "Empty"
            t.insert(tk.END, f"📋 Ready Queue:\n   {pids}\n\n")

        if current_process and current_process.remaining_time > 0:
            t.insert(tk.END, f"{'─'*40}\n▶️  RUNNING: {current_process.pid}\n"
                              f"   Remaining: {current_process.remaining_time:.1f}\n"
                              f"   Priority: {current_process.priority}\n")
        t.see(tk.END)

    def update_gantt_chart(self, gantt_data):
        self.gantt_ax.clear()
        if not gantt_data:
            self.gantt_ax.text(0.5, 0.5, "▶️ Start simulation to see Gantt chart",
                               transform=self.gantt_ax.transAxes, ha='center', va='center',
                               fontsize=11, fontweight='bold', color='gray')
            self.canvas_widget.draw()
            return
        intervals = {}
        for pid, s, e in gantt_data:
            intervals.setdefault(pid, []).append((s, e))
        colors = plt.cm.Set3(range(len(intervals)))
        color_map = {pid: colors[i] for i, pid in enumerate(intervals)}
        for y, (pid, segs) in enumerate(intervals.items()):
            for s, e in segs:
                self.gantt_ax.barh(y, e - s, left=s, height=0.6,
                                   color=color_map[pid], edgecolor='black', linewidth=0.8)
                self.gantt_ax.text(s + (e - s) / 2, y, pid,
                                   ha='center', va='center', fontsize=9, fontweight='bold')
        self.gantt_ax.set(xlabel="Time", ylabel="Processes", title="Gantt Chart - CPU Scheduling")
        self.gantt_ax.grid(True, alpha=0.3, axis='x')
        self.gantt_ax.set_yticks(range(len(intervals)))
        self.gantt_ax.set_yticklabels(list(intervals.keys()), fontsize=9)
        self.fig.tight_layout()
        self.canvas_widget.draw()

    def update_metrics(self, stats):
        for metric, value in stats.items():
            if metric in self.metrics_labels:
                text = f"{value:.2f}%" if metric == "CPU Utilization" else f"{value:.2f}"
                self.metrics_labels[metric].config(text=text)

    def add_feedback(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        self.feedback_text.insert(tk.END, f"[{ts}] {message}\n")
        self.feedback_text.see(tk.END)

    def clear_feedback(self):
        self.feedback_text.delete(1.0, tk.END)
        self._welcome()

    # ── Edit dialog ───────────────────────────────────────────────────────────

    def show_edit_dialog(self, process, save_callback):
        if self.edit_window and self.edit_window.winfo_exists():
            self.edit_window.lift()
            return
        self.edit_window = tk.Toplevel(self.root)
        self.edit_window.title(f"Edit Process {process.pid}")
        self.edit_window.geometry("400x320")
        self.edit_window.resizable(False, False)
        self.edit_window.transient(self.root)
        self.edit_window.grab_set()

        ttk.Label(self.edit_window, text=f"Editing: {process.pid}",
                  font=("Arial",12,"bold")).pack(pady=10)
        f = ttk.Frame(self.edit_window, padding=20)
        f.pack(fill=tk.BOTH, expand=True)

        fields = [
            ("Arrival Time:", str(process.arrival_time)),
            ("Burst Time:",   str(process.burst_time)),
            ("Priority:",     str(process.priority)),
        ]
        vars_ = []
        for row, (lbl, val) in enumerate(fields):
            ttk.Label(f, text=lbl, font=("Arial",10)).grid(row=row, column=0, padx=10, pady=10, sticky="w")
            v = tk.StringVar(value=val)
            ttk.Entry(f, textvariable=v, width=20).grid(row=row, column=1, padx=10, pady=10)
            vars_.append(v)
        arrival_v, burst_v, priority_v = vars_

        ttk.Label(f, text="Process Type:", font=("Arial",10)).grid(row=3, column=0, padx=10, pady=10, sticky="w")
        type_v = tk.StringVar(value="I/O-bound" if process.is_io_bound else "CPU-bound")
        ttk.Combobox(f, textvariable=type_v, values=["CPU-bound","I/O-bound"],
                     state="readonly", width=18).grid(row=3, column=1, padx=10, pady=10, sticky="w")

        bf = ttk.Frame(f)
        bf.grid(row=4, column=0, columnspan=2, pady=20)

        def save():
            try:
                a = int(float(arrival_v.get()))
                b = float(burst_v.get())
                p = int(priority_v.get())
                if a < 0 or b <= 0:
                    messagebox.showerror("Error", "Invalid values")
                    return
                save_callback(process.pid, a, b, p, type_v.get() == "I/O-bound")
                self.edit_window.destroy()
                self.edit_window = None
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numeric values")

        ttk.Button(bf, text="Save Changes", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(bf, text="Cancel",
                   command=lambda: self.edit_window.destroy()).pack(side=tk.LEFT, padx=5)