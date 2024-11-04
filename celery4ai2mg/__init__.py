#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import os, sys, json
import argparse
import celery, kombu, amqp
from kombu import Queue, Exchange
from celery import Celery
from celery.concurrency import asynpool
from .base import ConfigOperate,CeleryTaskOperate

# -------------------工作目录------------------
BASE_DIR = os.getcwd()
print(f"BASE_DIR: {BASE_DIR}")
sys.path.append(BASE_DIR)

# -------------------获取环境变量参数------------------
print(f"package version: \n   celery: {celery.__version__}, \n   kombu: {kombu.__version__}, \n   amqp: {amqp.__version__}")
version = os.getenv('CELERY_MODE','dev')
print(f"CELERY_MODE: {version}")

# -------------------获取当前队列参数与运行参数------------------
parser = argparse.ArgumentParser()
# parser.add_argument('-Q',type=str, default='')  # --queue
parser.add_argument("--start_worker", action="store_true", help="执行celery命令，启动worker")
args, unknown = parser.parse_known_args()

# # 启动指定任务队列的worker 如果为空，则全启动
# appoint_task_queue = args.Q
# print(f"appoint_task_queue: {appoint_task_queue}")

is_celery_cmd = 'celery' == os.path.basename(sys.argv[0]) # 判断是否执行的celery -A celery4ai2mg.tasks worker
if not is_celery_cmd: os.system(f"rm -rf {BASE_DIR}/.celery") # 删除临时文件夹内的内容，重新生成配置文件
print(f'start_worker: {args.start_worker}') 
print(f'is_celery_cmd: {is_celery_cmd}')
start_worker = args.start_worker or is_celery_cmd
# -------------------通用celery配置------------------
asynpool.PROC_ALIVE_TIMEOUT = 3600.0
celery_app = Celery('tasks')
celery_app.config_from_object(f"celery4ai2mg.celery_config") # 加载默认celery配置 配置文件celery_config.py 
celery_app.conf.worker_proc_alive_timeout = 3600 # worker存活检测，这里设置1小时

# -------------------task配置------------------
# 读取配置文件 第一次运行会创建一个默认配置文件
config_operate = ConfigOperate(BASE_DIR)
cyoperate = CeleryTaskOperate(celery_app=celery_app,
                              config_operate=config_operate,
                              start_worker=start_worker,)
"""
python main.py 
1、当前脚本执行一次，用于构建fastapi接口，并构建celery路由

python main.py --start_worker  -c 1 -l info -P prefork 
1、当前脚本执行两次，用于创建celery worker
2、第二次是由celery -A celery4ai2mg.tasks worker启动，这次不会构建.celery/config.ini文件，一致性由第一次创建的.celery/config.ini文件保证

注意事项：
1、celery的默认配置文件 celery_config.py 
"""