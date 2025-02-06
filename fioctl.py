import numpy as np
import argparse
import json
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

NR_FILES =      12
PRIVATE_RATIO = 25
MAX_FLOWS =     100
ACCESS_RATIO =  70

DIR="/srv/dax"
CREATE=1

FLOWS_FILE="fio-flows.json"

FIO_GLOBAL = """[global]
group_reporting=1
rw=read
size=6G
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
    #flows = -np.sort(-flows)

    return flows.tolist()

def generate_fio_jobs(fio_file):
    nr_private_files = (int)(NR_FILES * PRIVATE_RATIO / 100)
    nr_shared_files = NR_FILES - nr_private_files

    print(
            f"theta={THETA}",
            f"nr_files={NR_FILES}",
            f"private_ratio={PRIVATE_RATIO}",
            f"nr_private_files={nr_private_files}",
            f"nr_shared_files={nr_shared_files}",
            sep="\n"
    )

    with open(FLOWS_FILE, "r") as f:
        flows = json.load(f)

    print("per-file flow distribution=", flows)

    print(FIO_GLOBAL, file = fio_file)

    for file in range(nr_private_files):
        directory = DIR + "/private/"
        filename = directory + "private-" + str(file)
        if CREATE:
            if not os.path.exists(directory):
                os.makedirs(directory)
        print(
                f"[private-{file}]",
                f"flow={flows[file]}",
                f"filename={filename}",
                sep="\n",
                file = fio_file
        )

    for file in range(nr_shared_files):
        directory = DIR + "/shared/"
        filename = directory + "shared-" + str(file)
        if CREATE:
            if not os.path.exists(directory):
                os.makedirs(directory)
        print(
                f"[shared-{file}]",
                f"flow={flows[nr_private_files + file]}",
                f"filename={filename}",
                sep="\n",
                file = fio_file
        )

def generate_flows():
    nr_private_files = (int)(NR_FILES * PRIVATE_RATIO / 100)
    nr_shared_files = NR_FILES - nr_private_files

    flows = generate_zipfian_flows(nr_private_files + nr_shared_files, MAX_FLOWS, THETA)

    with open(FLOWS_FILE, "w") as f:
        json.dump(flows, f)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen_parser = subparsers.add_parser("generate", help="Generate distribution into file")
    gen_parser.add_argument("--theta", type=float, help="zipfian distribution skewness", required=True)

    fio_parser = subparsers.add_parser("fio", help="Generate fio")
    fio_parser.add_argument("--private-ratio", type=int, help="% local files", required=True)
    fio_parser.add_argument("--output", type=str, help="fio job file name", required=True)

    args = parser.parse_args()

    if args.command == "generate":
        THETA = args.theta
        generate_flows()
    elif args.command == "fio":
        PRIVATE_RATIO = args.private_ratio
        with open(args.output, "w") as f:
            generate_fio_jobs(f)
