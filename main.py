# encoding = utf-8
# 主程序
import time
import subprocess
import logging
import psutil
import sys

from logging_config import setup_logger
logger = setup_logger(log_file='app.log')

from dotenv import load_dotenv

_ = load_dotenv()

import os

if os.environ.get("BAIDU_APP_ID", "") == "":
    msg = "未设置参数: BAIDU_APP_ID"
    logger.error(msg)
    raise ValueError(msg)

if os.environ.get("BAIDU_API_KEY", "") == "":
    msg = "未设置参数: BAIDU_API_KEY"
    logger.error(msg)
    raise ValueError(msg)

if os.environ.get("BAIDU_SECRET_KEY", "") == "":
    msg = "未设置参数: BAIDU_SECRET_KEY"
    logger.error(msg)
    raise ValueError(msg)

python_exe = sys.executable

sub_processes = {
        "cam-capture": [python_exe, "cam-capture.py"],
        "person-detect": [python_exe, "person-detect.py"]
    }

def getProcessPid(process_cmdline):
    pids = psutil.pids()
    for pid in pids:
        try:
            cmdline = psutil.Process(pid).cmdline()
            if cmdline == process_cmdline:
                return pid
        except:
            pass
    return -1

def listPythonProcesses():
    pids = psutil.pids()
    for pid in pids:
        try:
            cmdline = psutil.Process(pid).cmdline()
        except:
            cmdline = []
        if len(cmdline)>0:
            if cmdline[0].lower().find('py')>=0:
                print(pid, cmdline)
    return -1

def startProcess(process_cmdline):
    pid = getProcessPid(process_cmdline)
    if pid > 0:
        return pid
    else:
        logging.info('%s Not started! try to start!' %process_cmdline)
        try:
            processObj = subprocess.Popen(process_cmdline)
            time.sleep(10)
            return processObj.pid
        except Exception as e:
            logging.info("start process %s failed: %s" %(" ".join(process_cmdline), e))
            return None

def killProcess(process_cmdline):
    pids = psutil.pids()
    for pid in pids:
        try:
            process = psutil.Process(pid)
            if process.cmdline() == process_cmdline:
                process.kill()
                logging.info("Kill process %s (%i) success." %(" ".join(process_cmdline), pid))
        except:
            pass

def main():
    logger.info("Process start!")
    while True:
        for process_name in sub_processes:
            process_id = startProcess(sub_processes[process_name])
            if process_id is None:
                logger.info('Start %s fail.' %sub_processes[process_name])
            time.sleep(5)
        time.sleep(10)

if __name__ == "__main__":
    main()