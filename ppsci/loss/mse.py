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

import paddle.nn.functional as F

from .base import LossBase


class MSELoss(LossBase):
    def __init__(self, reduction="mean"):
        super().__init__()
        assert reduction in ["mean", "sum"], \
            f"reduction must be 'mean' or 'sum', but got {reduction}"
        self.reduction = reduction

    def forward(self, output_dict, label_dict, weight_dict=None):
        losses = 0.0
        for key in label_dict:
            loss = F.mse_loss(
                output_dict[key],
                label_dict[key],
                "none"
            )
            if weight_dict is not None:
                loss *= weight_dict[key]
            if self.reduction == "sum":
                loss = loss.sum()
            elif self.reduction == "mean":
                loss = loss.mean()
            losses += loss
        return losses
