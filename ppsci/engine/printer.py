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

from __future__ import absolute_import, division, print_function

import datetime

import paddle

from ..utils import logger
from ..utils.misc import AverageMeter


@paddle.no_grad()
def update_metric(trainer, out, batch, batch_size):
    # calc metric
    if trainer.train_metric_func is not None:
        metric_dict = trainer.train_metric_func(out, batch[-1])
        for key in metric_dict:
            if key not in trainer.output_info:
                trainer.output_info[key] = AverageMeter(key, '7.5f')
            trainer.output_info[key].update(
                float(metric_dict[key]), batch_size)


def update_loss(trainer, loss_dict, batch_size):
    # update_output_info
    for key in loss_dict:
        if key not in trainer.output_info:
            trainer.output_info[key] = AverageMeter(key, '7.5f')
        trainer.output_info[key].update(float(loss_dict[key]), batch_size)


def log_info(trainer, batch_size, epoch_id, iter_id):
    lr_msg = f"lr: {trainer.lr_sch.get_lr():.8f}"

    metric_msg = ", ".join([
        f"{key}: {trainer.output_info[key].avg:.5f}"
        for key in trainer.output_info
    ])

    time_msg = "s, ".join([
        f"{key}: {trainer.time_info[key].avg:.5f}"
        for key in trainer.time_info
    ])

    ips_msg = f"ips: {batch_size / trainer.time_info['batch_cost'].avg:.5f} samples/s"

    eta_sec = (
        (trainer.config["Global"]["epochs"] - epoch_id + 1) *
        trainer.iter_per_epoch - iter_id) * trainer.time_info["batch_cost"].avg
    eta_msg = f"eta: {str(datetime.timedelta(seconds=int(eta_sec))):s}"
    logger.info(
        f"[Train][Epoch {epoch_id}/{trainer.config['Global']['epochs']}]"
        f"[Iter: {iter_id}/{trainer.iter_per_epoch}]{lr_msg}, "
        f"{metric_msg}, {time_msg}, {ips_msg}, {eta_msg}"
    )

    logger.scaler(
        name="lr",
        value=trainer.lr_sch.get_lr(),
        step=trainer.global_step,
        writer=trainer.vdl_writer
    )

    for key in trainer.output_info:
        logger.scaler(
            name=f"train_{key}",
            value=trainer.output_info[key].avg,
            step=trainer.global_step,
            writer=trainer.vdl_writer
        )


def type_name(object):
    return object.__class__.__name__
