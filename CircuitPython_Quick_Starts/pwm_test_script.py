import board
import pulseio

for pin_name in dir(board):
    pin = getattr(board, pin_name)
    try:
        p = pulseio.PWMOut(pin)
        p.deinit()
        print("PWM on:", pin_name)
    except ValueError:
        print("No PWM on:", pin_name)
    except RuntimeError:
        print("Timers in use:", pin_name)
