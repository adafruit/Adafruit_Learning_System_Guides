# Cyber Flower: Digital Valentine

    'Roses are red,
     Violets are blue,
     This flower changes color,
     To show its love for you.'

Load this on a Gemma M0 running CircuitPython and it will smoothly animate
the DotStar LED between different color hues.  Touch the D0 pad and it will
cause the pixel to pulse like a heart beat.  You might need to also attach a
wire to the ground pin to ensure capacitive touch sensing can work on battery
power.  For example strip the insulation from a wire and solder it to ground,
then solder a wire (with the insulation still attached) to D0, and wrap
both wires around the stem of a flower like a double-helix.  When you touch
the wires you'll ground yourself (touching the bare ground wire) and cause
enough capacitance in the D0 wire (even though it's still insulated) to
trigger the heartbeat.  Or just leave D0 unconnected to have a nicely
animated lit-up flower!

Note that on power-up the flower will wait about 5 seconds before turning on
the LED.  During this time the board's red LED will flash and this is an
indication that it's waiting to power on.  Place the flower down so nothing
is touching it and then pick it up again after the DotStar LED starts
animating.  This will ensure the capacitive touch sensing isn't accidentally
calibrated with your body touching it (making it less accurate).
