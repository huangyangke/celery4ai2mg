#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import sys
import importlib
from . import cyoperate,celery_app

print(f'================开始创建任务================')
cyoperate.batch_create_celery_task()