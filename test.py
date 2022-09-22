# coding:utf-8
from yolov5.camera import LoadStreams
dataset = LoadStreams()

print("dataset:",dataset)
for path, img, img0s, vid_cap in dataset:
    print("path:",path)
