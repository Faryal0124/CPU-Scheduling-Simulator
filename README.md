# CPU Scheduling Simulator

An interactive desktop simulator for visualizing and comparing CPU scheduling algorithms, built with Python and Tkinter.

---

## Features

- **7 Scheduling Algorithms** — FCFS, SJF (Non-Preemptive), SRTF (Preemptive), Priority (Non-Preemptive), Priority (Preemptive), Round Robin, and MLFQ
- **Live Gantt Chart** — updates in real time as the simulation runs
- **Adaptive AI Engine** — monitors the workload and recommends better algorithms; alerts on process starvation
- **Dynamic Process Management** — add, edit, or remove processes while the simulation is running or paused
- **MLFQ Configuration** — customize the number of queues, time quanta per level, aging threshold, and aging amount
- **Performance Statistics** — average waiting time, turnaround time, and response time calculated at completion

---

## Project Structure

```
├── main.py                  # Entry point; simulation controller and UI orchestration
├── scheduler.py             # All scheduling algorithm implementations
├── process.py               # Process data model
├── visualization.py         # Tkinter GUI and Gantt chart rendering
└── adaptive_intelligence.py # AI recommendation and starvation detection engine
```

---

## Requirements

- Python 3.8+
- Tkinter (included in the standard library on most platforms)

No third-party packages are required.

---

## Getting Started

# Run the simulator
python main.py
```



---

## Usage

1. **Add processes** using the process panel (PID, arrival time, burst time, priority, CPU/IO type).
2. **Select an algorithm** from the dropdown.
3. Press **Start** to begin the simulation.
4. Use **Pause / Resume** to step through the execution.
5. Watch the **Gantt chart** and **feedback panel** update live.
6. View **final statistics** and AI recommendations when the simulation completes.
7. Press **Reset** to start over.

---

## Algorithms

| Algorithm | Preemptive | Notes |
|---|---|---|
| FCFS | No | First Come First Served |
| SJF | No | Shortest Job First |
| SRTF | Yes | Shortest Remaining Time First |
| Priority | No | Lower number = higher priority |
| Priority | Yes | Preempts on higher-priority arrival |
| Round Robin | Yes | Configurable time quantum |
| MLFQ | Yes | Multi-Level Feedback Queue with aging |

---

## License

MIT License. Feel free to use, modify, and distribute.# CPU-Scheduling-Simulator
