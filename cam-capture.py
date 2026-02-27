# -*- coding: UTF-8 -*-
# ! /usr/bin/python

import cv2
import numpy
from datetime import datetime
import time
import json
from PIL import Image
from io import BytesIO
import base64
import threading

from logging_config import setup_logger

# 获取日志记录器
logger = setup_logger(log_file='app_cap.log')
logger.info("Camera capture start!")

import redis
memDB = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
# remoteDB = redis.Redis(host='192.168.6.63', port=6379, decode_responses=True)
# remoteDB = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)

redisMsgChannel = 'liftPersonImage'

def readJsonFile(fileName):
    with open(fileName, "r") as fj:
        return json.loads(fj.read())

cams = readJsonFile("lift_cams.json")
camThreads = {}
# camCapFlag = {}
camStopFlag = {}
# 图像捕捉的周期
camCapPeriod = 2
# 图像比较，出现连续相同的次数
MAX_CONTIUOUS_EQUAL_TIMES = 5

def readJpegFile(fileName):
    with open(fileName, "rb") as fj:
        return fj.read()

def getNowTime():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

def getNow():
    return datetime.now().strftime('%Y%m%d_%H%M%S_%f')

def numpyArrayConvertToBase64String(numpyArray):
    img = Image.fromarray(numpyArray)
    output_buffer = BytesIO()
    img.save(output_buffer, format='JPEG')
    byte_data = output_buffer.getvalue()
    return base64.b64encode(byte_data).decode('utf-8')

def captureCam(cam):
    # camCaptures[cam].release()
    cap = cv2.VideoCapture()
    capTimer = time.time()
    b64Data = ""
    b64Data_pre = ""
    b64DataSameCounter = MAX_CONTIUOUS_EQUAL_TIMES
    while True:
        if cap.isOpened():
            cap.grab()
            # if camCapFlag[cam]:
            if time.time() - capTimer > camCapPeriod:
                # logger.info(cam, "flag checked...")
                capTimer = time.time()
                # logger.info(cam, "timer up...")
                grabTime = time.time()
                grabbed, frame = cap.retrieve()
                if grabbed:
                    logger.info(cam, "frame grabbed...")
                    # camCapFrame[cam] = frame
                    try:
                        logger.info(cam, "frame publishing...")
                        # 颜色转换
                        frame = cv2.cvtColor(numpy.asarray(frame), cv2.COLOR_RGB2BGR)
                        height, width = frame.shape[:2]
                        frame_s = cv2.resize(frame, (int(width/2), int(height/2)), interpolation=cv2.INTER_CUBIC)
                        b64Data = numpyArrayConvertToBase64String(frame)
                        b64Data_s = numpyArrayConvertToBase64String(frame_s)
                        # 连续工作一段时间以后，图像不再变化
                        # 检查该数据是否变化
                        # 检查编码是否一致，一致的情况下，如果连续出现MAX_CONTIUOUS_EQUAL_TIMES次，释放连接
                        if b64Data == b64Data_pre:
                            b64DataSameCounter -= 1
                        else:
                            b64Data_pre = b64Data
                            b64DataSameCounter = MAX_CONTIUOUS_EQUAL_TIMES
                        if b64DataSameCounter == 0:
                            logger.info(cam, "MAX_CONTIUOUS_EQUAL_TIMES occurs, release connection.")
                            cap.release()
                        else:
                            ret = memDB.publish(redisMsgChannel,json.dumps({"camera": cam, "time":grabTime, "base64": b64Data, "base64_s": b64Data_s}))
                            logger.info(cam, "frame published, time cost: %0.3f" %(time.time()-grabTime), "same counter:", b64DataSameCounter)
                    except Exception as e:
                        logger.error("Error in publish frame:", e)
                    # camCapFlag[cam] = False
                else:
                    cap.release()
            # td = time.time() - grabTime
            # if td < 0.04:
                # time.sleep(0.04 - td)
        else:
            try:
                cap.open(cams[cam])
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            except Exception as e:
                logger.error("Error in opening file")
                time.sleep(1)

def main():
    for cam in cams:
        logger.info("%s init..." %(cam))
        # camCapFlag[cam] = False
        camThreads[cam] = threading.Thread(target=captureCam, args=(cam,))
        camThreads[cam].start()
    while True:
        for cam in cams:
            # logger.info(cam)
            # t0 = time.time()
            # camCapFlag[cam] = True
            # while camCapFlag[cam] and time.time() - t0 < 10:
                # pass
            # if camCapFlag[cam]:
                # logger.info("%s capture time out! what to do ..." %(cam))
                # logger.info(cam, camThreads[cam].name, "alive:", camThreads[cam].is_alive())
                # log.debug("%s capture time out, restart..." %(cam))
                # camThreads[cam] = threading.Thread(target=captureCam, args=(cam,))
                # camThreads[cam].start()
            # td = time.time() - t0
            # logger.info("time: %0.2f" %(td))
            # if td < 1:
                # time.sleep(1 - td)
            if not camThreads[cam].is_alive():
                log.debug("%s is not alive, restart..." %(cam))
                camThreads[cam] = threading.Thread(target=captureCam, args=(cam,))
                camThreads[cam].start()
            time.sleep(1)

if __name__ == "__main__":
    main()