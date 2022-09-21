#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import uuid
from utils.serial_control import serial_control
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
        main("TL 15.")
        # main("STOP 0.")
        # main("STOP 0.")
    except KeyboardInterrupt:
        print("ctrl+c stop")
        ser.close()

