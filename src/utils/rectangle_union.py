from __future__ import annotations

from collections import Counter
from math import isfinite
from typing import Any, Iterable


Bounds = tuple[
    float,
    float,
    float,
    float,
]


class RectangleUnion:
    """
    Calculates the union area of axis-aligned rectangles.

    Overlapping rectangles are counted only once.

    This is used for page-profile metrics such as:

        text coverage
        image coverage
        vector coverage
        table coverage
    """

    @classmethod
    def union_area(
        cls,
        rectangles: Iterable[Any],
        clip: Any | None = None,
    ) -> float:
        """
        Return the combined non-overlapping rectangle area.

        Rectangles may be:

        - objects with left/top/right/bottom;
        - objects with x0/y0/x1/y1;
        - objects containing bbox or rect;
        - four-item tuples or lists.

        When clip is supplied, all rectangles are restricted
        to the clipping rectangle.
        """

        clip_bounds = (
            cls.normalize_rectangle(clip)
            if clip is not None
            else None
        )

        normalized_rectangles: list[Bounds] = []

        for rectangle in rectangles:
            bounds = cls.normalize_rectangle(
                rectangle
            )

            if bounds is None:
                continue

            if clip_bounds is not None:
                bounds = cls.intersection(
                    bounds,
                    clip_bounds,
                )

                if bounds is None:
                    continue

            normalized_rectangles.append(
                bounds
            )

        if not normalized_rectangles:
            return 0.0

        events: list[
            tuple[
                float,
                int,
                float,
                float,
            ]
        ] = []

        for (
            left,
            top,
            right,
            bottom,
        ) in normalized_rectangles:
            events.append(
                (
                    left,
                    1,
                    top,
                    bottom,
                )
            )

            events.append(
                (
                    right,
                    -1,
                    top,
                    bottom,
                )
            )

        events.sort(
            key=lambda event: event[0]
        )

        active_intervals: Counter[
            tuple[float, float]
        ] = Counter()

        previous_x = events[0][0]
        active_height = 0.0
        total_area = 0.0

        event_index = 0

        while event_index < len(events):
            current_x = events[
                event_index
            ][0]

            horizontal_width = max(
                current_x - previous_x,
                0.0,
            )

            total_area += (
                horizontal_width
                * active_height
            )

            while (
                event_index < len(events)
                and events[event_index][0]
                == current_x
            ):
                (
                    _,
                    event_type,
                    interval_top,
                    interval_bottom,
                ) = events[event_index]

                interval = (
                    interval_top,
                    interval_bottom,
                )

                active_intervals[
                    interval
                ] += event_type

                if (
                    active_intervals[
                        interval
                    ]
                    <= 0
                ):
                    del active_intervals[
                        interval
                    ]

                event_index += 1

            active_height = (
                cls._merged_interval_length(
                    active_intervals.keys()
                )
            )

            previous_x = current_x

        return max(
            total_area,
            0.0,
        )

    @classmethod
    def coverage(
        cls,
        rectangles: Iterable[Any],
        container: Any,
    ) -> float:
        """
        Return rectangle-union coverage within a container.

        The result is clamped between 0.0 and 1.0.
        """

        container_bounds = (
            cls.normalize_rectangle(
                container
            )
        )

        if container_bounds is None:
            return 0.0

        container_area = cls.area(
            container_bounds
        )

        if container_area <= 0.0:
            return 0.0

        covered_area = cls.union_area(
            rectangles=rectangles,
            clip=container_bounds,
        )

        return cls.clamp_ratio(
            covered_area
            / container_area
        )

    @classmethod
    def normalize_rectangle(
        cls,
        rectangle: Any,
    ) -> Bounds | None:
        """
        Convert different rectangle representations into:

            left, top, right, bottom
        """

        if rectangle is None:
            return None

        if isinstance(
            rectangle,
            (tuple, list),
        ):
            if len(rectangle) < 4:
                return None

            values = rectangle[:4]

        elif cls._has_attributes(
            rectangle,
            (
                "left",
                "top",
                "right",
                "bottom",
            ),
        ):
            values = (
                rectangle.left,
                rectangle.top,
                rectangle.right,
                rectangle.bottom,
            )

        elif cls._has_attributes(
            rectangle,
            (
                "x0",
                "y0",
                "x1",
                "y1",
            ),
        ):
            values = (
                rectangle.x0,
                rectangle.y0,
                rectangle.x1,
                rectangle.y1,
            )

        elif hasattr(
            rectangle,
            "bbox",
        ):
            nested_bbox = getattr(
                rectangle,
                "bbox",
                None,
            )

            if nested_bbox is rectangle:
                return None

            return cls.normalize_rectangle(
                nested_bbox
            )

        elif hasattr(
            rectangle,
            "rect",
        ):
            nested_rect = getattr(
                rectangle,
                "rect",
                None,
            )

            if nested_rect is rectangle:
                return None

            return cls.normalize_rectangle(
                nested_rect
            )

        else:
            return None

        try:
            left = float(values[0])
            top = float(values[1])
            right = float(values[2])
            bottom = float(values[3])

        except (
            TypeError,
            ValueError,
            IndexError,
        ):
            return None

        if not all(
            isfinite(value)
            for value in (
                left,
                top,
                right,
                bottom,
            )
        ):
            return None

        normalized_left = min(
            left,
            right,
        )

        normalized_right = max(
            left,
            right,
        )

        normalized_top = min(
            top,
            bottom,
        )

        normalized_bottom = max(
            top,
            bottom,
        )

        if (
            normalized_right
            <= normalized_left
            or normalized_bottom
            <= normalized_top
        ):
            return None

        return (
            normalized_left,
            normalized_top,
            normalized_right,
            normalized_bottom,
        )

    @classmethod
    def intersection(
        cls,
        first: Any,
        second: Any,
    ) -> Bounds | None:
        """
        Return the intersection of two rectangles.
        """

        first_bounds = (
            cls.normalize_rectangle(first)
        )

        second_bounds = (
            cls.normalize_rectangle(second)
        )

        if (
            first_bounds is None
            or second_bounds is None
        ):
            return None

        left = max(
            first_bounds[0],
            second_bounds[0],
        )

        top = max(
            first_bounds[1],
            second_bounds[1],
        )

        right = min(
            first_bounds[2],
            second_bounds[2],
        )

        bottom = min(
            first_bounds[3],
            second_bounds[3],
        )

        if (
            right <= left
            or bottom <= top
        ):
            return None

        return (
            left,
            top,
            right,
            bottom,
        )

    @classmethod
    def area(
        cls,
        rectangle: Any,
    ) -> float:
        """
        Return one rectangle's area.
        """

        bounds = cls.normalize_rectangle(
            rectangle
        )

        if bounds is None:
            return 0.0

        return (
            bounds[2] - bounds[0]
        ) * (
            bounds[3] - bounds[1]
        )

    @staticmethod
    def clamp_ratio(
        value: float,
    ) -> float:
        """
        Clamp a numeric ratio into 0.0–1.0.
        """

        return max(
            0.0,
            min(
                float(value),
                1.0,
            ),
        )

    @staticmethod
    def _merged_interval_length(
        intervals: Iterable[
            tuple[float, float]
        ],
    ) -> float:
        """
        Return the union length of vertical intervals.
        """

        sorted_intervals = sorted(
            intervals,
            key=lambda interval: (
                interval[0],
                interval[1],
            ),
        )

        if not sorted_intervals:
            return 0.0

        current_start = (
            sorted_intervals[0][0]
        )

        current_end = (
            sorted_intervals[0][1]
        )

        total_length = 0.0

        for (
            interval_start,
            interval_end,
        ) in sorted_intervals[1:]:
            if interval_start <= current_end:
                current_end = max(
                    current_end,
                    interval_end,
                )

                continue

            total_length += max(
                current_end
                - current_start,
                0.0,
            )

            current_start = (
                interval_start
            )

            current_end = (
                interval_end
            )

        total_length += max(
            current_end
            - current_start,
            0.0,
        )

        return total_length

    @staticmethod
    def _has_attributes(
        value: Any,
        attributes: tuple[str, ...],
    ) -> bool:
        return all(
            hasattr(
                value,
                attribute,
            )
            for attribute in attributes
        )