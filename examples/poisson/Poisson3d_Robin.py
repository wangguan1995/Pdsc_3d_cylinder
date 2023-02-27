# Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
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

import os

import numpy as np
import paddle
import paddlescience as psci
from paddlescience.optimizer.lr import Cosine

# Geometry
npoints = 10201
seed_num = 42
sampler_method = "uniform"
# Network
epochs = 20000
num_layers = 5
hidden_size = 20
activation = "tanh"
# Optimizer
learning_rate = 0.001
# Post-processing
solution_filename = "output_laplace3d"
vtk_filename = "output_laplace3d"
checkpoint_path = "checkpoints"

paddle.seed(seed_num)
np.random.seed(seed_num)

# time
start_time = 0.1
end_time = 1.5
time_step = 0.1
time_num = int((end_time - start_time + 0.5 * time_step) / time_step) + 1
time_tmp = np.linspace(start_time, end_time, time_num, endpoint=True)
time_array = time_tmp
print(f"time_num = {time_num}, time_array = {time_array}")

# set geometry and boundary
geo = psci.neo_geometry.Sphere((0.0, 0.0, 0.0), 1.0)
geo.add_sample_config("interior", 40000)
geo.add_sample_config("boundary", 4000)

points_dict = geo.fetch_batch_data()
geo_disc = geo
geo_disc.interior = points_dict["interior"]
geo_disc.boundary = {
    "around":
    (points_dict["boundary"], geo.boundary_normal(points_dict["boundary"])),
}
geo_disc.user = None
geo_disc.normal = {"around": None, }

# Poisson
pde = psci.pde.Poisson(dim=3, alpha=0.1, rhs=1.0, weight=1.0)

# define boundary condition dT/dn+hT-hT_amb=0
bc_around = psci.bc.Robin("T", a=1.0, b=1.0, rhs=1.0)

# set bounday condition
pde.set_bc("around", bc_around)

# define initial condition T
ic_T = psci.ic.IC("T", rhs=0.0)

# set initial condition T
pde.set_ic(ic_T)

# Network
# TODO: remove num_ins and num_outs
net = psci.network.FCNet(
    num_ins=4,
    num_outs=1,
    num_layers=num_layers,
    hidden_size=hidden_size,
    activation=activation)
# net.initialize("./checkpoint/dynamic_net_params_20000.pdparams")

# loss = psci.loss.L2()
# eq loss
cords_interior = geo_disc.interior
num_cords = cords_interior.shape[0]
print("num_cords = ", num_cords)
inputeq = psci.utils.replicate_t(time_array, cords_interior)
outeq = net(inputeq)
losseq = psci.loss.EqLoss(pde.equations[0], netout=outeq)

# ic loss
inputic = psci.utils.replicate_t([0.0], cords_interior)
print("inputic.shape: ", inputic.shape)
outic = net(inputic)
lossic = psci.loss.IcLoss(netout=outic[:, :1])

# bc loss
inputbc = geo_disc.boundary["around"][0]
inputbc_n = geo_disc.boundary["around"][1]
inputbc = psci.utils.replicate_t(time_array, inputbc)
inputbc_n = psci.utils.replicate_t(time_array, inputbc_n)
outbc = net((inputbc, inputbc_n))
lossbc = psci.loss.BcLoss("around", netout=outbc)

# total loss
loss = losseq + 10.0 * lossic + 10.0 * lossbc

# Algorithm
algo = psci.algorithm.PINNs(net=net, loss=loss)

# Optimizer
learning_rate = Cosine(
    epochs, 1, learning_rate, warmup_epoch=int(epochs * 0.05), by_epoch=True)()
opt = psci.optimizer.Adam(
    learning_rate=learning_rate, parameters=net.parameters())

# Solver
solver = psci.solver.Solver(pde=pde, algo=algo, opt=opt)
solution = solver.solve(
    num_epoch=epochs, use_dataloader=False, batch_size=[10240, 10240, 10240])
# solution = solver.predict()
for i in range(len(solution)):
    print(f"solution[{i}]={solution[i].shape}")

# Save result to vtk
dirname = "vtk_3d_robin_bs10240_PRver"
os.makedirs(f"./{dirname}", exist_ok=True)
for i in range(time_num):
    psci.visu.__save_vtk_raw(
        filename=f"./{dirname}/disk_poisson3d_output_time{i}",
        cordinate=geo_disc.interior,
        data=solution[0][i * num_cords:(i + 1) * num_cords])
