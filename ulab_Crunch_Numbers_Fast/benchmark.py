import time
import math
import ulab.numpy

def mean(values):
    return sum(values) / len(values)

def normalized_rms(values):
    minbuf = int(mean(values))
    samples_sum = sum(
        float(sample - minbuf) * (sample - minbuf)
        for sample in values
    )

    return math.sqrt(samples_sum / len(values))

def normalized_rms_ulab(values):
    # this function works with ndarrays only
    minbuf = ulab.numpy.mean(values)
    values = values - minbuf
    samples_sum = ulab.numpy.sum(values * values)
    return math.sqrt(samples_sum / len(values))

# Instead of using sensor data, we generate some data
# The amplitude is 5000 so the rms should be around 5000/1.414 = 3536
nums_list = [int(8000 + math.sin(i) * 5000) for i in range(100)]
nums_array = ulab.numpy.array(nums_list)

def timeit(s, f, n=100):
    t0 = time.monotonic_ns()
    for _ in range(n):
        x = f()
    t1 = time.monotonic_ns()
    r = (t1 - t0) * 1e-6 / n
    print("%-30s : %8.3fms [result=%f]" % (s, r, x))

print("Computing the RMS value of 100 numbers")
timeit("traditional", lambda: normalized_rms(nums_list))
timeit("ulab, with ndarray, some implementation in python", lambda: normalized_rms_ulab(nums_array))
timeit("ulab only, with list", lambda: ulab.numpy.std(nums_list))
timeit("ulab only, with ndarray", lambda: ulab.numpy.std(nums_array))
