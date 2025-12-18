# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
import math
import random

import displayio


def svg_points(_points):
    """
    Get the SVG polygon representation of a list of points

    :param _points: the points as a list of tuples
    :return: the points as a string ready to be used in an SVG polygon
    """
    return " ".join(",".join(str(_) for _ in point) for point in _points)


def distance(point_a, point_b):
    """
    Find the distance between two points
    """
    x1, y1 = point_a
    x2, y2 = point_b
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def random_polygon():
    """
    Generate a random polygon and return the points of its vertices.

    :return: a list of the vertex points
    """

    def ccw(A, B, C):
        """Check if three points are in counter-clockwise order"""
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    def segments_intersect(A, B, C, D):
        """Check if line segment AB intersects with line segment CD"""
        # Segments intersect if endpoints are on opposite sides of each other
        return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

    def would_intersect(points, new_point):
        """Check if adding new_point would create an intersecting segment"""
        if len(points) < 2:
            return False

        new_segment_start = points[-1]
        new_segment_end = new_point

        # Check against all existing segments except the one we're extending from
        for i in range(len(points) - 1):
            existing_start = points[i]
            existing_end = points[i + 1]

            if segments_intersect(
                new_segment_start, new_segment_end, existing_start, existing_end
            ):
                return True

        # Also check if closing the polygon would create an intersection
        if len(points) >= 3:
            closing_segment_start = new_point
            closing_segment_end = points[0]

            # Check against all segments except the first and last
            for i in range(1, len(points) - 1):
                existing_start = points[i]
                existing_end = points[i + 1]

                if segments_intersect(
                    closing_segment_start,
                    closing_segment_end,
                    existing_start,
                    existing_end,
                ):
                    return True

        return False

    # choose a random number of vertices
    vertex_count = random.randint(3, 6)

    # randomly select the first point
    first_point_x = random.randint(0, 119)
    first_point_y = random.randint(0, 119)
    points = [(first_point_x, first_point_y)]

    max_attempts = 100

    for _ in range(vertex_count - 1):
        attempts = 0
        while attempts < max_attempts:
            # select a location offset from the previous point by a random amount
            offset_x = random.randint(-40, 40)
            offset_y = random.randint(-40, 40)
            new_x = max(0, min(119, points[-1][0] + offset_x))
            new_y = max(0, min(119, points[-1][1] + offset_y))
            new_point = (new_x, new_y)

            # check if it intersects any existing segments
            if not would_intersect(points, new_point):
                # if it doesn't, then add it to the list to use
                points.append(new_point)
                break

            # if it did intersect then try again up to max_attempts times
            attempts += 1

        # If we couldn't find a valid point, return what we have
        if attempts >= max_attempts:
            break

    return points


def fill_polygon(the_bmp, polygon_points, color_index):
    """
    Fill a polygon defined by points in a bitmap.

    Args:
        the_bmp: 2D bitmap array where pixels can be set via the_bmp[x, y] = 1
        polygon_points: List of (x, y) tuples defining the polygon vertices
        color_index: Index of the color to fill the polygon with
    """
    if len(polygon_points) < 3:
        return  # Need at least 3 points for a polygon

    # Find the bounding box of the polygon
    min_y = int(min(p[1] for p in polygon_points))
    max_y = int(max(p[1] for p in polygon_points))

    # For each scanline (horizontal line) in the bounding box
    for y in range(min_y, max_y + 1):
        # Find all intersections of this scanline with polygon edges
        intersections = []

        # Check each edge of the polygon
        for i in range(len(polygon_points)):
            p1 = polygon_points[i]
            p2 = polygon_points[
                (i + 1) % len(polygon_points)
            ]  # Wrap around to first point

            # Check if this edge crosses the scanline
            if (p1[1] <= y < p2[1]) or (p2[1] <= y < p1[1]):
                # Calculate x coordinate of intersection
                # Using line equation: x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                if p2[1] != p1[1]:  # Avoid division by zero
                    x_intersect = p1[0] + (y - p1[1]) * (p2[0] - p1[0]) / (
                        p2[1] - p1[1]
                    )
                    intersections.append(x_intersect)

        # Sort intersections by x coordinate
        intersections.sort()

        # Fill pixels between pairs of intersections
        # (inside polygon is between odd and even intersection indices)
        for i in range(0, len(intersections) - 1, 2):
            x_start = int(intersections[i])
            x_end = int(intersections[i + 1])

            # Fill all pixels in this span
            for x in range(x_start, x_end + 1):
                the_bmp[x, y] = color_index


