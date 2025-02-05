#!/bin/bash

THETAS=(0 0.5 1 1.2 1.5)
PRIVATE_RATIOS=(0 5 20 50 70 100)

TIMESTAMP=`date +%s`

RESULTS="fio.results.${TIMESTAMP}"

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

function generate()
{
	theta=$1
	pratio=$2

	python fioctl.py \
		--private-ratio "$pratio" \
		--theta "$theta" \
		--output fio/jobs/main.fio >> $RESULTS
}

function run()
{
	theta=$1
	pratio=$2

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

function drop_caches_loop()
{
	for i in `seq 1 5`; do
		echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null
		sleep 1
	done
}

function generate_and_run()
{
	theta=$1
	pratio=$2

	echo "--- Running theta=$theta, pratio=$pratio ---" | tee -a $RESULTS

	generate $theta $pratio

	for i in `seq 1 2`; do
		printf "Starting host 0.."
		start_host 0
		printf "Starting host 1.."
		start_host 1
		sleep 0.5
		monpid=$(start_monitoring "${TIMESTAMP}_${theta}_${pratio}_${i}.csv")
		printf "Running.."
		run $theta $pratio
		printf "Done.."
		sleep 1
		shutdown_host 0
		shutdown_host 1
		printf "Shutting down.."
		sleep 5
		kill -INT $monpid
		printf "Waiting for monitor.."
		wait $monpid >/dev/null 2>&1
		pkill_loop
		printf "Pkill done..Droppping cache.."
		drop_caches_loop
		printf "Done\n"
		sleep 5
	done
}

function main()
{
	sudo pkill qemu
	sleep 0.5
	echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null

	for theta in ${THETAS[@]}; do
		for pratio in ${PRIVATE_RATIOS[@]}; do
			generate_and_run $theta $pratio
		done
	done

	echo "Done! Timestap is ${TIMESTAMP}"
}

time main
