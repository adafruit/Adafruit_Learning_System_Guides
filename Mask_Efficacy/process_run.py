import time
import imageio
from skimage.color import rgb2gray
import matplotlib.pyplot as plt
import numpy as np

THRESH = 0.3

RUN = int(input('Enter run number: '))

vid = imageio.get_reader('run_{:03d}.mp4'.format(RUN), 'ffmpeg')

#----------------
# MAIN PROCESSING
#----------------
frame_data = []
start = time.monotonic()
# go through video frame by frame
print("Processing", end='')
for frame in vid:
    print('.', end='', flush=True)
    frame_bin = rgb2gray(frame) > THRESH
    frame_count = np.count_nonzero(frame_bin == True)
    frame_percent = 100 * frame_count / (1920*1080)
    frame_data.append((frame_count, frame_percent))
# overall stats
avg_count = sum([x[0] for x in frame_data]) / len(frame_data)
avg_percent = 100 * avg_count / (1920*1080)

end = time.monotonic()
print("\nProcessing done in {} secs.".format(end - start))
print("Average Count = {}".format(avg_count))
print("Average Percent = {}".format(avg_percent))

#-------------
# SAVE TO FILE
#-------------
print("Saving data to file...")
with open('run_{:03d}.csv'.format(RUN), 'w') as fp:
    for frame, data in enumerate(frame_data):
        fp.write('{},{},{}\n'.format(frame, data[0], data[1]))

#---------
# PLOTTING
#---------
print("Generating plots...")
fig, ax = plt.subplots(1, figsize = (10,5))
ax.set_title("RUN {:03d}\nTHRESH = {}, AVG_CNT = {:4.2}, AVG_PER = {:.3}".format(RUN, THRESH,avg_count, avg_percent))
ax.set_xlabel("FRAME")
ax.set_ylabel("COUNT")
ax.plot([x[0] for x in frame_data])
fig.savefig('run_{:03d}_plot.png'.format(RUN))

print("DONE.")
