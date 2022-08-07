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


def tail_F(file_path):
    """works like tail -f in linux, yells every incoming message to the file."""
    first_call = True
    while True:
        try:
            with open(file_path) as input:
                if first_call:
                    #input.seek(0, 2)
                    first_call = False
                latest_data = input.read()
                while True:
                    if '\n' not in latest_data:
                        latest_data += input.read()
                        if '\n' not in latest_data:
                            yield ''
                            if not os.path.isfile(file_path):
                                break
                            continue
                    latest_lines = latest_data.split('\n')
                    if latest_data[-1] != '\n':
                        latest_data = latest_lines[-1]
                    else:
                        latest_data = input.read()
                    for line in latest_lines[:-1]:
                        yield line + '\n'
        except IOError:
            yield ''


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


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read("config.ini")

    logger_handlers = [logging.handlers.RotatingFileHandler(
        config.get("CALIBRATION", "LogFile"),
        maxBytes=100000000,
        backupCount=3
    )]
    if config.getboolean("DEFAULT", "StandardOutputLogging"):
        logger_handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(handlers=logger_handlers,
                        level=logging.INFO,
                        format=
                        '%(asctime)s.%(msecs)02d %(levelname)s' \
                        + ' %(module)s - %(funcName)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    for key in logging.Logger.manager.loggerDict:
        logging.getLogger(key).setLevel(logging.ERROR)

    counter = int(config.get("CALIBRATION", "RestartCount"))
    delay = float(config.get("GATEWAY", "RequestDelay"))
    timeout = int(config.get("CALIBRATION", "Timeout"))
    device_count = int(config.get("GUI", "DeviceCount"))
    # Counter prevents constant reboot loop.
    if counter > 0:
        logging.info("New test start.")
        while True:
            # Checking gateway.log until one mosaic stop responding with thermal images.
            mosaic_ret = log_correct_check(timeout)
            # print("ret: " + mosaic_ret)
            data = []
            if len(mosaic_ret) > 0:
                now = datetime.datetime.now()
                finish_date = now.strftime("%Y-%m-%d %H:%M:%S.%f")
                # Saving results to csv file to future analyse.
                data = [finish_date, device_count, delay, mosaic_ret.strip()]

                with open('delay_test_results.csv', 'a', encoding='UTF8', newline='\n') as result_file:
                    writer = csv.writer(result_file)
                    writer.writerow(data)
                # Reducing counter and increasing delay for next test round.
                counter -= 1
                config.set("CALIBRATION", "RestartCount", f"{counter}")
                logging.info("Counter reduced to %s", counter)
                delay += 0.1
                config.set("GATEWAY", "RequestDelay", f"{round(delay, 1)}")
                logging.info("Request delay increased to %s", delay)
                logging.info("Restarting test.")
                with open('config.ini', 'w') as configfile:
                    config.write(configfile)
                # Reboot gateway RPI.
                os.system('sudo shutdown -r now')