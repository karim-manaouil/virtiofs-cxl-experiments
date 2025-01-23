---

---
## Machine
---
- AMD AMD EPYC 9224
- 720GiB DDR5
- 120GiB PCIe5 CXL MXP expander (Samsung)

```
karim@seksu:~/mlc/Linux$ numactl -H  
available: 5 nodes (0-4)        
node 0 cpus: 0 1 2 3 4 5 6 7 8 9 10 11 48 49 50 51 52 53 54 55 56 57 58 59                       
node 0 size: 193283 MB  
node 0 free: 190539 MB  
node 1 cpus: 12 13 14 15 16 17 18 19 20 21 22 23 60 61 62 63 64 65 66 67 68 69 70 71  
node 1 size: 193493 MB  
node 1 free: 186990 MB  
node 2 cpus: 24 25 26 27 28 29 30 31 32 33 34 35 72 73 74 75 76 77 78 79 80 81 82 83  
node 2 size: 193529 MB  
node 2 free: 191264 MB  
node 3 cpus: 36 37 38 39 40 41 42 43 44 45 46 47 84 85 86 87 88 89 90 91 92 93 94 95  
node 3 size: 193490 MB  
node 3 free: 191164 MB  
node 4 cpus:  
node 4 size: 129017 MB  
node 4 free: 126838 MB  
node distances:  
node   0   1   2   3   4    
 0:  10  12  32  32  50    
 1:  12  10  32  32  50    
 2:  32  32  10  12  60    
 3:  32  32  12  10  60    
 4:  255  255  255  255  10
```

## Experiment
---

Idle latency and peak bandwidth
```
Measuring idle latencies for random access (in ns)...  
               Numa node  
Numa node            0       1       2       3       4  
      0         107.5   117.1   200.7   200.7   279.4  
      1         115.8   106.8   199.9   199.9   278.8  
      2         200.0   200.1   106.8   115.8   363.8  
      3         199.0   199.0   115.6   105.9   363.5  
  
Measuring Peak Injection Memory Bandwidths for the system  
Bandwidths are in MB/sec (1 MB/sec = 1,000,000 Bytes/sec)  
Using all the threads from each core if Hyper-threading is enabled  
Using traffic with the following read-write ratios  
ALL Reads        :      398309.1  
3:1 Reads-Writes :      535952.2  
2:1 Reads-Writes :      554716.7  
1:1 Reads-Writes :      457350.0  
Stream-triad like:      541992.1  
  
Measuring Memory Bandwidths between nodes within system    
Bandwidths are in MB/sec (1 MB/sec = 1,000,000 Bytes/sec)  
Using all the threads from each core if Hyper-threading is enabled  
Using Read-only traffic type  
               Numa node  
Numa node            0       1       2       3       4  
      0        99833.3 99794.2 76592.0 76746.5 17594.0  
      1        101196.7        101291.9        77137.2 77067.8 17602.0  
      2        76935.0 77621.6 101120.1        99639.8 17587.8  
      3        76710.9 77357.6 101024.9        100869.7        17585.8
```

4 MLC threads with 8GiB each. 

MLC file describing workloads:
```
# following values (reads and writes are as observed on the memory controller):  
# W2 =  2 reads and 1 write22  
# W3 =  3 reads and 1 write  
# W5 =  1 read and 1 write

0-3 R seq 8000000 dram 4
0-3 W3 rand 8000000 dram 4
0-3 W5 rand 8000000 dram 4
```

## Results
---
All results in GB/sec.

| Workload   | Ideal CXL x8 (from SMT paper [1]) | NUMA local | NUMA remote | Real CXL | Achieved % of ideal CXL | Achieved % of local NUMA | Achieved % of remote NUMA |
| ---------- | --------------------------------- | ---------- | ----------- | -------- | ----------------------- | ------------------------ | ------------------------- |
| seq R      | 25.6                              | 50         | 41          | 17.7     | 69%                     | 35.4%                    | 43%                       |
| rand 2R-1W | 41.2                              | 56.6       | 34.6        | 18.3     | 44%                     | 32%                      | 52%                       |
| rand 1R-1W | 39.6                              | 57.5       | 44.8        | 21       | 53%                     | 36%                      | 47%                       |

# Memory Bandwidth Scan
---
`./mlc --memory_bandwidth_scan -t num_threads -j numa_memory_node`

Reading 1GiB 

| NUMA/THREADS (GB/S) | 1   | 2   | 4   | 8   | 12  | 16  | 24  | 32  |
| ------------------- | --- | --- | --- | --- | --- | --- | --- | --- |
| LOCAL NUMA          | 45  | 49  | 50  | 96  | 104 | 104 | 104 | 104 |
| CXL                 | 17  | 17  | 17  | 17  | 17  | 17  | 17  | 17  |

## Refs
---
[1] https://ieeexplore.ieee.org/abstract/document/10032695