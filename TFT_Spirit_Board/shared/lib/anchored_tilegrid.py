"""
AnchoredTilegrid helper class
"""
try:
    from typing import Tuple
except ImportError:
    pass

from displayio import TileGrid


class AnchoredTileGrid(TileGrid):
    """
    AnchoredTileGrid extends TileGrid and allows placing the TileGrid
    relative to an arbitrary anchor point.
    """
    def __init__(self, bitmap, **kwargs):
        super().__init__(bitmap, **kwargs)
        self._anchor_point = (0, 0)

        self._anchored_position = (
            0 if "x" not in kwargs else kwargs["x"],
            0 if "y" not in kwargs else kwargs["y"]
        )

    @property
    def anchor_point(self):
        """
        The anchor point. tuple containing x and y values ranging
        from 0 to 1.
        """
        return self._anchor_point

    @anchor_point.setter
    def anchor_point(self, new_anchor_point: Tuple[float, float]) -> None:
        self._anchor_point = new_anchor_point
        # update the anchored_position using setter
        self.anchored_position = self._anchored_position

    @property
    def anchored_position(self) -> Tuple[int, int]:
        """Position relative to the anchor_point. Tuple containing x,y
        pixel coordinates."""
        return self._anchored_position

    @anchored_position.setter
    def anchored_position(self, new_position: Tuple[int, int]) -> None:
        self._anchored_position = new_position

        if (self._anchor_point is not None) and (self._anchored_position is not None):
            # Calculate (x,y) position
            self.x = int(
                new_position[0]
                - round(self._anchor_point[0] * (self.tile_width * self.width))
            )

            self.y = int(
                new_position[1]
                - round(self._anchor_point[1] * (self.tile_height * self.height))
            )
