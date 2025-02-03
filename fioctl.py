import numpy as np
import sys

NR_FILES = 32
PRIVATE_RATIO = 25
MAX_FLOWS = 100
HOT_RATIO=70

FIO_GLOBAL = """[global]
group_reporting=1
directory=/mnt/
rw=read
size=1G
bs=1M
unique_filename=0
time_based=1
runtime=60
iodepth=8
ioengine=libaio
direct=1
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

def generate_fio_jobs(f):
    """
    MAX_FLOWS is divided between private and shared files according to
    HOT_RATIO. If HOT_RATIO=70, that means 70% of FLOWS are made to the
    private files. If PRIVATE_FILES=5, then it means 70% of FLOWS goes
    to 5% of the total files across the jobs.
    """
    nr_private_files = (int)(NR_FILES * PRIVATE_RATIO / 100)
    nr_shared_files = NR_FILES - nr_private_files

    max_private_flows = (int)(MAX_FLOWS * HOT_RATIO / 100)
    max_shared_flows = MAX_FLOWS - max_private_flows

    print(f"nr_private_files={nr_private_files}")
    print(f"nr_shared_files={nr_shared_files}")
    print(f"max_private_flows={max_private_flows}")
    print(f"max_shared_flows={max_shared_flows}")

    flows_private = random_partition(nr_private_files, max_private_flows, 1)
    flows_shared = random_partition(nr_shared_files, max_shared_flows, 1)

    print("private flows:", flows_private)
    print("shared flows:", flows_shared)

    print(FIO_GLOBAL, file=f)

    for file in range(nr_private_files):
        print("""[private-{}]\nfilename=private-{}\nflow={}""".format(
            file, file, flows_private[file]), file=f)

    for file in range(nr_shared_files):
        print("""[shared-{}]\nfilename=shared-{}\nflow={}""".format(
            file, file, flows_shared[file]), file=f)


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <output_file>")
        sys.exit(1)

    filename = sys.argv[1]

    with open(filename, "w") as f:
        generate_fio_jobs(f)
