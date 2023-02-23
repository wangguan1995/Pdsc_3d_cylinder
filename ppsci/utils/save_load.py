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

import errno
import os

import paddle

from . import logger
from .download import get_weights_path_from_url

__all__ = ["load_checkpoint", "save_checkpoint", "load_pretrain"]


def _mkdir_if_not_exist(path):
    """mkdir if not exists, ignore the exception when multiprocess mkdir together

    Args:
        path (str): Path for makedir
    """
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(path):
                logger.warning(f"{path} already created")
            else:
                raise OSError(f"Failed to mkdir {path}")


def _load_pretrain_from_path(model, path):
    """Load pretrained model from given path.

    Args:
        model (nn.Layer): Model with parameters.
        path (str, optional): Pretrained model path.
    """
    if not (os.path.isdir(path) or os.path.exists(path + '.pdparams')):
        raise ValueError(
            f"Pretrained model path {path}.pdparams does not exists."
        )

    param_state_dict = paddle.load(path + ".pdparams")
    model.set_dict(param_state_dict)
    logger.info(f"Finish loading pretrained model from {path}")


def load_pretrain(model, path):
    """Load pretrained model from given path or url.

    Args:
        model (nn.Layer): Model with parameters.
        path (str): Pretrained model url.
    """
    if path.startswith("http"):
        path = get_weights_path_from_url(path).replace(".pdparams", "")
    _load_pretrain_from_path(model, path=path)


def load_checkpoint(path, model, optimizer=None):
    """Load from checkpoint or pretrained_model

    Args:
        path (AttrDict): Path for checkpoint.
        model (nn.Layer): Model with parameters.
        optimizer (optimizer.Optimizer, optional): Optimizer for model.. Defaults to None.

    Returns:
        Dict[str, Any]: Loaded metric information.
    """
    if path and optimizer is not None:
        assert os.path.exists(path + ".pdparams"), \
            f"{path}.pdparams not exist."
        assert os.path.exists(path + ".pdopt"), \
            f"{path}.pdopt not exist."
        # load state dict
        param_dict = paddle.load(path + ".pdparams")
        optim_dict = paddle.load(path + ".pdopt")
        metric_dict = paddle.load(path + ".pdstates")
        # set state dict
        model.set_state_dict(param_dict)
        optimizer.set_state_dict(optim_dict)
        logger.info(f"Finish loading checkpoints from {path}")
        return metric_dict


def save_checkpoint(
    model,
    optimizer,
    metric,
    model_dir,
    model_name="",
    prefix="ppsci"
):
    """Save checkpoint, including model params, optimizer params, metric information.

    Args:
        model (nn.Layer): Model with parameters.
        optimizer (optimizer.Optimizer): Optimizer for model.
        metric (Dict[str, Any]): Metric information, such as {"RMSE": ...}.
        model_dir (str): Directory for chekpoint storage.
        model_name (str, optional): Name of model, such as "MLP". Defaults to "".
        prefix (str, optional): Prefix for storage. Defaults to "ppsci".
    """
    if paddle.distributed.get_rank() != 0:
        return
    model_dir = os.path.join(model_dir, model_name)
    _mkdir_if_not_exist(model_dir)
    model_path = os.path.join(model_dir, prefix)

    paddle.save(model.state_dict(), model_path + ".pdparams")
    paddle.save(optimizer.state_dict(), model_path + ".pdopt")
    paddle.save(metric, model_path + ".pdstates")
    logger.info(f"Already save model in {model_path}")
