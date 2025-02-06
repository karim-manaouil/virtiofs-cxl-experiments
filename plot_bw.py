import argparse
import re
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def parse_file(file_path):
    """Extracts bandwidth values from the file and computes averages based on paired sums."""
    bandwidth_data = {}
    
    with open(file_path, 'r') as file:
        current_theta = None
        current_pratio = None
        
        for line in file:
            match_theta = re.match(r'--- Running theta=(\d+\.\d+|\d+), pratio=(\d+) ---', line)
            if match_theta:
                current_theta = float(match_theta.group(1))
                current_pratio = int(match_theta.group(2))
                bandwidth_data[(current_theta, current_pratio)] = []
                continue
            
            match_read = re.search(r'bw=\d+MiB/s \((\d+)MB/s\)', line)
            if match_read and (current_theta, current_pratio) in bandwidth_data:
                bandwidth_mb = int(match_read.group(1))
                bandwidth_data[(current_theta, current_pratio)].append(bandwidth_mb)
    
    # Compute averages by summing consecutive pairs and averaging their sums
    average_bandwidth = {}
    for (theta, pratio), bws in bandwidth_data.items():
        if len(bws) >= 4:
            paired_sums = [(bws[i] + bws[i+1]) for i in range(0, len(bws), 2)]
            average_bandwidth[(theta, pratio)] = sum(paired_sums) / len(paired_sums)
        else:
            average_bandwidth[(theta, pratio)] = 0  # Fallback if not enough data
    
    return average_bandwidth

def plot_bandwidth(average_bandwidth, theta_values, pratio_values):
    """Generates a single bar plot for all specified theta and pratio values with different colors and even spacing."""
    colors = plt.cm.viridis(np.linspace(0, 1, len(theta_values)))
    
    plt.figure(figsize=(10, 6))
    bar_width = 0.3  # Adjusted width for better spacing
    num_thetas = len(theta_values)
    spacing = 0.2  # Ensures a gap between groups
    
    positions = {pratio: i * (num_thetas * bar_width + spacing) for i, pratio in enumerate(sorted(pratio_values))}
    
    for i, theta in enumerate(theta_values):
        pratio_subset = [pratio for (t, pratio) in average_bandwidth if t == theta and pratio in pratio_values]
        bandwidths = [average_bandwidth[(theta, pratio)] for pratio in pratio_subset]
        
        plt.bar([positions[p] + i * bar_width for p in pratio_subset], bandwidths, width=bar_width, label=f"Theta={theta}", color=colors[i])
    
    plt.xlabel("Pratio")
    plt.ylabel("Avg Bandwidth (MB/s)")
    plt.title("Avg Bandwidth for Different Theta Values")
    plt.xticks([positions[p] + (bar_width * (num_thetas / 2 - 0.5)) for p in pratio_values], pratio_values)
    plt.legend()
    plt.show()

def main():
    parser = argparse.ArgumentParser(description="Extract and plot bandwidth data.")
    parser.add_argument("file", type=str, help="Path to the input file")
    parser.add_argument("--theta", nargs='+', type=float, required=True, help="Theta values to plot")
    parser.add_argument("--pratio", nargs='+', type=int, required=True, help="Pratio values to include in the plot")
    args = parser.parse_args()
    
    average_bandwidth = parse_file(args.file)
    plot_bandwidth(average_bandwidth, args.theta, args.pratio)

if __name__ == "__main__":
    main()

