
- AMD EPYC 4th gen, 4 NUMA nodes 128GB each
- Samsung CXL 128GB Memory Expander, 17.5GB/s
- Storage: Seagate BarraCuda hard drive 4TB 5400RPM, 120MB/s
## Commands
---

```
$QEMU \  
       -enable-kvm \  
       -M virt \  
       -cpu host \  
       -smp 8 \  
       -m 32G \  
       -object memory-backend-file,id=mem0,mem-path=memory-file-$VM,size=32G,share=on \  
       -numa node,memdev=mem0 \  
       -kernel $VMLINUX \  
       -append "${kcmdline[*]}" \  
       -drive format=raw,file="$VM.img",if=virtio \  
       -netdev tap,id=mynet1,vhost=on,queues="$SMP",ifname="$TAP",script=no,downscript=no \  
       -device virtio-net,netdev=mynet1,mq=on,vectors="$SMP",mac="$MAC" \  
       -chardev socket,id=char0,path=/tmp/"$VM.sock" \  
       -device vhost-user-fs-pci,queue-size=1024,chardev=char0,tag=daxfs,cache-size=16G \  
       -nographic
```

```
fio --name=read_throughput --directory=/mnt --numjobs=8 --size=8G --time_based --runtime=60s --ramp_time=2s --ioengine=libaio --direct=0 --verify=0 --bs=1M --iodepth=64 --rw=read --group_reporting=1 --invalidate=0
```
# virtiofsd on CXL
---
- virtiofsd -o cache={none|always} pinned on CXL, exporting /dev/sdb3
- 32 GB guest V,  cpu+memory pinned on NUMA node 1
- fio 8 threads x 8GB --direct=0 --invalidate=0
- Hyperthreading: off
- Autonuma: off
- cpufreq: performance
- hugepages: 1G

| Run          | First run | Second run | Third run | Fourth run | file cache size at end of tests |
| ------------ | --------- | ---------- | --------- | ---------- | ------------------------------- |
| cache=none   | 89MB/s    | 2GB/s      | 5.1GB/s   | 5.1GB/s    | 180MiB                          |
| cache=always | 70MB/s    | 172MB/s    | 30GB/s    | 32GB/s     | 8GB                             |

NB: no invalidation or drop_cache between the runs

# Paper Experiments
---
- Each experiment has a throughput table and includes a graph of the evolution of the amount of file pages `file` on the host (`virtiofsd`) and the two guests (`vm0` and `vm1`) 

- The job file used is https://github.com/karim-manaouil/virtiofs-cxl-experiments/blob/main/fio/jobs/job8-8-4k-1g.fio
- In short, it creates 8 jobs, each accessing 8x1G files (64G in total). 

- The files are created with `filectl` and distributed across CXL/DRAM with x1.5/x0.5 ratios.

- Guest caching knob is controlled from `virtiofsd` with `-o cache` option.
## Experiment 1)
---
2 VMs, each one reading the same file over virtiofs, cache=None, O_DIRECT (no host no guest)

| VM                | VM0  | VM1  |
| ----------------- | ---- | ---- |
| Throughput (MB/s) | 72.4 | 72.5 |

![](exp1.png)
