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


class EulerBeam(PDE):
    """EulerBeam

    Args:
        E (float, optional): _description_. Defaults to 1.0.
        q (float, optional): _description_. Defaults to 1.0.
        mass (float, optional): _description_. Defaults to 1.0.
        time (bool, optional): _description_. Defaults to False.
    """
    def __init__(self, E=1.0, q=1.0, mass=1.0, time=False):
        x = sympy.Symbol("x")
        u = sympy.Function("u")(x)
        u__x__x__x__x = u.diff(x).diff(x).diff(x).diff(x)

        super().__init__()
        eq = E * u__x__x__x__x + 1
        self.equations["eulerbeam"] = eq
