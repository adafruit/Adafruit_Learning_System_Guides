#======
# NOTE: Run this on your PC, not the Matrix Portal.
#======
import sys
import numpy as np
from PIL import Image
from ecoulements import systeme

# load geometry
grid = np.where(np.asarray(Image.open(sys.argv[1])), 1, 0)

# add inlet / outlet flows
inlet = np.array([2] * grid.shape[0])
outlet = np.array([3] * grid.shape[0])
grid = np.hstack((inlet[:, None], grid, outlet[:, None]))

# add upper/ lower walls
wall = np.array([0] * grid.shape[1])
grid = np.vstack((wall, grid, wall))

# solve
_, VX, VY, _ = systeme.sol(grid)

# save results to file
OUTFILE = "flow_solution.py"
with open(OUTFILE , "w") as fp:
    fp.write("nan = None\n")
    fp.write("solution = {\n")
    fp.write('"VX":\n')
    fp.write(str(VX[1:-1, 1:-1].tolist()))
    fp.write(',\n"VY":\n')
    fp.write(str(VY[1:-1, 1:-1].tolist()))
    fp.write("\n}\n")

# done
print("DONE! Results saved to", OUTFILE)
