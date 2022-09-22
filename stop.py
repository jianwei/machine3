#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import uuid
from utils.serial_control import serial_control
import sys
ser = serial_control()

def main(cmd):
    cmd_dict = {
        "uuid": str(uuid.uuid1()),
        "cmd": cmd,
        "from": "camera",
    }
    ser.send_cmd(cmd_dict)
    print(ser.get_ret())



if __name__ == "__main__":
    try:
        arg = sys.argv[1]
        cmd = ""
        if (int(arg)==1):
            cmd = "MF 15"
        elif (int(arg)==2):
            cmd = "TL 15"
        else:
            cmd = "STOP 0"
        print(cmd)
        main(cmd)
        # main("TL 90.")
        # main("STOP 0.")
        # main("STOP 0.")
    except KeyboardInterrupt:
        print("ctrl+c stop")
        # ser.close()

