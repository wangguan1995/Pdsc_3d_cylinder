# Copyright (c) 2023 PaddlePaddle Authors. All Rights Reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Code below is heavily based on [https://github.com/lululxvi/deepxde](https://github.com/lululxvi/deepxde)
"""

import numpy as np
import paddle

from ppsci.geometry import geometry


class CSGUnion(geometry.Geometry):
    """Construct an object by CSG Union(except for Mesh)."""

    def __init__(self, geom1, geom2):
        if geom1.ndim != geom2.ndim:
            raise ValueError(
                f"{geom1}.ndim({geom1.ndim}) should be equal to "
                f"{geom2}.ndim({geom1.ndim})"
            )
        super().__init__(
            geom1.ndim,
            (
                np.minimum(geom1.bbox[0], geom2.bbox[0]),
                np.maximum(geom1.bbox[1], geom2.bbox[1]),
            ),
            geom1.diam + geom2.diam,
        )
        self.geom1 = geom1
        self.geom2 = geom2
        self.area = (
            geom1.area + geom2.area
        )  # assum no area intersection, fix while sampling

        n = 1000
        n1 = int(
            self.geom1.perimeter / (self.geom1.perimeter + self.geom2.perimeter) * n
        )
        n2 = n - n1
        geom1_boundary_points = self.geom1.random_boundary_points(n1, random="pseudo")
        geom1_boundary_points = geom1_boundary_points[
            ~self.geom2.is_inside(geom1_boundary_points)
        ]

        geom2_boundary_points = self.geom2.random_boundary_points(n2, random="pseudo")
        geom2_boundary_points = geom2_boundary_points[
            ~self.geom1.is_inside(geom2_boundary_points)
        ]

        points = np.concatenate((geom1_boundary_points, geom2_boundary_points))
        points = np.random.permutation(points)
        self.perimeter = (
            (self.geom1.perimeter + self.geom2.perimeter) * len(points) / (n1 + n2)
        )

    def is_inside(self, x):
        return np.logical_or(self.geom1.is_inside(x), self.geom2.is_inside(x))

    def on_boundary(self, x):
        return np.logical_or(
            np.logical_and(self.geom1.on_boundary(x), ~self.geom2.is_inside(x)),
            np.logical_and(self.geom2.on_boundary(x), ~self.geom1.is_inside(x)),
        )

    def boundary_normal(self, x):
        return np.logical_and(self.geom1.on_boundary(x), ~self.geom2.is_inside(x))[
            :, np.newaxis
        ] * self.geom1.boundary_normal(x) + np.logical_and(
            self.geom2.on_boundary(x), ~self.geom1.is_inside(x)
        )[
            :, np.newaxis
        ] * self.geom2.boundary_normal(
            x
        )

    def random_points(self, n, random="pseudo"):
        x = np.empty(shape=(n, self.ndim), dtype=paddle.get_default_dtype())
        _size = 0
        while _size < n:
            points = (
                np.random.rand(n, self.ndim) * (self.bbox[1] - self.bbox[0])
                + self.bbox[0]
            )
            points = points[self.is_inside(points)]

            if len(points) > n - _size:
                points = points[: n - _size]
            x[_size : _size + len(points)] = points
            _size += len(points)
        return x

    def random_boundary_points(self, n, random="pseudo"):
        x = np.empty(shape=(n, self.ndim), dtype=paddle.get_default_dtype())
        _size = 0
        while _size < n:
            n1 = int(self.geom1.perimeter / self.perimeter * n)
            n2 = n - n1
            geom1_boundary_points = self.geom1.random_boundary_points(n1, random=random)
            geom1_boundary_points = geom1_boundary_points[
                ~self.geom2.is_inside(geom1_boundary_points)
            ]

            geom2_boundary_points = self.geom2.random_boundary_points(n2, random=random)
            geom2_boundary_points = geom2_boundary_points[
                ~self.geom1.is_inside(geom2_boundary_points)
            ]

            points = np.concatenate((geom1_boundary_points, geom2_boundary_points))
            points = np.random.permutation(points)

            self.perimeter = (
                (self.geom1.perimeter + self.geom2.perimeter) * len(points) / (n1 + n2)
            )

            if len(points) > n - _size:
                points = points[: n - _size]
            x[_size : _size + len(points)] = points
            _size += len(points)
        return x

    def periodic_point(self, x, component):
        x = np.copy(x)
        on_boundary_geom1 = np.logical_and(
            self.geom1.on_boundary(x), ~self.geom2.is_inside(x)
        )
        x[on_boundary_geom1] = self.geom1.periodic_point(x, component)[
            on_boundary_geom1
        ]
        on_boundary_geom2 = np.logical_and(
            self.geom2.on_boundary(x), ~self.geom1.is_inside(x)
        )
        x[on_boundary_geom2] = self.geom2.periodic_point(x, component)[
            on_boundary_geom2
        ]
        return x

    def sdf_func(self, points: np.ndarray) -> np.ndarray:
        sdf_geom1 = self.geom1.sdf_func(points)
        sdf_geom2 = self.geom2.sdf_func(points)
        return np.minimum(sdf_geom1, sdf_geom2)


class CSGDifference(geometry.Geometry):
    """Construct an object by CSG Difference."""

    def __init__(self, geom1, geom2):
        if geom1.ndim != geom2.ndim:
            raise ValueError(
                f"{geom1}.ndim({geom1.ndim}) should be equal to "
                f"{geom2}.ndim({geom1.ndim})."
            )
        super().__init__(geom1.ndim, geom1.bbox, geom1.diam)
        self.geom1 = geom1
        self.geom2 = geom2
        self.area = (
            geom1.area - geom2.area
        )  # assum full area intersection, fix while sampling

    def is_inside(self, x):
        return np.logical_and(self.geom1.is_inside(x), ~self.geom2.is_inside(x))

    def on_boundary(self, x):
        return np.logical_or(
            np.logical_and(self.geom1.on_boundary(x), ~self.geom2.is_inside(x)),
            np.logical_and(self.geom1.is_inside(x), self.geom2.on_boundary(x)),
        )

    def boundary_normal(self, x):
        return np.logical_and(self.geom1.on_boundary(x), ~self.geom2.is_inside(x))[
            :, np.newaxis
        ] * self.geom1.boundary_normal(x) + np.logical_and(
            self.geom1.is_inside(x), self.geom2.on_boundary(x)
        )[
            :, np.newaxis
        ] * -self.geom2.boundary_normal(
            x
        )

    def random_points(self, n, random="pseudo"):
        x = np.empty(shape=(n, self.ndim), dtype=paddle.get_default_dtype())
        _size = 0
        while _size < n:
            tmp = self.geom1.random_points(n, random=random)
            tmp = tmp[~self.geom2.is_inside(tmp)]

            if len(tmp) > n - _size:
                tmp = tmp[: n - _size]
            x[_size : _size + len(tmp)] = tmp
            _size += len(tmp)
        return x

    def random_boundary_points(self, n, random="pseudo"):
        x = np.empty(shape=(n, self.ndim), dtype=paddle.get_default_dtype())
        _size = 0
        while _size < n:
            geom1_boundary_points = self.geom1.random_boundary_points(n, random=random)
            geom1_boundary_points = geom1_boundary_points[
                ~self.geom2.is_inside(geom1_boundary_points)
            ]

            geom2_boundary_points = self.geom2.random_boundary_points(n, random=random)
            geom2_boundary_points = geom2_boundary_points[
                self.geom1.is_inside(geom2_boundary_points)
            ]

            points = np.concatenate((geom1_boundary_points, geom2_boundary_points))
            points = np.random.permutation(points)

            if len(points) > n - _size:
                points = points[: n - _size]
            x[_size : _size + len(points)] = points
            _size += len(points)
        return x

    def periodic_point(self, x, component):
        x = np.copy(x)
        on_boundary_geom1 = np.logical_and(
            self.geom1.on_boundary(x), ~self.geom2.is_inside(x)
        )
        x[on_boundary_geom1] = self.geom1.periodic_point(x, component)[
            on_boundary_geom1
        ]
        return x

    def sdf_func(self, points: np.ndarray) -> np.ndarray:
        # geom1 - geom2
        sdf_geom1 = self.geom1.sdf_func(points)
        sdf_geom2 = self.geom2.sdf_func(points)
        return np.maximum(sdf_geom1, -sdf_geom2)


class CSGIntersection(geometry.Geometry):
    """Construct an object by CSG Intersection."""

    def __init__(self, geom1, geom2):
        if geom1.ndim != geom2.ndim:
            raise ValueError(
                f"{geom1}.ndim({geom1.ndim}) should be equal to "
                f"{geom2}.ndim({geom1.ndim})"
            )
        super().__init__(
            geom1.ndim,
            (
                np.maximum(geom1.bbox[0], geom2.bbox[0]),
                np.minimum(geom1.bbox[1], geom2.bbox[1]),
            ),
            min(geom1.diam, geom2.diam),
        )
        self.geom1 = geom1
        self.geom2 = geom2

    def is_inside(self, x):
        return np.logical_and(self.geom1.is_inside(x), self.geom2.is_inside(x))

    def on_boundary(self, x):
        return np.logical_or(
            np.logical_and(self.geom1.on_boundary(x), self.geom2.is_inside(x)),
            np.logical_and(self.geom1.is_inside(x), self.geom2.on_boundary(x)),
        )

    def boundary_normal(self, x):
        return np.logical_and(self.geom1.on_boundary(x), self.geom2.is_inside(x))[
            :, np.newaxis
        ] * self.geom1.boundary_normal(x) + np.logical_and(
            self.geom1.is_inside(x), self.geom2.on_boundary(x)
        )[
            :, np.newaxis
        ] * self.geom2.boundary_normal(
            x
        )

    def random_points(self, n, random="pseudo"):
        x = np.empty(shape=(n, self.ndim), dtype=paddle.get_default_dtype())
        _size = 0
        while _size < n:
            points = self.geom1.random_points(n, random=random)
            points = points[self.geom2.is_inside(points)]

            if len(points) > n - _size:
                points = points[: n - _size]
            x[_size : _size + len(points)] = points
            _size += len(points)
        return x

    def random_boundary_points(self, n, random="pseudo"):
        x = np.empty(shape=(n, self.ndim), dtype=paddle.get_default_dtype())
        _size = 0
        while _size < n:
            geom1_boundary_points = self.geom1.random_boundary_points(n, random=random)
            geom1_boundary_points = geom1_boundary_points[
                self.geom2.is_inside(geom1_boundary_points)
            ]

            geom2_boundary_points = self.geom2.random_boundary_points(n, random=random)
            geom2_boundary_points = geom2_boundary_points[
                self.geom1.is_inside(geom2_boundary_points)
            ]

            points = np.concatenate((geom1_boundary_points, geom2_boundary_points))
            points = np.random.permutation(points)

            if len(points) > n - _size:
                points = points[: n - _size]
            x[_size : _size + len(points)] = points
            _size += len(points)
        return x

    def periodic_point(self, x, component):
        x = np.copy(x)
        on_boundary_geom1 = np.logical_and(
            self.geom1.on_boundary(x), self.geom2.is_inside(x)
        )
        x[on_boundary_geom1] = self.geom1.periodic_point(x, component)[
            on_boundary_geom1
        ]
        on_boundary_geom2 = np.logical_and(
            self.geom2.on_boundary(x), self.geom1.is_inside(x)
        )
        x[on_boundary_geom2] = self.geom2.periodic_point(x, component)[
            on_boundary_geom2
        ]
        return x
