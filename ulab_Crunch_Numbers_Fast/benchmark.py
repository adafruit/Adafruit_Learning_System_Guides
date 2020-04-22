import utime
import math
import ulab
import ulab.numerical

def timeit(f, *args, **kwargs):
    func_name = str(f).split(' ')[1]
    def new_func(*args, **kwargs):
        t = utime.ticks_us()
        result = f(*args, **kwargs)
        print('execution time: ', utime.ticks_diff(utime.ticks_us(), t), ' us')
        return result
    return new_func

def mean(values):
    return sum(values) / len(values)

@timeit
def normalized_rms(values):
    minbuf = int(mean(values))
    samples_sum = sum(
        float(sample - minbuf) * (sample - minbuf)
        for sample in values
    )

    return math.sqrt(samples_sum / len(values))

@timeit
def normalized_rms_ulab(values):
    minbuf = ulab.numerical.mean(values)
    values = values - minbuf
    samples_sum = ulab.numerical.sum(values * values)
    return math.sqrt(samples_sum / len(values))


@timeit
def normalized_std_ulab(values):
    return ulab.numerical.std(values)

@timeit
def normalized_std_ulab_iterable(values):
    return ulab.numerical.std(values)

# Instead of using sensor data, we generate some data
# The amplitude is 5000 so the rms should be around 5000/1.414 = 3536
nums_list = [int(8000 + math.sin(i) * 5000) for i in range(100)]
nums_array = ulab.array(nums_list)

print("Computing the RMS value of 100 numbers")

print('in python')
normalized_rms(nums_list)

print('\nin ulab, with some implementation in python')
normalized_rms_ulab(nums_array)

print('\nin ulab only, with ndarray')
normalized_std_ulab(nums_array)

print('\nin ulab only, with list')
normalized_std_ulab_iterable(nums_list)
