import configparser
import csv
import datetime
import logging
import logging.handlers
import os
import sys
import time
from collections import Iterator


def follow(file, sleep_sec=1) -> Iterator[str]:
    """ Yield each line from a file as they are written.
    `sleep_sec` is the time to sleep after empty reads. 
    Starts from begining of the file."""
    line = ''
    while True:
        tmp = file.readlines()[-1]
        print("tmp = ", tmp)
        if tmp is not None:
            line += tmp
            if line.endswith("\n"):
                yield line
                line = ''
        else:
            if sleep_sec:
                time.sleep(sleep_sec)


def log_correct_check(timeout: int) -> bool:
    """Check if mosaic is responding with thermal images.
    timeout - acceptable time of mosaic no activity."""
    file_path = "new.log"
    # with open(file_path, 'r') as file:
    last_active = {}
    for line in tail_F(file_path):
        splited_line = line.split(" ", 3)
        if len(splited_line) >= 3:
            log_date = splited_line[0]
            log_time = splited_line[1]
            log_code = splited_line[2]
            # 2022-06-14 23:02:09.339
            if len(log_date) == 10 and len(log_time) == 12 and len(log_code) > 0:
                pass
            else:
                continue

            log_message = splited_line[3]
            print("log = ", log_message)
            if log_date and log_time:
                log_time = datetime.datetime.strptime(log_date + " " + log_time, "%Y-%m-%d %H:%M:%S.%f")

                if "Stored image from" in log_message:
                    splited_log_message = log_message.split(" ")
                    mosaic_no = splited_log_message[6].replace(".\n", "")
                    last_active[mosaic_no] = log_time

        for mosaic in last_active:
            time_diff = log_time - last_active[mosaic]
            if time_diff.total_seconds() > timeout:
                logging.info("Mosaic no. %s is not responding for %s seconds", mosaic, str(time_diff.total_seconds()))
                return mosaic
            #time.sleep(0.5)
    return ""


