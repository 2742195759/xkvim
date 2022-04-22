import vim
import os
import os.path as osp
from .vim_utils import *

def toForwardName(name):
    if '_grad' in name:
        return name.split('_grad')[0]
    return name

def toCapitalize(name):
    if name == 'kldiv_loss': return "KLDivLoss"  # special case
    if name == 'kldiv_loss_grad': return "KLDivLossGrad"  # special case
    return "".join([ name.capitalize() for name in name.split("_") ])

class PtenFileNameManager:
    def __init__(self, root, name, type):
        self.root = root
        self.type = type
        self.name = name

    def get_kernel_header(self):
        return '%s/paddle/phi/kernels/%s_kernel.h' % (self.root, self.name)

    def get_cpu_kernel_impl(self):
        return '%s/paddle/phi/kernels/cpu/%s_kernel.cc' % (self.root, self.name)

    def get_gpu_kernel_impl(self):
        return '%s/paddle/phi/kernels/gpu/%s_kernel.cu' % (self.root, self.name)

    def get_cpu_kernel_helper(self):
        return '%s/paddle/phi/kernels/cpu/%s.h' % (self.root, self.name)

    def get_gpu_kernel_helper(self):
        return '%s/paddle/phi/kernels/gpu/%s.h' % (self.root, self.name)

    def get_kernel_signature(self):
        return '%s/paddle/phi/ops/compat/%s_sig.cc' % (self.root, toForwardName(self.name))

    def get_device_unrelated_kernel_impl(self):
        return '%s/paddle/phi/kernels/impl/%s_kernel_impl.h' % (self.root, self.name)

    def get_device_helper_func(self):
        return '%s/paddle/phi/kernels/funcs/%s.h' % (self.root, self.name)

    def get_infershape(self):
        return '%s/paddle/phi/infermate/unary.h' % (self.root)

    def get_related_path(self, full_path):
        return full_path[len(self.root)+1:]

class FluidFileNameManager:
    def __init__(self, root, name, type):
        self.root = root
        self.type = type
        self.name = name

    def get_kernel_header(self):
        return '%s/paddle/fluid/operators/%s_op.cc' % (self.root, self.name)

    def get_cpu_kernel_impl(self): 
        return '%s/paddle/fluid/operators/%s_op.h' % (self.root, self.name)

    def get_gpu_kernel_impl(self):
        return '%s/paddle/fluid/operators/%s_op.cu' % (self.root, self.name)

    def files(self):
        return [self.get_kernel_header(), self.get_cpu_kernel_impl(), self.get_gpu_kernel_impl()]

