# SPDX-FileCopyrightText: 2025 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
this code is a very slight adjustment of Tom Whitwell's slowmovie.py to use eInk Bonnet and
7.5" monochrome display
https://github.com/TomWhitwell/SlowMovie/blob/main/slowmovie.py
"""

#!/usr/bin/env python
# -*- coding:utf-8 -*-

# example use:
# sudo -E env PATH=$PATH python3 slowmovie_adafruit.py -f Steamboat_Willie_480p.mp4 -s 1 -c 4.0

import os
import time
import sys
import random
import signal
import logging
import glob
from fractions import Fraction
import ffmpeg
import configargparse
from PIL import Image, ImageEnhance


# Adafruit display imports
import board
import busio
import digitalio
from adafruit_epd.uc8179 import Adafruit_UC8179

# Compatible video file-extensions
fileTypes = [".avi", ".mp4", ".m4v", ".mkv", ".mov"]
subtitle_fileTypes = [".srt", ".ssa", ".ass"]

# Move to the directory where this code is
os.chdir(os.path.dirname(os.path.realpath(__file__)))


# Handle when the program is killed and exit gracefully
def exithandler(signum, frame):  # pylint: disable=unused-argument
    logger.info("Exiting Program")
    if args.clear:
        # Clear display on exit if requested
        blank = Image.new("RGB", (epd.width, epd.height), (255, 255, 255))
        epd.image(blank)
        epd.display()
    sys.exit()


# Add hooks for interrupt signal
signal.signal(signal.SIGTERM, exithandler)
signal.signal(signal.SIGINT, exithandler)


def clamp(n, smallest, largest):
    return max(smallest, min(n, largest))


def generate_frame(in_filename, out_filename, time):  # pylint: disable=redefined-outer-name
    (
        ffmpeg.input(in_filename, ss=time)
        .filter("scale", "iw*sar", "ih")
        .fullscreen_filter()
        .filter("scale", width, height, force_original_aspect_ratio=1)
        .filter("pad", width, height, -1, -1)
        .overlay_filter()
        .output(out_filename, vframes=1, copyts=None)
        .overwrite_output()
        .run(capture_stdout=True, capture_stderr=True)
    )


def overlay_filter(self):
    if args.subtitles and videoInfo["subtitle_file"]:
        return self.filter("subtitles", videoInfo["subtitle_file"])
    elif args.timecode:
        return self.drawtext(
            escape_text=False,
            text="%{pts:hms}",
            fontcolor="white",
            fontsize=24,
            x="(w-text_w)/2",
            y="h-(text_h*2)",
            bordercolor="black",
            borderw=1,
        )
    return self


def fullscreen_filter(self):
    if args.fullscreen:
        if videoInfo["aspect_ratio"] > width / height:
            return self.filter("crop", f"ih*{width / height}", "ih")
        elif videoInfo["aspect_ratio"] < width / height:
            return self.filter("crop", "iw", f"iw*{height / width}")
    return self


ffmpeg.Stream.overlay_filter = overlay_filter
ffmpeg.Stream.fullscreen_filter = fullscreen_filter


# Used by configargparse to check that a file exists and is a compatible video
def check_vid(value):
    if not os.path.isfile(value):
        raise configargparse.ArgumentTypeError(f"File '{value}' does not exist")
    if not supported_filetype(value):
        raise configargparse.ArgumentTypeError(
            f"File '{value}' should be a file w supported extensions: {', '.join(fileTypes)}"
        )
    return value


def check_dir(value):
    if os.path.isdir(value):
        return value
    else:
        raise configargparse.ArgumentTypeError(f"Directory '{value}' does not exist")


def supported_filetype(file):  # pylint: disable=redefined-outer-name
    _, ext = os.path.splitext(file)
    return ext.lower() in fileTypes and not file.startswith(".")


# Get framerate, frame count, duration, and frame-time of video via FFmpeg probe
def video_info(file):  # pylint: disable=redefined-outer-name
    if file in videoInfos:
        info = videoInfos[file]
    else:
        probeInfo = ffmpeg.probe(file, select_streams="v")
        stream = probeInfo["streams"][0]

        # Calculate framerate
        avg_fps = stream["avg_frame_rate"]
        fps = float(Fraction(avg_fps))

        # Calculate duration
        duration = float(probeInfo["format"]["duration"])

        # Either get frame count or calculate it
        try:
            # Get frame count for .mp4s
            frameCount = int(stream["nb_frames"])
        except KeyError:
            # Calculate frame count for .mkvs (and maybe other formats?)
            frameCount = int(duration * fps)

        # Calculate frametime (ms each frame is displayed)
        frameTime = 1000 / fps

        subtitle_file = find_subtitles(file)
        aspect_ratio = int(stream["width"]) / int(stream["height"])

        info = {
            "frame_count": frameCount,
            "fps": fps,
            "duration": duration,
            "frame_time": frameTime,
            "subtitle_file": subtitle_file,
            "aspect_ratio": aspect_ratio,
        }

        videoInfos[file] = info
    return info


# Returns the next video in the videos directory, or the first one if there's no current video
def get_next_video(viddir, currentVideo=None):  # pylint: disable=redefined-outer-name
    # Only consider videos in the directory
    videos = sorted(list(filter(supported_filetype, os.listdir(viddir))))

    # Return None if there are no videos
    if not videos:
        return None

    if currentVideo:
        nextIndex = videos.index(currentVideo) + 1
        # If we're not wrapping around
        if not nextIndex >= len(videos):
            return os.path.join(viddir, videos[nextIndex])
    # Wrapping around or no current video: return first video
    return os.path.join(viddir, videos[0])


# Returns a random video from the videos directory
def get_random_video(viddir):  # pylint: disable=inconsistent-return-statements, redefined-outer-name
    videos = list(filter(supported_filetype, os.listdir(viddir)))
    if videos:
        return os.path.join(viddir, random.choice(videos))


# Calculate how long it'll take to play a video.
def estimate_runtime(delay, increment, frames, all=False):  # pylint: disable=redefined-builtin
    # Calculate runtime lengths in different units
    seconds = (frames / increment) * delay
    minutes = seconds / 60
    hours = minutes / 60
    days = hours / 24

    if all:
        output = f"{seconds:.1f} sec(s)/{minutes:.1f} min(s)/{hours:.1f} hour(s)/{days:.2f} day(s)"
    else:
        if minutes < 1:
            output = f"{seconds:.1f} second(s)"
        elif hours < 1:
            output = f"{minutes:.1f} minute(s)"
        elif days < 1:
            output = f"{hours:.1f} hour(s)"
        else:
            output = f"{days:.2f} day(s)"

    return output


# Check for a matching subtitle file
def find_subtitles(file):  # pylint: disable=redefined-outer-name
    if args.subtitles:
        name, _ = os.path.splitext(file)
        for i in glob.glob(name + ".*"):
            _, ext = os.path.splitext(i)
            if ext.lower() in subtitle_fileTypes:
                logger.debug(f"Found subtitle file '{i}'")  # pylint: disable=logging-fstring-interpolation
                return i
    return None


class ArgparseLogger(configargparse.ArgumentParser):
    def error(self, message):  # pylint: disable=no-self-use
        logger.error(message)
        sys.exit(1)


# Set up logging
logger = logging.getLogger()

fileHandler = logging.FileHandler("slowmovie.log")
fileHandler.setFormatter(
    logging.Formatter("[%(asctime)s] %(levelname)-8s: %(module)s : %(message)s")
)
logger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logging.Formatter("%(levelname)s:%(module)s:%(message)s"))
logger.addHandler(consoleHandler)

# parse config or CLI arguments
parser = ArgparseLogger(default_config_files=["slowmovie.conf"])
parser.add_argument(
    "-f",
    "--file",
    type=check_vid,
    help="video file to start playing; otherwise play the first file in the videos directory",
)
parser.add_argument(
    "-D",
    "--directory",
    type=check_dir,
    help="directory containing available videos to play (default: Videos)",
)
parser.add_argument(
    "-l",
    "--loop",  # pylint: disable=broad-except
    action="store_true",
    help="loop a single video; otherwise play through the files in the videos directory",
)
parser.add_argument(
    "-R",
    "--random-file",
    action="store_true",
    help="play files in a random order; otherwise play them in directory order",
)
parser.add_argument(
    "-o",
    "--loglevel",
    default="INFO",
    type=str.upper,
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    help="minimum importance-level of messages displayed & saved to logfile (default: %(default)s)",
)

# frame update controls
argsControl = parser.add_argument_group(
    "Frame Update Args", "arguments that control frame updates and display"
)
argsControl.add_argument(
    "-r",
    "--random-frames",
    action="store_true",
    help="choose a random frame every refresh",
)
argsControl.add_argument(
    "-d",
    "--delay",
    default=120,
    type=int,
    help="delay in seconds between screen updates (default: %(default)s)",
)
argsControl.add_argument(
    "-i",
    "--increment",
    default=4,
    type=int,
    help="advance INCREMENT frames each refresh (default: %(default)s)",
)
argsControl.add_argument(
    "-s", "--start", type=int, help="start playing at a specific frame"
)
argsControl.add_argument(
    "-F", "--fullscreen", action="store_true", help="expand image to fill display"
)
textOverlayGroup = argsControl.add_mutually_exclusive_group()
textOverlayGroup.add_argument(
    "-S", "--subtitles", action="store_true", help="display SRT subtitles"
)
textOverlayGroup.add_argument(
    "-t", "--timecode", action="store_true", help="display video timecode"
)

# display controls
argsEpd = parser.add_argument_group("Display Args", "arguments to modify the display")
argsEpd.add_argument(
    "-c",
    "--contrast",
    default=1.0,
    type=float,
    help="adjust image contrast (default: %(default)s)",
)
argsEpd.add_argument("-C", "--clear", action="store_true", help="clear display on exit")

args = parser.parse_args()

# Set log level
logger.setLevel(getattr(logging, args.loglevel))

# Set up Adafruit e-Paper display
logger.info("Initializing Adafruit UC8179 display...")
try:
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    ecs = digitalio.DigitalInOut(board.CE0)
    dc = digitalio.DigitalInOut(board.D22)
    srcs = None
    rst = digitalio.DigitalInOut(board.D27)
    busy = digitalio.DigitalInOut(board.D17)

    epd = Adafruit_UC8179(
        800,
        480,
        spi,
        cs_pin=ecs,
        dc_pin=dc,
        sramcs_pin=srcs,
        rst_pin=rst,
        busy_pin=busy,
        tri_color=False,
    )

    epd.set_black_buffer(1, False)
    epd.set_color_buffer(1, False)
    epd.rotation = 0

    logger.info("Display initialized successfully")
except Exception as e:  # pylint: disable=broad-except
    logger.error(f"Failed to initialize display: {e}")  # pylint: disable=logging-fstring-interpolation
    sys.exit(1)

# set width and height
width = epd.width
height = epd.height

logger.info(f"Display size: {width}x{height}")  # pylint: disable=logging-fstring-interpolation

# Set path of Videos directory and logs directory.
if args.directory:
    viddir = args.directory
else:
    viddir = "Videos"
progressdir = "progress"

# Create progress and Videos directories if missing
if not os.path.isdir(progressdir):
    os.mkdir(progressdir)
if not os.path.isdir(viddir):
    os.mkdir(viddir)

# Pick which video to play
logger.debug("Picking which video to play...")

# First, try the --file CLI argument...
logger.debug("...trying the --file argument...")
currentVideo = args.file

# ...then try a random video, if --random-file was selected...
if not currentVideo and args.random_file:
    logger.debug("...random-file mode: trying to pick a random video...")
    currentVideo = get_random_video(viddir)

# ...then try the nowPlaying file, which stores the last played video...
if not currentVideo and os.path.isfile("nowPlaying"):
    logger.debug("...trying the video in the nowPlaying file...")
    with open("nowPlaying") as file:
        lastVideo = os.path.abspath(file.readline().strip())
    if os.path.isfile(lastVideo):
        if os.path.dirname(lastVideo) == os.path.abspath(viddir) or not args.directory:
            currentVideo = lastVideo
    else:
        logger.warning(  # pylint: disable=logging-fstring-interpolation
            f"'{lastVideo}' read from nowPlaying not be found. Removing file for recreation."
        )
        os.remove("nowPlaying")

# ...then just pick the first video in the videos directory...
if not currentVideo:
    logger.debug("...trying to pick the first video in the directory...")
    currentVideo = get_next_video(viddir)

# ...if none of those worked, exit.
if not currentVideo:
    logger.critical("No videos found")
    sys.exit(1)

logger.debug(f"...picked '{currentVideo}'!")  # pylint: disable=logging-fstring-interpolation

logger.info(f"Update interval: {args.delay}")  # pylint: disable=logging-fstring-interpolation
if not args.random_frames:
    logger.info(f"Frame increment: {args.increment}")  # pylint: disable=logging-fstring-interpolation

if not (args.random_file and args.random_frames):
    # Write the current video to the nowPlaying file
    with open("nowPlaying", "w") as file:
        file.write(os.path.abspath(currentVideo))

videoFilename = os.path.basename(currentVideo)
viddir = os.path.dirname(currentVideo)

progressfile = os.path.join(progressdir, f"{videoFilename}.progress")

videoInfos = {}
videoInfo = video_info(currentVideo)

# Set up the start position based on CLI input or progressfiles if either exists
if not args.random_frames:
    if args.start:
        currentFrame = clamp(args.start, 0, videoInfo["frame_count"])
        logger.info(f"Starting at frame {currentFrame}")  # pylint: disable=logging-fstring-interpolation
    elif os.path.isfile(progressfile):
        # Read current frame from progressfile
        with open(progressfile) as log:
            try:
                currentFrame = int(log.readline())
                currentFrame = clamp(currentFrame, 0, videoInfo["frame_count"])
                logger.info(f"Resuming at frame {currentFrame}")  # pylint: disable=logging-fstring-interpolation
            except ValueError:
                currentFrame = 0
    else:
        currentFrame = 0

# Initialize lastVideo so that first time through the loop, we'll print "Playing x"
lastVideo = None

while True:
    if lastVideo != currentVideo:
        # Print a message when starting a new video
        logger.info(f"Playing '{videoFilename}'")  # pylint: disable=logging-fstring-interpolation
        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"Video info: {videoInfo['frame_count']} frames, {videoInfo['fps']:.3f}fps, duration: {time.strftime('%H:%M:%S', time.gmtime(videoInfo['duration']))}"  # pylint: disable=line-too-long
        )
        if not args.random_frames:
            logger.info(  # pylint: disable=logging-fstring-interpolation
                f"This video will take {estimate_runtime(args.delay, args.increment, videoInfo['frame_count'] - currentFrame)} to play."  # pylint: disable=line-too-long
            )

        lastVideo = currentVideo

    # Note the time when starting to display so later we can sleep for the delay value minus how long this takes  # pylint: disable=line-too-long
    timeStart = time.perf_counter()

    if args.random_frames:
        currentFrame = random.randint(0, videoInfo["frame_count"])

    msTimecode = f"{int(currentFrame * videoInfo['frame_time'])}ms"

    # Use ffmpeg to extract a frame from the movie, letterbox/pillarbox it, and put it in memory as frame.bmp  # pylint: disable=line-too-long
    generate_frame(currentVideo, "/dev/shm/frame.bmp", msTimecode)

    # Open frame.bmp in PIL
    pil_im = Image.open("/dev/shm/frame.bmp")

    # Adjust contrast if specified
    if args.contrast != 1:
        enhancer = ImageEnhance.Contrast(pil_im)
        pil_im = enhancer.enhance(args.contrast)

    pil_im = pil_im.convert("L")  # Convert to grayscale (8-bit)
    pil_im = pil_im.convert(
        "1", dither=Image.FLOYDSTEINBERG
    )  # Then to 1-bit with dithering
    pil_im = pil_im.convert("RGB")  # Convert back to RGB for Adafruit display

    # Display the image
    logger.debug(  # pylint: disable=logging-fstring-interpolation
        f"Displaying frame {int(currentFrame)} of {videoFilename} ({(currentFrame / videoInfo['frame_count']) * 100:.1f}%)"
    )
    epd.image(pil_im)
    epd.display()

    # Increment the position
    if args.random_frames:
        if args.random_file:
            # Pick a new random video
            currentVideo = get_random_video(viddir)
            videoFilename = os.path.basename(currentVideo)
            videoInfo = video_info(currentVideo)
    else:
        currentFrame += args.increment
        # If it's the end of the video
        if currentFrame > videoInfo["frame_count"]:
            if not args.loop:
                if args.random_file:
                    # Pick a new random video
                    currentVideo = get_random_video(viddir)
                else:
                    # Update currently playing video to be the next one in the Videos directory
                    currentVideo = get_next_video(viddir, videoFilename)

                # Note new video in nowPlaying file
                with open("nowPlaying", "w") as file:
                    file.write(os.path.abspath(currentVideo))

                # Update videoFilepath for new video
                videoFilename = os.path.basename(currentVideo)
                # Update progressfile location
                progressfile = os.path.join(progressdir, f"{videoFilename}.progress")
                # Update video info for new video
                videoInfo = video_info(currentVideo)

            # Reset frame to 0 (this restarts the same video if looping)
            currentFrame = 0

        # Log the new location in the proper progressfile
        with open(progressfile, "w") as log:
            log.write(str(currentFrame))

    # Adjust sleep delay to account for the time since we started updating this frame.
    timeDiff = time.perf_counter() - timeStart
    time.sleep(max(args.delay - timeDiff, 0))