def draw_snowflake(bmp, polygons, color_index):
    """
    Draw a snowflake into the bitmap by filling all the polygons that
    make up the snowflake

    :param bmp: The bitmap to draw into
    :param polygons: list of polygons to draw
    :param color_index: color index within the palette to draw
    """
    for polygon in polygons:
        fill_polygon(bmp, polygon, color_index)


class PointHighlighterCache:
    """
    Pool of point highlighter cross-hairs, shown when a user clicks on a point.
    Only creates as many as are needed and re-uses them instead of creating new
    ones.
    """

    def __init__(self, parent_group):
        self._pool = []  # Available highlighters ready for reuse
        self._active = {}  # Currently active highlighters mapped by point tuple

        self._point_highlight_bmp = displayio.Bitmap(6, 3, 3)
        self.point_highlight_palette = displayio.Palette(3)
        self.point_highlight_palette[0] = 0xFF00FF
        self.point_highlight_palette[1] = 0x000000
        self.point_highlight_palette[2] = 0x00FF00
        self.point_highlight_palette.make_transparent(0)

        self._point_highlight_bmp[1, 0] = 1
        self._point_highlight_bmp[0, 1] = 1
        self._point_highlight_bmp[2, 1] = 1
        self._point_highlight_bmp[1, 2] = 1

        self._point_highlight_bmp[1 + 3, 0] = 2
        self._point_highlight_bmp[0 + 3, 1] = 2
        self._point_highlight_bmp[2 + 3, 1] = 2
        self._point_highlight_bmp[1 + 3, 2] = 2

        self._parent_group = parent_group

    def _create_new_highlighter(self, point):
        """Create a new highlighter TileGrid positioned at the given point."""
        new_highlighter = displayio.TileGrid(
            bitmap=self._point_highlight_bmp,
            pixel_shader=self.point_highlight_palette,
            tile_width=3,
            tile_height=3,
        )
        new_highlighter.x = point[0] - 1
        new_highlighter.y = point[1] - 1
        self._parent_group.append(new_highlighter)
        return new_highlighter

    def get_highlighter(self, point):
        """
        Get a highlighter for the given point, either from the pool or create new.

        Args:
            point: Tuple (x, y) representing the point to highlight

        Returns:
            TileGrid highlighter positioned at the point
        """
        point_key = tuple(point)  # Ensure it's a tuple for dict key

        # If we already have an active highlighter for this point, return it
        if point_key in self._active:
            return self._active[point_key]

        # Try to get from pool first
        if self._pool:
            highlighter = self._pool.pop()
            highlighter.x = point[0] - 1
            highlighter.y = point[1] - 1
        else:
            # Create new if pool is empty
            highlighter = self._create_new_highlighter(point)

        # Mark as active
        self._active[point_key] = highlighter
        highlighter.hidden = False
        return highlighter

    def release_highlighter(self, point):
        """
        Release a highlighter back to the pool for the given point.

        Args:
            point: Tuple (x, y) of the highlighter to release

        Returns:
            The released TileGrid or None if point wasn't active
        """
        point_key = tuple(point)

        if point_key in self._active:
            highlighter = self._active.pop(point_key)
            highlighter.hidden = True
            self._pool.append(highlighter)
            return highlighter
        return None

    def release_all(self):
        """Release all active highlighters back to the pool."""
        for highlighter in self._active.values():
            highlighter.hidden = True
            self._pool.append(highlighter)
        self._active.clear()

    def clear_pool(self):
        """Clear the pool of cached highlighters (useful for memory management)."""
        self._pool.clear()

    def get_active_highlighters(self):
        """
        Get all currently active highlighters.

        Returns:
            List of active TileGrid highlighters
        """
        return list(self._active.values())

    def get_active_points(self):
        """
        Get all points that currently have active highlighters.

        Returns:
            List of point tuples
        """
        return list(self._active.keys())

    def is_active(self, point):
        """Check if a point currently has an active highlighter."""
        return tuple(point) in self._active

    @property
    def pool_size(self):
        """Number of highlighters available in the pool."""
        return len(self._pool)

    @property
    def active_count(self):
        """Number of currently active highlighters."""
        return len(self._active)

    @property
    def total_count(self):
        """Total number of highlighters (active + pooled)."""
        return len(self._active) + len(self._pool)
