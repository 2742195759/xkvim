import multiprocessing as mp
import numpy as np
import copy
import os
import time
import sys


class GpuSchedular:
    def __init__(self, n_gpus=4):
        self.n_gpus = n_gpus 
        self.reset()
        
    def allocate(self, task_idx):
        """
        负责给GPU分配任务，尽量使得GPU任务数量尽量平均。不考虑显存大小。只是平均分任务。
        """
        assert(task_idx not in self.task2gpu)
        n_tasks = [len(val) for key, val in self.gpu2tasks.items()]
        idx = (np.array(n_tasks)*-1).argmax()  # 选择最小的
        target = [i for i in self.gpu2tasks.keys()][idx] # 选择对应的gpu id
        self.gpu2tasks[target].append(task_idx)
        self.task2gpu[task_idx] = target
        return target
    
    def reset(self):
        self.gpu2tasks = {i: [] for i in range(self.n_gpus)}
        self.task2gpu = {}
        
class AvgMemoryGpuSchedular:
    def __init__(self, n_gpus=2):
        import pynvml
        pynvml.nvmlInit()
        self.n_gpus = n_gpus
        self.reset()

    def get_used_memory(self, index):
        handle = pynvml.nvmlDeviceGetHandleByIndex(index)
        meminfo = pynvml.nvmlDeviceGetMemoryInfo(handle)
        return meminfo.used // 1024 // 1024

    def allocate(self, task_idx):
        """
        负责给GPU分配任务，尽量使得GPU任务数量尽量平均。
        计算显存大小，然后给显存最小的进行传递任务。需要额外安装库： pip install nvidia-ml-py3
        """
        import time
        time.sleep(20)
        assert(task_idx not in self.task2gpu)
        used_memorys = [self.get_used_memory(gpu_id) for gpu_id in range(self.n_gpus)]
        #print (used_memorys)
        idx = (np.array(used_memorys)*-1).argmax()  # 选择最小的
        target = idx # gpu_idx is the target gpu
        self.gpu2tasks[target].append(task_idx)
        self.task2gpu[task_idx] = target
        return target

    def reset(self):
        self.gpu2tasks = {i: [] for i in range(self.n_gpus)}
        self.task2gpu = {}

class TaskPool:
    def __init__(self, n_pool=5, arg_type='long', n_gpu=4):
        self.n_pool = n_pool
        self.arg_type = arg_type
        self.gpu_schedular = GpuSchedular(n_gpu)
        
        self.reset()
    
    def reset(self):
        self.best_param_dict = {}
    
    def collect_results(self, info):
        """
        key, val ? 
        """
        return 0, 12
    
    def _worker(self, param_dict, gpu_id):
        cmd = "CUDA_VISIBLE_DEVICES={}".format(gpu_id) + " " + self._cmd_body() + " " + self._paramdict2str(param_dict)
        print (cmd + "\n")
        r = os.popen(cmd)
        info = r.readlines()
        return self.collect_results(info)
        
    def start(self, grid_param_dict):
        """
        grad_param_dict: 
            'anchor_model: [4]'
            'reg': [0.001, 0.01, 0.1]
        """
        s = time.time()
        for key, vals in grid_param_dict.items():
            results = [None for _ in range(len(vals))]
            with mp.Pool(self.n_pool) as p:
                for idx, val in enumerate(vals):
                    tmp_dict = copy.deepcopy(self.best_param_dict)
                    tmp_dict.update({key:val})
                    results[idx] = p.apply_async(self._worker, (tmp_dict, self.gpu_schedular.allocate(idx)))
                
                output_keys = [None for _ in range(len(vals))]
                output_vals = [None for _ in range(len(vals))]
                for idx, res in enumerate(results): 
                    output_keys[idx], output_vals[idx] = res.get()
                self.gpu_schedular.reset()
                
                print ("\tTotal Output Key:", output_keys)
                idx = np.array(output_keys).argmax()
                print ("Find Better {}={}: \n{}\n".format(key, vals[idx], output_vals[idx]))
                self.best_param_dict[key] = vals[idx]
                
        print ('Time: \t', (time.time() - s), ' sec')
        print ("Best Parameters: \n{}".format(self.best_param_dict))

    def _paramdict2str(self, dic):
        params = []
        slash = "--" if self.arg_type == "long" else "-"
        for key, val in dic.items():
            assert (type(key) == str)
            params.append(slash + key)
            params.append(str(val))
        return " ".join(params)
    
    def _cmd_body(self):
        """
        将param_dict中的参数展开作为 --key val 的形式
        """
        return "head main.py"
        
    
class Cvpack2TaskPool(TaskPool):
    def _paramdict2str(self, dic):
        params = []
        slash = " "
        for key, val in dic.items():
            assert (type(key) == str)
            params.append(slash + key)
            params.append(str(val))
        return " ".join(params)
    
    def __init__(self, n_pool):
        super(Cvpack2TaskPool, self).__init__(n_pool, "long")
        
    def _cmd_body(self):
        #return "python main.py"
        #return "cvpack2_train --eval --resume "
        return "pods_train "
    
    def _get_name_from_evaluation_table(self, table_lines, search_name):
#        print (table_lines)
        assert (len(table_lines) == 3)
        val_field = table_lines[2].split('|')
        name_field = table_lines[0].split('|')
        val_field = [_.strip() for _ in val_field]
        name_field = [_.strip() for _ in name_field]
#        print (val_field)
#        print (name_field)
        for id, name in enumerate(name_field):
            if name == search_name: return float(val_field[id])
        assert (False)
    
    def collect_results(self, info):
        parameter, result, result_reward, time_cost = '', '', '', ''
        generate_info = ""
        f1_list = []
        table_str_list = []
        for line_id, line in enumerate(info):
            if 'Evaulation results for mse:' in line:
                table_str = "".join(info[line_id+1:line_id+4])
                f1 = self._get_name_from_evaluation_table(info[line_id+1:line_id+4], "mse")
                table_str_list.append(table_str)
                f1_list.append(f1)
        if len(f1_list) == 0: 
            return 0, "wrong happen\n"
        else:
            best_id = np.array(f1_list).argmax()
            return f1_list[best_id], table_str_list[best_id]
    
    
    
# 单元测试
gpu_schedular = GpuSchedular(2)
assert (gpu_schedular.allocate('task_1') == 0)
assert (gpu_schedular.allocate('task_2') == 1)
assert (gpu_schedular.allocate('task_3') == 0)
assert (gpu_schedular.allocate('task_4') == 1)
assert (gpu_schedular.allocate('task_5') == 0)
assert (gpu_schedular.allocate('task_6') == 1)
print  (gpu_schedular.gpu2tasks)
print  (gpu_schedular.task2gpu)


anchor_grid_param_dict = {
    'SOLVER.OPTIMIZER.BASE_LR': [0.0001, 0.001, 0.01, 0.1, 1.0], 
    'MODEL.BPR.DIM': [10, 20, 30, 40, 50, 60], 
    'SOLVER.OPTIMIZER.WEIGHT_DECAY': [0.00001, 0.0001, 0.001, 0.01, 0.1, 1.0], 
}

# Tuning for anchor model 
assert len(sys.argv) >= 2, "please input the args."
concurrency = int(sys.argv[1])
task = Cvpack2TaskPool(concurrency)
task.start(anchor_grid_param_dict)
#task.start(anchor_grid_param_dict)
#task.start(anchor_grid_param_dict) # for better initial values
