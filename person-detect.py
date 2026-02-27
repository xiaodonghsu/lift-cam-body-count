# -*- coding: UTF-8 -*-
# ! /usr/bin/python

from datetime import datetime
import time
from aip import AipBodyAnalysis
from io import BytesIO
import json
import threading
import os
import base64
import requests
import stomp
from dotenv import load_dotenv
_ = load_dotenv()

from logging_config import setup_logger
import logging
# 获取日志记录器
logger = setup_logger(log_file='app_det.log')
logger.info("Person detective start!")
# mq 的级别设置为CRITICAL
stomp.logging.setLevel(logging.CRITICAL)

# def readJsonFile(fileName):
    # with open(fileName, "r") as fj:
        # return json.loads(fj.read())

# cams = readJsonFile("lift_cams.json")
# 图片及结果发送到消息队列
MQ_IP = os.environ.get("MQ_IP", "127.0.0.1")
MQ_PORT = int(os.environ.get("MQ_PORT", 61613))
MQ_CHANNEL = os.environ.get("MQ_CHANNEL", "")
MQ_USER = os.environ.get("MQ_USER", "admin")
MQ_PASS = os.environ.get("MQ_PASS", "admin")
mq_dest = MQ_CHANNEL
mq_conn = stomp.Connection(host_and_ports=[(MQ_IP, MQ_PORT)])
mq_conn.connect(MQ_USER, MQ_PASS, wait=True)

import redis
memDb = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
LIFT_READER_IP = os.environ.get("LIFT_READER_IP", "127.0.0.1")
LIFT_READER_REDIS_PORT = os.environ.get("LIFT_READER_REDIS_PORT", 6379)
remoteDb = redis.Redis(host=LIFT_READER_IP, port=LIFT_READER_REDIS_PORT, decode_responses=True)
redisKeyLiftPerson = 'LiftPerson'
redisMsgChannel_lift = 'liftPersonImage'

# baidu AI 人体分析 的初始化对象
APP_ID = os.environ.get("BAIDU_APP_ID", "")
API_KEY = os.environ.get("BAIDU_API_KEY", "")
SECRET_KEY = os.environ.get("BAIDU_SECRET_KEY", "")
imageType = "BASE64"

camThreads = {}

# web cache api
WEB_CACHE_API_BASE = os.environ.get("WEB_CACHE_API_BASE", "")

def getNow():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

def getNowStr():
    return datetime.now().strftime('%Y%m%d_%H%M%S_%f')

# def get_file_content(filePath):
    # with open(filePath, 'rb') as fp:
        # return fp.read()

def _saveJpgByte(cam, byte_data, timeStamp, person_num):
    ts = time.localtime(timeStamp)
    tp = os.getcwd() + os.sep + "jpg" + os.sep + cam +os.sep + time.strftime("%Y%m%d", ts) + os.sep + time.strftime("%H", ts)
    tf = "%s_%s_%i.jpg" %(time.strftime("%H%M%S", ts), str(timeStamp)[str(timeStamp).rindex(".")+1:], person_num)
    if not os.path.exists(tp):
        os.makedirs(tp)
    with open(tp + os.sep + tf, 'wb') as f:
        f.write(byte_data)

def saveLog(cam, logID, logContent):
    memDb.hset("%s_log" %cam, logCount, logContent)

def getPersonNum(cam):
    # logCount = 0
    # saveLog(cam, logCount, "get person process:%s" %cam)
    client = AipBodyAnalysis(APP_ID, API_KEY, SECRET_KEY)
    while True:
        if memDb.hget(cam, "flag"):
            capData = memDb.hgetall(cam)
            if len(capData) == 0:
                logger.info("capData length is 0")
            else:
                memDb.delete(cam)
                byte_data = base64.b64decode(capData["base64"])
                byte_data_s = base64.b64decode(capData["base64_s"])
                t0 = time.time()
                try:
                    ret = client.bodyNum(byte_data)
                except Exception as e:
                    logger.info("infer error:", e)
                    ret = {"error_code": -1}
                if "error_code" in ret:
                    logger.info(getNow(), cam, ":", ret, "api time: %0.3f" %(time.time()-t0), "total time: %0.3f" %(time.time()-float(capData['time'])))
                    if ret["error_code"] == 18:
                        time.sleep(0.5)
                else:
                    logger.info(getNow(), cam, ":", ret["person_num"], "api time: %0.3f" %(time.time()-t0), "total time: %0.3f" %(time.time()-float(capData['time'])))
                    try:
                        sTmp = "%s_%s" %(redisKeyLiftPerson, cam)
                        remoteDb.set(sTmp, ret["person_num"])
                        remoteDb.expire(sTmp, 3)
                    except Exception as e:
                        logger.info(getNow(), cam, e)
                    # if ret["person_num"]:
                        # _saveJpgByte(cam, byte_data, float(capData['time']), ret["person_num"])
                    # Save to aliyun cache, for more read.
                    headers = {
                        # "Content-Type": "application/json",
                        "enctype": "multipart/form-data",
                        "charset": "utf8"
                    }
                    data = {'type': 'file'}
                    files = {cam: byte_data_s}
                    # 发送到ncc
                    if WEB_CACHE_API_BASE:
                        try:
                            ret = requests.post(WEB_CACHE_API_BASE, data = data, headers = headers, files = files, timeout=2)
                            logger.info(getNow(), cam, 'save to cloud:', ret.text)
                        except Exception as e:
                            logger.info(getNow(), cam, 'cache file error:', e)
                    # 发送到消息队列
                    try:
                        mq_conn.send(body= json.dumps({"camera": cam, "time": capData['time'], "base64": capData["base64"]}), destination=mq_dest)
                    except Exception as e:
                        logger.info(getNow(), cam, 'mq file error:', e)
        else:
            time.sleep(0.5)

def main():
    ps = memDb.pubsub()
    ps.subscribe(redisMsgChannel_lift) 
    try:
        for item in ps.listen():
            if item['type'] == 'message':
                # logger.info(getNow(), item['channel'], item['data'])
                if item['channel'] == redisMsgChannel_lift:
                    # threading.Thread(target=getPersonNum, args=(item['data'],)).start()
                    # personNum = getPersonNum("%s.jpg" %item['data'])
                    # memDb.set("%s_stat" %(item['data']), 0)
                    json_data = json.loads(item['data'])
                    if 'camera' in json_data:
                        logger.info("received:", json_data['camera'])
                        if not json_data['camera'] in camThreads:
                            logger.info("starting get person process:", json_data['camera'])
                            camThreads[json_data['camera']] = threading.Thread(target=getPersonNum, args=(json_data['camera'],))
                            camThreads[json_data['camera']].start()
                        if memDb.hget(json_data['camera'], "time"):
                            logger.info(json_data['camera'], "not expire or not process, drop!")
                            pass
                        else:
                            if not camThreads[json_data['camera']].is_alive():
                                logger.info("restarting get person process:", json_data['camera'])
                                camThreads[json_data['camera']] = threading.Thread(target=getPersonNum, args=(json_data['camera'],))
                                camThreads[json_data['camera']].start()
                            memDb.hset(json_data['camera'], "base64", json_data['base64'])
                            memDb.hset(json_data['camera'], "base64_s", json_data['base64_s'])
                            memDb.hset(json_data['camera'], "time", json_data['time'])
                            memDb.hset(json_data['camera'], "flag", 1)
                            memDb.expire(json_data['camera'], 2)
                else:
                    logger.info("unknown channel", item['channel'] )
    except Exception as e:
        logger.info(e)
    mq_conn.disconnect()

if __name__ == "__main__":
    main()