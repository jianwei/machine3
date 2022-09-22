#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# from asyncio.log import logger
# from distutils.log import error

import json,re
from operator import le
import serial
import time,termios
from utils.log import log



class serial_control():
    def __init__(self):
        port = "/dev/ttyACM0"  # Arduino端口
        self.l = log(logfile="./serial_control.log")
        # self.l = log("~/serial_control.log")
        self.logger = self.l.getLogger()
        self.timeout = 0.005

        f = open(port)
        attrs = termios.tcgetattr(f)
        attrs[2] = attrs[2] & ~termios.HUPCL
        termios.tcsetattr(f, termios.TCSAFLUSH, attrs)
        f.close()

        self.ser = serial.Serial()
        self.ser.baudrate = 9600
        self.ser.port = port
        self.ser.open()  
     

        
    def close(self):
        self.ser.close()

    # {"uuid": "0ddbb5f8-1b68-11ed-af17-57a903635f20", "cmd": "RST ."}'
    # begin_time:1661395309.6998177
    # 1661395409.5343091  
    def send_cmd(self, message):
        ret = -2
        # print("---------------------------------------------------------------------------------------------")
        print("send_cmd--message:",message)
        if ("cmd" in message.keys()):
            cmd = message["cmd"]
        else:
            cmd = None
            self.logger.info("Lost message:%s", message)
        uuid = message["uuid"]
        print("send_cmd--cmd1:",cmd)
        if (cmd):
            print("send_cmd--cmd2:",cmd)
            # self.logger.info("cmd:%s,begin_time:%s",cmd,time.time())
            print("cmd:%s,begin_time:%s",cmd,time.time())
            self.ser.write(cmd.encode())
            print("cmd:end write:%s",time.time())
            try:
                cnt=1
                ret_all = ""
                time0 = time.time()
                while True:
                    cnt+=1
                    time1 = float(time.time())
                    response = self.ser.read()
                    print("response:",response)
                    time2 = float(time.time())
                    diff = time2-time1
                    if (response):
                        ret_all += str(response,"UTF-8")
                        response_arr = ret_all.splitlines()
                        ret = response_arr[len(response_arr)-1] if len(response_arr) > 0 else ""
                        self.logger.info("1--cnt:%s,send_cmd:uuid:%s,cmd:%s,ret:%s,difftime:%s,response:%s",cnt, uuid, cmd, ret, diff,ret_all)
                        # time.sleep(0.1)
                        s1 = re.compile('^(-?[1-9]|0{1}\d*)$')
                        r1 = s1.findall(ret)
                        if(len(r1)>0): 
                            self.logger.info("send_cmd:uuid:%s,cmd:%s,ret:%s,difftime:%s,response:%s", uuid, cmd, ret, diff,ret_all)
                            ret_dict = {
                                "uuid":uuid,
                                "cmd":cmd,
                                "retsult":ret,
                                
                            }
                            self.ret_dict = ret_dict
                            self.logger.info("break,cmd:%s,end_time:%s,ret_all:%s,",cmd,time.time(),ret_all)
                            return ret
                        time3 = time.time()
                        if(time3-time0>=10):
                            self.logger.info("break,time out")
                            break
            except Exception as e:
                self.l.logError("serial连接或者执行失败,reason:",e)

    def get_ret(self):
        # print("ret_dict:",self.ret_dict)
        return self.ret_dict


