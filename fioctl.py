import numpy as np
import argparse
import sys
import os

"""
Theta controls the skeweness of the zipfian distribution.
Theta = 0 is equivalent to a uniform distribution.
Theta = infinity ~ the first file gets all the accesses
Theta = 0.5 ~ popular files gets most of the accesses, but gap is smaller.
Theta = [1 - 1.5] ~ typical zipfian distribution
Theta > 2 ~ Very sharp/Highly skewed distribution
"""
THETA=1.2

NR_FILES =      64
NR_WORKERS =    8
PRIVATE_RATIO = 25
MAX_FLOWS =     1000
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

def generate_zipfian_flows(nr_files, max_flows, theta):
    """
    Generate a Zipfian distribution of flows for nr_files based on theta and max_flows.

    :param nr_files: Total number of files
    :param max_flows: Total number of flows to distribute
    :param theta: Skewness parameter of the Zipfian distribution
    :return: A list where the i-th element represents the number of flows assigned to file i
    """
    # Generate Zipfian probabilities
    ranks = np.arange(1, nr_files + 1)  # Rank from 1 to nr_files
    probabilities = 1.0 / (ranks ** theta)  # Zipfian formula
    probabilities /= probabilities.sum()  # Normalize to sum to 1

    # Generate flow counts based on probabilities
    flows = np.random.multinomial(max_flows, probabilities).astype(int)

    return flows.tolist()

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
    nr_private_files = (int)(NR_FILES * PRIVATE_RATIO / 100)
    nr_shared_files = NR_FILES - nr_private_files

    nr_files_per_dir = int(NR_FILES / NR_WORKERS)
    nr_private_dirs, taken_private = count_dirs(nr_private_files, nr_files_per_dir)
    nr_shared_dirs, taken_shared  = count_dirs(nr_shared_files, nr_files_per_dir)

    print(
            f"theta={THETA}",
            f"nr_files={NR_FILES}",
            f"private_ratio={PRIVATE_RATIO}",
            f"nr_private_files={nr_private_files}",
            f"nr_shared_files={nr_shared_files}",
            f"nr_files_per_dir={nr_files_per_dir}",
            f"nr_private_dirs={nr_private_dirs}",
            f"nr_shared_dirs={nr_shared_dirs}",
            sep="\n"
    )

    flows = generate_zipfian_flows(NR_FILES, MAX_FLOWS, THETA)

    print("per-file flow distribution=", flows)

    print(FIO_GLOBAL, file = f)

    for dir in range(nr_private_dirs):
        directory = DIR + "/private/private-" + str(dir)
        if CREATE:
            if not os.path.exists(directory):
                os.makedirs(directory)
        print(
                f"[private-{dir}]",
                f"flow={flows[dir]}",
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
                f"flow={flows[nr_private_files + dir]}",
                f"directory={directory}",
                f"filename_format=shared-$filenum",
                f"nrfiles={taken_shared[dir]}",
                sep="\n",
                file = f
        )

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--private-ratio", type=int, help="% local files", required=True)
    parser.add_argument("--theta", type=float, help="zipfian distribution skewness", required=True)
    parser.add_argument("--output", type=str, help="fio job file name", required=True)

    args = parser.parse_args()

    PRIVATE_RATIO = args.private_ratio
    THETA = args.theta

    with open(args.output, "w") as f:
        generate_fio_jobs(f)