class Project : 
    def __init__(self):
        self.name = 'kthvalue_grad'
        self.type = 'backward'
        self.root = '/home/data/Paddle'
        self.pten_sm = PtenFileNameManager(self.root, self.name, self.type)
        self.fluid_sm = FluidFileNameManager(self.root, toForwardName(self.name), self.type)
        self.current_state_info = [
            "init stage",
            "create forward kernel signature stage", 
            "create forward kernel corresponding stage",
            "create", 
        ]

        self.current_state = -1

    def create_forward_signature():
        pass
        
    def next(self):
        if len(self.current_state_info) == self.current_state: 
            print("Successful ! Check your unittest and open a PR.")
            return 
        self.current_state += 1
        #getattr(self, "_stage_%d_end" % self.current_state-1)()
        getattr(self, "_stage_%d" % self.current_state)()

    def _stage_0(self):
        print ("please set the name , root, and type")

    def _stage_1(self):
        pten_kernel = """
// Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#pragma once

#include "paddle/phi/core/dense_tensor.h"

namespace phi {

template <typename T, typename Context>
// XKTODO (change name)
void %sKernel(const Context& dev_ctx,
                    const DenseTensor& x,
                    int offset,
                    int axis1,
                    int axis2,
                    DenseTensor* out);
}  // namespace phi
        """ % toCapitalize(self.name)
        print ("please set the signature of kernel:")
        if not osp.exists(self.pten_sm.get_kernel_header()):
            InsertLinesAtLocation(pten_kernel.split("\n"), Location(self.pten_sm.get_kernel_header(), 1, 1))
        EditFileWithPath(self.pten_sm.get_kernel_header())
        SearchToString("XKTODO")

    def _stage_2(self):
        print ("start change the cpu kernel input.")
        pten_kernel = RenderTemplateFile("/home/data/template/op_kernel_cpu.h", kernel_name=self.name, Kernel_name=toCapitalize(self.name))
        if not osp.exists(self.pten_sm.get_cpu_kernel_impl()):
            InsertLinesAtLocation(pten_kernel.split('\n'), Location(self.pten_sm.get_cpu_kernel_impl(), 1, 1))
        EditFileWithPath(self.pten_sm.get_cpu_kernel_impl(), 'tabe')
        EditFileWithPath(self.fluid_sm.get_cpu_kernel_impl(), 'vne')

    def _stage_3(self):
        print ("stage3: start change the gpu kernel input.")
        pten_kernel = RenderTemplateFile("/home/data/template/op_kernel_gpu.h", kernel_name=self.name, Kernel_name=toCapitalize(self.name))
        if not osp.exists(self.pten_sm.get_gpu_kernel_impl()):
            InsertLinesAtLocation(pten_kernel.split('\n'), Location(self.pten_sm.get_gpu_kernel_impl(), 1, 1))
        EditFileWithPath(self.pten_sm.get_gpu_kernel_impl(), 'tabe')
        EditFileWithPath(self.fluid_sm.get_gpu_kernel_impl(), 'vne')

    def _stage_4(self):
        print ("stage4: start change the sig.cc of kernel")
        pten_sig = RenderTemplateFile("/home/data/template/op_signature.h", kernel_name=self.name, Kernel_name=toCapitalize(self.name))
        if not osp.exists(self.pten_sm.get_kernel_signature()):
            InsertLinesAtLocation(pten_sig.split('\n'), Location(self.pten_sm.get_kernel_signature(), 1, 1))
        EditFileWithPath(self.pten_sm.get_kernel_signature(), 'tabe')
        EditFileWithPath(self.fluid_sm.get_kernel_header(), 'vne')
        SearchToString("%sOpGradMaker" % toForwardName(self.name))

    def _stage_5(self):
        print ("stage5: transfer the operator InferShape function.")
        EditFileWithPath(self.pten_sm.get_infershape(), 'tabe')
        EditFileWithPath(self.fluid_sm.get_kernel_header(), 'vne')

    def start_project(self):
        self.next()

    def create_impl_file(self):
        impl_file = self.pten_sm.get_device_unrelated_kernel_impl()
        impl_template = RenderTemplateFile("/home/data/template/op_kernel_impl.h", kernel_name=self.name, Kernel_name=toCapitalize(self.name))
        InsertIncludeStatementAtLast(CurrentEditFile(), '#include "%s"'%self.pten_sm.get_related_path(impl_file))
        SyncCurrentFile()
        if not osp.exists(impl_file):
            InsertLinesAtLocation(impl_template.split('\n'), Location(impl_file, 1, 1))
        EditFileWithPath(CurrentEditFile(), 'tabe')
        EditFileWithPath(impl_file, 'vne')

    def create_helper_file(self):
        impl_file = self.pten_sm.get_device_helper_func()
        impl_template = RenderTemplateFile("/home/data/template/op_kernel_impl.h", kernel_name=self.name, Kernel_name=toCapitalize(self.name))
        InsertIncludeStatementAtLast(CurrentEditFile(), '#include "%s"'%self.pten_sm.get_related_path(impl_file))
        SyncCurrentFile()
        if not osp.exists(impl_file):
            InsertLinesAtLocation(impl_template.split('\n'), Location(impl_file, 1, 1))
        EditFileWithPath(CurrentEditFile(), 'tabe')
        EditFileWithPath(impl_file, 'vne')

            


