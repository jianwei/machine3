# coding:utf-8

import cv2
import json
import time
import torch
import numpy as np
import random
import sys
import os
import threading

from yolov5.camera import LoadStreams, LoadImages
from yolov5.utils.torch_utils import select_device
from yolov5.models.experimental import attempt_load
from yolov5.utils.general import non_max_suppression, scale_coords, check_imshow
from utils.work import work_space
from utils.redis_connect import redis_connect
from strong_sort.utils.parser import get_config
from strong_sort.strong_sort import StrongSORT
from yolov5.utils.general import (LOGGER, check_img_size, non_max_suppression, scale_coords, check_requirements, cv2,
                                  check_imshow, xyxy2xywh, increment_path, strip_optimizer, colorstr, print_args, check_file)
redis = redis_connect()
# limit the number of cpus used by high performance libraries
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"


class Darknet(object):
    """docstring for Darknet"""

    def __init__(self, opt):
        self.opt = opt
        self.device = select_device(self.opt["device"])
        self.half = self.device.type != 'cpu'  # half precision only supported on CUDA
        self.model = attempt_load(self.opt["weights"])
        self.stride = int(self.model.stride.max())
        self.model.to(self.device).eval()
        self.names = self.model.module.names if hasattr(
            self.model, 'module') else self.model.names
        if self.half:
            self.model.half()
        self.source = self.opt["source"]
        self.webcam = self.source.isnumeric() or self.source.endswith('.txt') or self.source.lower().startswith(
            ('rtsp://', 'rtmp://', 'http://'))
        self.navigation_points = []
        self.vegetable_points = []
        # self.work_obj = work_space(redis)

    def preprocess(self, img):
        img = np.ascontiguousarray(img)
        img = torch.from_numpy(img).to(self.device)
        img = img.half() if self.half else img.float()  # uint8 to fp16/32
        img /= 255.0  # ???????????????
        if img.ndimension() == 3:
            img = img.unsqueeze(0)
        return img

    def detect(self, dataset):
        view_img = check_imshow()
        t0 = time.time()
        work_thread = ""
        # work_obj = work_space(redis)
        # initialize StrongSORT
        cfg = get_config()
        cfg.merge_from_file("./strong_sort/configs/strong_sort.yaml")
        strong_sort_weights = "./weights/osnet_x0_25_msmt17.pt"
        strongsort_list = []
        nr_sources = 1
        for i in range(nr_sources):
            strongsort_list.append(
                StrongSORT(
                    strong_sort_weights,
                    self.device,
                    max_dist=cfg.STRONGSORT.MAX_DIST,
                    max_iou_distance=cfg.STRONGSORT.MAX_IOU_DISTANCE,
                    max_age=cfg.STRONGSORT.MAX_AGE,
                    n_init=cfg.STRONGSORT.N_INIT,
                    nn_budget=cfg.STRONGSORT.NN_BUDGET,
                    mc_lambda=cfg.STRONGSORT.MC_LAMBDA,
                    ema_alpha=cfg.STRONGSORT.EMA_ALPHA,
                )
            )
        # print("dataset:%s,nr_sources:%s,strongsort_list:%s",dataset,nr_sources,strongsort_list)
        outputs = [None] * nr_sources
        # print("outputs:%s,nr_sources:%s,strongsort_list:%s",outputs,nr_sources,strongsort_list)

        # j=0
        curr_frames, prev_frames = [None] * nr_sources, [None] * nr_sources
        print("dataset:------", dataset)
        print("dataset:type------", type(dataset))
        for path, img, img0s, vid_cap in dataset:
            img = self.preprocess(img)
            t1 = time.time()
            pred = self.model(img, augment=self.opt["augment"])[0]  # 0.22s
            pred = pred.float()

            # track
            pred = non_max_suppression(
                pred, self.opt["conf_thres"], self.opt["iou_thres"], classes=0)

            t2 = time.time()
            pred_boxes = []
            # track end
            for i, det in enumerate(pred):
                if self.webcam:  # batch_size >= 1
                    p, s, im0, frame = path[i], '%g: ' % i, img0s[i].copy(
                    ), dataset.count
                else:
                    p, s, im0, frame = path, '', img0s, getattr(
                        dataset, 'frame', 0)
                # track------------------------1
                curr_frames[i] = im0
                if cfg.STRONGSORT.ECC:  # camera motion compensation
                    strongsort_list[i].tracker.camera_update(
                        prev_frames[i], curr_frames[i])
                prev_frames[i] = curr_frames[i]
                # track------------------------2

                s += '%gx%g ' % img.shape[2:]  # print string
                # normalization gain whwh
                gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]
                if det is not None and len(det):

                    det[:, :4] = scale_coords(
                        img.shape[2:], det[:, :4], im0.shape).round()

                    confs = det[:, 4]
                    clss = det[:, 5]
                    xywhs = xyxy2xywh(det[:, 0:4])

                    # id = output[4]
                    # print("outputs:",outputs)

                    # Print results
                    for c in det[:, -1].unique():
                        n = (det[:, -1] == c).sum()  # detections per class
                        # add to string
                        s += f"{n} {self.names[int(c)]}{'s' * (n > 1)}, "

                    item_navigation_points = []
                    item_vegetable_points = []
                    for *xyxy, conf, cls_id in det:
                        id = None
                        outputs[i] = strongsort_list[i].update(
                            xywhs.cpu(), confs.cpu(), clss.cpu(), im0)
                        for j, (output, conf) in enumerate(zip(outputs[i], confs)):
                            id = int(output[4])
                        lbl = self.names[int(cls_id)]

                        xyxy = torch.tensor(xyxy).view(1, 4).view(-1).tolist()
                        score = round(conf.tolist(), 3)
                        label = "cls_id:{},id:{},{}: {}".format(
                            cls_id, id, lbl, score)
                        x1, y1, x2, y2 = int(xyxy[0]), int(
                            xyxy[1]), int(xyxy[2]), int(xyxy[3])

                        pred_boxes.append((x1, y1, x2, y2, lbl, score))
                        if view_img:
                            self.plot_one_box(
                                # xyxy, im0, color=(255, 0, 0), label=label)
                                xyxy, im0, color=(255, 0, 0), label=label)
                        box_label = self.get_full_data(
                            xyxy, lbl, [img.shape[2:][0], img.shape[2:][1]])

                        # print("x1, y1, x2, y2:",x1, y1, x2, y2)
                        print("cls_id,uuid,id:,box_label:",
                              cls_id, id, i, box_label)
                        if (i == 1):
                            item_navigation_points.append(box_label)
                        else:
                            item_vegetable_points.append(box_label)

                    if (i == 1):
                        self.add_point(item_navigation_points, 1)
                    else:
                        self.add_point(item_vegetable_points, 2)

                    # prev_frames[i] = curr_frames[i]
                else:
                    strongsort_list[i].increment_ages()
                    LOGGER.info('No detections')

                if (work_thread == "" or not (work_thread.is_alive())):
                    print("????????????????????????work_and_run")
                    # print("self.work_obj", work_obj)
                    # work_obj.work_and_run(i)
                    # work_thread = threading.Thread(
                    # target=work_obj.work_and_run, args=(i,))
                    # work_thread.start()
                else:
                    print("?????????????????????????????????????????????,??????")

                print(f'{s}Done. ({t2 - t1:.3f}s),fps:{1/(t2-t1)}')

                if view_img:
                    cv2.imshow(str(p), cv2.resize(im0, (800, 600)))
                    if self.webcam:
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                    else:
                        cv2.waitKey(0)

    def add_point(self, item_points, flag):
        max_length = 60*3*20
        if (flag == 1):
            length = len(self.navigation_points)
            if (length > max_length):
                self.navigation_points = self.navigation_points[:max_length]
            self.navigation_points.insert(0, item_points)
            redis.set("navigation_points", json.dumps(self.navigation_points))
            return self.navigation_points
        else:
            length = len(self.vegetable_points)
            if (length > max_length):
                self.vegetable_points = self.vegetable_points[:max_length]
            self.vegetable_points.insert(0, item_points)
            redis.set("vegetable_points", json.dumps(self.vegetable_points))
            return self.vegetable_points

    def get_point(self, box):
        p1, p2 = (int(box[0]), int(box[1])), (int(box[2]), int(box[3]))
        points = [(p1[0], p1[1]), (p2[0], p1[1]),
                  (p1[0], p2[1]), (p2[0], p2[1])]
        print(points)
        return points

    def get_full_data(self, box, name, screenSize, id=0):
        box_label = {}
        p1, p2 = (int(box[0]), int(box[1])), (int(box[2]), int(box[3]))
        point = [(p1[0], p1[1]), (p2[0], p1[1]),
                 (p1[0], p2[1]), (p2[0], p2[1])]
        box_label["id"] = id
        box_label["point"] = point
        box_label["name"] = name
        box_label["time"] = time.time()
        box_label["screenSize"] = screenSize
        box_label["centerx"] = (point[0][0] + point[1][0])/2
        box_label["centery"] = (point[0][1] + point[2][1])/2
        box_label["center"] = [box_label["centerx"], box_label["centery"]]
        return box_label

    # Plotting functions
    def plot_one_box(self, x, img, color=None, label=None, line_thickness=None):
        # Plots one bounding box on image img
        tl = line_thickness or round(
            0.001 * max(img.shape[0:2])) + 1  # line thickness
        # color = color or [random.randint(0, 255) for _ in range(3)]
        color = [random.randint(0, 255) for _ in range(3)]
        # print("color:",color)
        c1, c2 = (int(x[0]), int(x[1])), (int(x[2]), int(x[3]))
        cv2.rectangle(img, c1, c2, color, thickness=tl)
        if label:
            tf = max(tl - 1, 1)  # font thickness
            t_size = cv2.getTextSize(
                label, 0, fontScale=tl / 3, thickness=tf)[0]
            c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
            cv2.rectangle(img, c1, c2, color, -1)  # filled
            cv2.putText(img, label, (c1[0], c1[1] - 2), 0, tl / 3,
                        [0, 0, 0], thickness=tf, lineType=cv2.LINE_AA)

    def stop(self):
        self.work_obj.stop()


if __name__ == "__main__":
    with open('yolov5_config.json', 'r', encoding='utf8') as fp:
        opt = json.load(fp)
        print('[INFO] YOLOv5 Config:', opt)
    darknet = Darknet(opt)
    dataset = LoadStreams(
        darknet.source, img_size=opt["imgsz"], stride=darknet.stride)
    try:
        darknet.detect(dataset)
        cv2.destroyAllWindows()
    except KeyboardInterrupt:
        darknet.stop()

    # with open('yolov5_config.json', 'r', encoding='utf8') as fp:
    #     opt = json.load(fp)
    #     print('[INFO] YOLOv5 Config:', opt)
    # darknet = Darknet(opt)
    # if darknet.webcam:
    #     # cudnn.benchmark = True  # set True to speed up constant image size inference
    #     dataset = LoadStreams(darknet.source, img_size=opt["imgsz"], stride=darknet.stride)
    # else:
    #     dataset = LoadImages(darknet.source, img_size=opt["imgsz"], stride=darknet.stride)
    # # print("dataset:",dataset)
    # darknet.detect(dataset)
    # cv2.destroyAllWindows()
