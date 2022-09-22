#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import uuid
from utils.serial_control import serial_control
import sys
import time
ser = serial_control()


def main(cmd):
    cmd =cmd+"."
    cmd_dict = {
        "uuid": str(uuid.uuid1()),
        "cmd": cmd,
        "from": "camera",
    }
    print("cmd_dict",cmd_dict)
    ser.send_cmd(cmd_dict)
    print(ser.get_ret())



if __name__ == "__main__":
    try:
        # arg = sys.argv[1]
        # cmd = ""
        # if (int(arg)==1):
        #     cmd = "MF 15"
        # elif (int(arg)==2):
        #     cmd = "TL 15"
        # else:
        #     cmd = "STOP 0"
        # print(cmd)
        # cmd1 = "MF 150"
        # print("------------------------------------------------------------------"+cmd1+"-------------------------------------------------------------------------")
        # main(cmd1)
        # time.sleep(4)
        cmd2 = "TL 90"
        print("------------------------------------------------------------------"+cmd2+"-------------------------------------------------------------------------")
        main(cmd2)
        time.sleep(1)
        cmd3 = "STOP 0"
        print("------------------------------------------------------------------"+cmd3+"-------------------------------------------------------------------------")
        main(cmd3)
        # main("TL 90.")
        # main("STOP 0.")
        # main("STOP 0.")
    except KeyboardInterrupt:
        print("ctrl+c stop")
        # ser.close()

