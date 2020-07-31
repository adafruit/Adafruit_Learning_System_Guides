worm_ratio = 40 / 1
belt_ratio = 100 / 60

steps = 200
microsteps = 64

time = 1 / (((worm_ratio * belt_ratio) * steps * microsteps) / 86400)
print(f"One step every: {time} seconds")
print(f"Delay should be: {time-.001} seconds")
