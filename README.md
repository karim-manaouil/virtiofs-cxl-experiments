# Preparation
---
## Dependency
---

## Images
---
Two Ubuntu 22.04 images vm0.img and vm1.img needs to be prepared and put into ./images directory.

## fio
---
fio needs to be built.

## Networking
---

# Runnings the guests
---
To run a guest, you just need to issue

```
sudo ./cgctl $ID
```

Where $ID is the VM's id, either 0 or 1. The script will great a cgroup and bind CPUs and memory according to the description in `cgctl` script.

Once the guests are running, ssh and run:

```
fio --server
```

From the host, change directory to `fio` and run

```
bin/fio --client=host.list jobs/job8-8-4k-1g.fio
```

You can choose other job configurations from `jobs` directory.


# Stats
---
`stats.py` allows to gather stats from `/sys/fs/cgroup/$CG/memory.numa_stats` from all specified host and guest cgroups (it supports connecting to the guests via SSH).

The following command can be run before fio is started to start sampling:

```
python stats.py monitor --cgroups virtiofsd=/sys/fs/cgroup/virtiofsd/memory.numa_stat vm0=root@vm0:/sys/fs/cgroup/memory.numa_stat vm1=root@vm1:/sys/fs/cgroup/memory.numa_stat --interval 500 --duration 0 --output numa_stats.csv
```

At the end, you can compare with 

```
python stats.py compare --file numa_stats.csv --stat file --cgroup1 virtiofsd --cgroup2 vm0 --cgroup3 vm1
```
