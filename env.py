import torch


print("is_available:",torch.cuda.is_available())
print("device_count:",torch.cuda.device_count())
print("get_device_name:",torch.cuda.get_device_name())
print("current_device:",torch.cuda.current_device())
print("__version__:",torch.__version__)