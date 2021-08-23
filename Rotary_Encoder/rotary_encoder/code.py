import rotaryio
import board

encoder = rotaryio.IncrementalEncoder(board.D10, board.D9)
last_position = None
while True:
    position = encoder.position
    if last_position is None or position != last_position:
        print(position)
    last_position = position
