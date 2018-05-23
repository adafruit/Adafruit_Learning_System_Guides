from express import cpx
import array
import math


def constrain(value, floor, ceiling):
    return max(floor, min(value, ceiling))


def log_scale(input_value, input_min, input_max, output_min, output_max):
    normalized_input_value = (input_value - input_min) / (input_max - input_min)
    return output_min + math.pow(normalized_input_value, 0.630957) * (output_max - output_min)


def normalized_rms(values):
    minbuf = int(sum(values) / len(values))
    return math.sqrt(sum(float(sample - minbuf) * (sample - minbuf) for sample in values) / len(values))


samples = array.array('H', [0] * 160)
input_floor = normalized_rms(samples) + 10

# Lower number means more sensitive - more LEDs will light up with less sound.
sensitivity = 500
input_ceiling = input_floor + sensitivity

peak = 0
while True:
    print(cpx.magnitude())

    c = log_scale(constrain(cpx.magnitude(), input_floor, input_ceiling),
                  input_floor, input_ceiling, 0, 10)

    cpx.pixels.fill((0, 0, 0))
    for i in range(10):
        if i < c:
            cpx.pixels[i] = (i * (255 // 10), 50, 0)
        if c >= peak:
            peak = min(c, 10 - 1)
        elif peak > 0:
            peak = peak - 1
        if peak > 0:
            cpx.pixels[int(peak)] = (80, 0, 255)
    cpx.pixels.show()
