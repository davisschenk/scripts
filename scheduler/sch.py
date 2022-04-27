__author__ = "Davis Schenkenberger"
__version__ = "1.0.0"

import argparse
import pandas
from typing import List
from collections import deque
from abc import ABC, abstractmethod


class Process:
    """
    A class representing a process
    """

    def __init__(self, pid, arrival, burst, priority):
        self.pid = pid
        self.arrival = arrival
        self.burst = burst
        self.priority = priority

        self.waiting_time = 0
        self.turnaround_time = 0

    @classmethod
    def from_tuple(cls, t):
        """Create a process from a tuple"""
        _, pid, at, bt, p = t
        return cls(pid, at, bt, p)

    def __repr__(self):
        return f"Process({self.pid}, {self.arrival}, {self.burst}, {self.priority})"


class Processes(list):
    """A container that holds processes"""

    @classmethod
    def from_csv(cls, csv):
        """Generate a list of processes from a pandas dataframe"""
        a = cls()
        a.extend([Process.from_tuple(t) for t in csv.itertuples()])
        return a

    def average_waiting_time(self):
        """Calculate average waiting time"""
        return sum(p.waiting_time for p in self) / len(self)

    def average_turnaround_time(self):
        """Calculate average turnaround time"""
        return sum(p.turnaround_time for p in self) / len(self)

    def print(self, name):
        print(f" {name} ".center(40, "-"))
        print("Process ID | Waiting Time | Turnaround Time")
        for process in sorted(self, key=lambda p: p.pid):
            print(
                f"{process.pid:^11}|{process.waiting_time:^14}|{process.turnaround_time:^16}"
            )


class GanttChartInfo:
    """Stores a data entry for the gantt chart"""

    def __init__(self, job, start, stop):
        self.job = job
        self.start = start
        self.stop = stop

    def __repr__(self):
        return f"[{self.start:^6}]--{self.job:^6}--[{self.stop:^6}]"


class GanttChart:
    """A gantt chart that allows adding data and printing it out"""

    def __init__(self):
        self.data = []

    def add(self, job, start, stop):
        self.data.append(GanttChartInfo(job, start, stop))

    def __repr__(self):
        return f"{self.data}"

    def fill_empty(self):
        for index in range(1, len(self.data)):
            if self.data[index - 1].stop != self.data[index].start:
                self.data.insert(
                    index,
                    GanttChartInfo(
                        "IDLE", self.data[index - 1].stop, self.data[index].start
                    ),
                )

    def print(self):
        self.fill_empty()

        print("Gantt Chart is:")
        for row in self.data:
            print(f"{row}")


class Scheduler(ABC):
    """Base class for a scheduler"""

    def __init__(self, processes: Processes, quantum):
        self.processes: Processes = processes
        self.quantum = quantum
        self.gantt = GanttChart()

    @abstractmethod
    def run(self):
        return NotImplemented

    def average_turnaround_time(self):
        return self.processes.average_turnaround_time()

    def average_waiting_time(self):
        return self.processes.average_waiting_time()

    def calculate_throughput(self):
        return len(self.processes) / self.gantt.data[-1].stop

    def print_stats(self):
        print(f"Average Waiting Time: {self.average_waiting_time()}")
        print(f"Average Turnaround Time: {self.average_turnaround_time()}")
        print(f"Throughput: {self.calculate_throughput()}")


class FirstComeFirstServe(Scheduler):
    def __init__(self, processes: List[Process], quantum: int):
        super().__init__(processes, quantum)

        # Sort processes first by arrival, then by pid
        processes.sort(key=lambda p: (p.arrival, p.pid))
        self.finish_time = [-1 for _ in self.processes]

    def run(self):
        """Iterate through processes, calculate finsh time/waiting time/turnaround time, and add gantt entry"""
        for index, process in enumerate(self.processes):
            if index == 0 or process.arrival > self.finish_time[index - 1]:
                self.finish_time[index] = process.arrival + process.burst
                self.gantt.add(process.pid, process.arrival, self.finish_time[index])
            else:
                self.finish_time[index] = self.finish_time[index - 1] + process.burst
                self.gantt.add(
                    process.pid, self.finish_time[index - 1], self.finish_time[index]
                )

            process.turnaround_time = self.finish_time[index] - process.arrival
            process.waiting_time = (
                self.finish_time[index] - process.arrival - process.burst
            )


class Priority(FirstComeFirstServe):
    """Priority queue reuses FCFS since the only difference is sorting"""

    def __init__(self, processes: List[Process], quantum: int):
        super().__init__(processes, quantum)

        # Sort by arrival, then priority and finally pid
        processes.sort(key=lambda p: (p.arrival, p.priority, p.pid))
        self.finish_time = [-1 for _ in self.processes]


class RoundRobin(Scheduler):
    def __init__(self, processes, quantum):
        super().__init__(processes, quantum)

        self.processes.sort(key=lambda p: (p.arrival, p.pid))
        self.time = self.processes[0].arrival
        self.remaining_time = {p.pid: p.burst for p in self.processes}
        self.unfinished = [p for p in self.processes]
        self.queue = deque([self.unfinished[0]])

    def run(self):
        while sum(self.remaining_time) and len(self.unfinished) > 0:
            # Iterate while processes have remaining time and there are unfinished jobs
            if len(self.queue) == 0 and len(self.unfinished) > 0:
                # Reload the queue if its empty and there are unfinished jobs
                self.queue.append(self.unfinished[0])
                self.time = self.queue[0].arrival

            # Use first process in queue
            process = self.queue[0]

            if self.remaining_time[process.pid] <= self.quantum:
                # if the remaining time is less than or equal to quantum then we remove the remaining time and add it it to total time
                t = self.remaining_time[process.pid]
                self.remaining_time[process.pid] -= t
                old_time = self.time
                self.time += t

                self.gantt.add(process.pid, old_time, self.time)
            else:
                # Otherwise we just remove the quantum
                self.remaining_time[process.pid] -= self.quantum
                old_time = self.time
                self.time += self.quantum

                self.gantt.add(process.pid, old_time, self.time)

            # Add all processes that will arrive at this time to the queue and push the head of the queue to the end
            self.queue.extend([p for p in self.processes if self.arriving(p)])
            self.queue.rotate(-1)

            # Remove the process from unfinished and the queue if its done
            if self.remaining_time[process.pid] == 0:
                self.queue.remove(process)
                self.unfinished.remove(process)

            # Calculate turnaround and waiting time
            process.turnaround_time = self.time - process.arrival
            process.waiting_time = self.time - process.arrival - process.burst

    def arriving(self, p):
        """Check if a process is arriving now"""
        return (
            p.arrival <= self.time
            and p is not self.queue[0]
            and p not in self.queue
            and p in self.unfinished
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HW4 CPU Scheduling Algorithms")
    parser.add_argument(
        "FILE", type=pandas.read_csv, help="CSV containing process info"
    )
    parser.add_argument("QUANTUM", help="Time Quantum")

    args = parser.parse_args()

    processes = Processes.from_csv(args.FILE)
    schedulers = {
        "FCFS": FirstComeFirstServe,
        "PS": Priority,
        "Round Robin": RoundRobin,
    }

    # Run each scheduler
    for name, scheduler in schedulers.items():
        s = scheduler(processes, int(args.QUANTUM))
        s.run()

        s.processes.print(name)
        print()
        s.gantt.print()
        print()
        s.print_stats()
        print()
