#!/bin/bash

set -o xtrace

THETAS=(0 0.5 1 1.2 1.5)
PRIVATE_RATIOS=(0 5 20 50 70 100)

TIMESTAMP=`date +%s`

RESULTS="results/fio.results.${TIMESTAMP}"

function start_host()
{
	host="vm${1}"

	sudo ./cgctl "$1"

	until ssh -o ConnectTimeout=2 "root@${host}" "exit" 2>/dev/null; do
		sleep 0.1
	done

	ssh "root@${host}" "nohup ./mount.sh </dev/null &> /dev/null &"
}

function shutdown_host()
{
	host="vm${1}"

	ssh "root@${host}" "shutdown -h now --no-wall"
}

function generate_zipf()
{
	python fioctl.py generate --theta "$1"
}

function generate_fio()
{
	python fioctl.py fio --private-ratio "$1" --output fio/jobs/main.fio >> $RESULTS
}

function run_fio()
{
	#sudo fio fio/jobs/main.fio >> $RESULTS
	./fio/bin/fio --client=fio/host.list fio/current >> $RESULTS
}

function start_monitoring() {
    nohup python stats.py monitor \
        --interval 500 --duration 0 \
        --output "stats/numa_stats_${1}.csv" \
        --cgroups \
        host=/sys/fs/cgroup/memory.numa_stat \
        virtiofsd=/sys/fs/cgroup/virtiofsd/memory.numa_stat \
        vm0-cg=/sys/fs/cgroup/virtual-vm0/memory.numa_stat \
        vm1-cg=/sys/fs/cgroup/virtual-vm1/memory.numa_stat \
        vm0=root@vm0:/sys/fs/cgroup/memory.numa_stat \
        vm1=root@vm1:/sys/fs/cgroup/memory.numa_stat \
        </dev/null &> stats_monitor.log &  # Redirect input and logs
    echo $!
}

function do_pkill()
{
	while pgrep -f "$1" > /dev/null 2>&1; do
		sudo pkill "$1" > /dev/null 2>&1
		sleep 1
	done
}

function pkill_loop()
{
	do_pkill "qemu"
	do_pkill "virtiofsd"
	do_pkill "python"
}

function drop_caches() {
    while true; do
        read -r _ line < <(numastat -m | grep FilePages)
        read -ra values <<< "$line"

        for ((i=0; i<${#values[@]}-1; i++)); do
            if (( $(echo "${values[i]} > 200" | bc -l) )); then
		echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null
                sleep 1
                continue 2
            fi
        done
        return
    done
}

function clean()
{
	printf "Cleaning.."
	pkill_loop
	printf "Pkill done..Droppping cache.."
	sudo rm /tmp/*.sock
	drop_caches
	printf "Done\n"
	sleep 1
}

function run()
{
	theta=$1
	pratio=$2

	echo "--- Running theta=$theta, pratio=$pratio ---" | tee -a $RESULTS

	for i in `seq 1 2`; do
		printf "Starting host 0.."
		start_host 0
		printf "Starting host 1.."
		start_host 1
		sleep 1
		monpid=$(start_monitoring "${TIMESTAMP}_${theta}_${pratio}_${i}")
		printf "Running.."
		run_fio
		printf "Done.."
		sleep 1
		printf "Shutting down.."
		shutdown_host 0
		shutdown_host 1
		sleep 5
		kill -INT $monpid
		sleep 5
		clean
	done
}

function main()
{
	clean

	echo "Starting.. Timestap is ${TIMESTAMP}"

	for theta in ${THETAS[@]}; do
		generate_zipf $theta
		for pratio in ${PRIVATE_RATIOS[@]}; do
			generate_fio $pratio
			run $theta $pratio
		done
	done

	echo "Done! Timestap is ${TIMESTAMP}"
}

time main
