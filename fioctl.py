import numpy as np
import argparse
import sys
import os

NR_FILES =      64
NR_WORKERS =    8
PRIVATE_RATIO = 25
MAX_FLOWS =     200
ACCESS_RATIO =  70

DIR="/srv/dax"
CREATE=0

FIO_GLOBAL = """[global]
group_reporting=1
rw=read
size=1G
bs=1M
unique_filename=0
time_based=1
runtime=60s
ramp_time=2s
iodepth=8
ioengine=libaio
direct=0
verify=0
invalidate=0
"""

def random_partition(n: int, total: int, min_value: int):
    """
    Generate `n` random integer values that sum up to `total`, with each value
    being at least `min_value`.

    :param n: Number of elements to generate.
    :param total: The total sum of generated values.
    :param min_value: The minimum value for each generated element.
    :return: A NumPy array of `n` integer values summing to `total`.
    """

    if min_value * n > total:
        raise ValueError("The total sum is too small for the minimum value constraint.")

    adjusted_total = total - min_value * n

    partitions = np.sort(np.random.uniform(0, adjusted_total, n - 1))
    values = np.diff(np.concatenate(([0], partitions, [adjusted_total])))
    values = np.round(values + min_value).astype(int)

    return values

def count_dirs(nr_type_files, nr_files_per_dir):
    nr_files = nr_type_files
    nr_dirs = 0
    taken = []

    while nr_files:
        if nr_files < nr_files_per_dir * 2:
            take = nr_files
        else:
            take = nr_files_per_dir
        nr_files -= take
        taken.append(take)
        nr_dirs += 1

    return nr_dirs, taken

def generate_fio_jobs(f):
    """
    MAX_FLOWS is divided between private and shared files according to
    ACCESS_RATIO. If ACCESS_RATIO=70, that means 70% of FLOWS are made to the
    private files. If PRIVATE_FILES=5, then it means 70% of FLOWS goes
    to 5% of the total files across the jobs.
    """
    nr_private_files = (int)(NR_FILES * PRIVATE_RATIO / 100)
    nr_shared_files = NR_FILES - nr_private_files

    max_private_flows = (int)(MAX_FLOWS * ACCESS_RATIO / 100)
    max_shared_flows = MAX_FLOWS - max_private_flows

    nr_files_per_dir = int(NR_FILES / NR_WORKERS)
    nr_private_dirs, taken_private = count_dirs(nr_private_files, nr_files_per_dir)
    nr_shared_dirs, taken_shared  = count_dirs(nr_shared_files, nr_files_per_dir)

    print(
            f"nr_files={NR_FILES}",
            f"private_ratio={PRIVATE_RATIO}",
            f"access_ratio={ACCESS_RATIO}",
            f"nr_private_files={nr_private_files}",
            f"nr_shared_files={nr_shared_files}",
            f"max_private_flows={max_private_flows}",
            f"max_shared_flows={max_shared_flows}",
            f"nr_files_per_dir={nr_files_per_dir}",
            f"nr_private_dirs={nr_private_dirs}",
            f"nr_shared_dirs={nr_shared_dirs}",
            sep="\n"
    )

    if max_private_flows:
        flows_private = random_partition(nr_private_dirs, max_private_flows, 1)
        print("private flows:", flows_private)

    if max_shared_flows:
        flows_shared = random_partition(nr_shared_dirs, max_shared_flows, 1)
        print("shared flows:", flows_shared)

    print(FIO_GLOBAL, file = f)

    for dir in range(nr_private_dirs):
        directory = DIR + "/private/private-" + str(dir)
        if CREATE:
            if not os.path.exists(directory):
                os.makedirs(directory)
        print(
                f"[private-{dir}]",
                f"flow={flows_private[dir]}",
                f"directory={directory}",
                f"filename_format=private-$filenum",
                f"nrfiles={taken_private[dir]}",
                sep="\n",
                file = f
        )

    for dir in range(nr_shared_dirs):
        directory = DIR + "/shared/shared-" + str(dir)
        if CREATE:
            if not os.path.exists(directory):
                os.makedirs(directory)
        print(
                f"[shared-{dir}]",
                f"flow={flows_shared[dir]}",
                f"directory={directory}",
                f"filename_format=shared-$filenum",
                f"nrfiles={taken_shared[dir]}",
                sep="\n",
                file = f
        )

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--private-ratio", type=int, help="% local files", required=True)
    parser.add_argument("--access-ratio", type=int, help="% access to local files", required=True)
    parser.add_argument("--output", type=str, help="fio job file name", required=True)

    args = parser.parse_args()

    PRIVATE_RATIO = args.private_ratio
    ACCESS_RATIO = args.access_ratio

    with open(args.output, "w") as f:
        generate_fio_jobs(f)
