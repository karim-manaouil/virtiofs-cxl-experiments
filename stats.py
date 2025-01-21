import os
import time
import csv
import signal
import sys
import argparse
import matplotlib.pyplot as plt
from datetime import datetime
import subprocess

# Flag to handle Ctrl-C
running = True

def signal_handler(sig, frame):
    """
    Handles SIGINT (Ctrl-C) to stop the script gracefully.
    """
    global running
    running = False
    print("\nMonitoring stopped by user.")

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)

def read_numa_stats(cgroups, interval_ms, duration_s, output_file):
    """
    Reads `file*` stats from memory.numa_stat of given cgroups at specified intervals and stores them in memory.
    """
    global running
    data = []  # Store stats as a list of dictionaries
    start_time = time.time()
    end_time = start_time + duration_s if duration_s > 0 else float("inf")

    try:
        while running and time.time() < end_time:
            timestamp = time.time() - start_time
            for cgroup, location in cgroups.items():
                user, machine, path = location.get("user"), location.get("machine"), location.get("path")
                if machine:
                    stats_file = f"{user}@{machine}:{path}"
                    command = f"ssh {user}@{machine} cat {path}"
                else:
                    stats_file = path
                    command = f"cat {path}"
                try:
                    result = subprocess.check_output(command, shell=True, text=True)
                    for line in result.splitlines():
                        if line.startswith("file"):
                            stat_name, *node_values = line.strip().split()
                            stat_data = {"timestamp": timestamp, "cgroup": cgroup, "stat": stat_name}
                            for node_value in node_values:
                                node, value = node_value.split("=")
                                stat_data[node] = int(value) / (1024 * 1024)  # Convert bytes to MB
                            data.append(stat_data)
                except Exception as e:
                    print(f"Warning: Could not read {stats_file}. Error: {e}")
            time.sleep(interval_ms / 1000.0)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Save collected data before exiting
        save_to_csv(data, output_file)
        print("Data saved.")

def save_to_csv(data, output_file):
    """
    Saves collected stats to a CSV file.
    """
    if not data:
        print("No data to save.")
        return

    keys = data[0].keys()
    with open(output_file, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    print(f"Stats saved to {output_file}")

def plot_stats(file):
    """
    Reads saved stats from a CSV file and plots the evolution of `file*` stats over time.
    """
    stats = {}
    with open(file, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            elapsed_time = float(row["timestamp"])
            cgroup = row["cgroup"]
            stat = row["stat"]
            if (cgroup, stat) not in stats:
                stats[(cgroup, stat)] = {"timestamps": [], "values": []}
            stats[(cgroup, stat)]["timestamps"].append(elapsed_time)
            stats[(cgroup, stat)]["values"].append(sum(float(row[node]) for node in row if node.startswith("N")))

    # Plot each stat
    for (cgroup, stat), values in stats.items():
        timestamps = values["timestamps"]
        stats_values = values["values"]
        plt.figure(figsize=(10, 6))
        plt.plot(timestamps, stats_values, label=f"{stat} ({cgroup})")
        plt.xlabel("Seconds Elapsed")
        plt.ylabel("Memory (MB)")
        plt.title(f"Evolution of {stat} for {cgroup}")
        plt.legend()
        plt.tight_layout()
        plt.show()

def compare_stats(file, stat_name, cgroup1, cgroup2, cgroup3=None):
    """
    Reads saved stats from a CSV file and plots the evolution of the given stat for up to three cgroups on the same graph.
    """
    stats = {cgroup1: {"timestamps": [], "values": []}, cgroup2: {"timestamps": [], "values": []}}
    if cgroup3:
        stats[cgroup3] = {"timestamps": [], "values": []}

    with open(file, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            elapsed_time = float(row["timestamp"])
            cgroup = row["cgroup"]
            stat = row["stat"]

            if stat == stat_name and cgroup in stats:
                try:
                    # Sum NUMA node stats, ignoring missing or empty values
                    total = sum(float(row[node]) for node in row if node.startswith("N") and row[node].strip())
                    stats[cgroup]["timestamps"].append(elapsed_time)
                    stats[cgroup]["values"].append(total)
                except ValueError:
                    print(f"Skipping row with invalid data: {row}")

    # Plot comparison
    plt.figure(figsize=(10, 6))
    for cgroup, values in stats.items():
        plt.plot(values["timestamps"], values["values"], label=f"{stat_name} ({cgroup})")

    plt.xlabel("Seconds Elapsed")
    plt.ylabel("Memory (MB)")
    plt.title(f"Comparison of {stat_name} between cgroups")
    plt.legend()
    plt.tight_layout()
    plt.show()

# Main entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor and analyze memory.numa_stat for cgroups.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Monitor subcommand
    monitor_parser = subparsers.add_parser("monitor", help="Monitor and save memory.numa_stat stats.")
    monitor_parser.add_argument("--cgroups", nargs="+", required=True, help="List of cgroups and their locations in the format cgroup=user@machine:path.")
    monitor_parser.add_argument("--interval", type=int, required=True, help="Reading interval in milliseconds.")
    monitor_parser.add_argument("--duration", type=int, default=0, help="Duration to monitor in seconds (0 for infinite).")
    monitor_parser.add_argument("--output", required=True, help="Output CSV file to save stats.")

    # Plot subcommand
    plot_parser = subparsers.add_parser("plot", help="Plot stats from a saved CSV file.")
    plot_parser.add_argument("--file", required=True, help="CSV file containing saved stats.")

    # Compare subcommand
    compare_parser = subparsers.add_parser("compare", help="Compare a stat between up to three cgroups.")
    compare_parser.add_argument("--file", required=True, help="CSV file containing saved stats.")
    compare_parser.add_argument("--stat", required=True, help="Stat name to compare.")
    compare_parser.add_argument("--cgroup1", required=True, help="First cgroup to compare.")
    compare_parser.add_argument("--cgroup2", required=True, help="Second cgroup to compare.")
    compare_parser.add_argument("--cgroup3", help="Third cgroup to compare (optional).")

    args = parser.parse_args()

    if args.command == "monitor":
        cgroups = {}
        for entry in args.cgroups:
            cgroup, location = entry.split("=", 1)
            if "@" in location:
                user_machine, path = location.split(":", 1)
                user, machine = user_machine.split("@", 1)
                cgroups[cgroup] = {"user": user, "machine": machine, "path": path}
            else:
                cgroups[cgroup] = {"user": None, "machine": None, "path": location}

        print("Press Ctrl-C to stop monitoring...")
        read_numa_stats(cgroups, args.interval, args.duration, args.output)
    elif args.command == "plot":
        plot_stats(args.file)
    elif args.command == "compare":
        compare_stats(args.file, args.stat, args.cgroup1, args.cgroup2, args.cgroup3)
