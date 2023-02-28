# Copyright (c) 2023 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sympy
from .base import PDE


class Poisson(PDE):
    """Poisson

    Args:
        dim (int): Number of dimension.
        alpha (float): Alpha factor.
        time (bool): Whther equation is time-dependent.
    """
    def __init__(self, dim, alpha, time):
        self.alpha = alpha

        t = sympy.Symbol("t")
        x = sympy.Symbol("x")
        y = sympy.Symbol("y")
        z = sympy.Symbol("z")
        invars = [x, y, z][: dim]
        if time:
            invars = [t] + invars
        u = sympy.Function("u")(*invars)

        super().__init__()
        self.equations["poisson"] = \
            u.diff(t) - self.alpha * (u.diff(x).diff(x) + u.diff(y).diff(y) + u.diff(z).diff(z))
