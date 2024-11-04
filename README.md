# celery ai2mg
###### 本包基于celery, 将常用不会变的配置封装进了包内, 并简化了异步改造的流程. 用户只需简单的几步即可完成同步代码的celery异步化.


### 安装
```
git clone -b package https://git.imgo.tv/aiops/celery_ai2mg.git
cd celery_ai2mg
pip install . -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host mirrors.aliyun.com --default-timeout=100
```
### 同步函数改造示例

- 以fastapi的一个服务为例, 现有代码为
```
main_api.py   # 程序api的入口
engine.py     # 主要功能函数或类的代码部分
```
main_api.py
```
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from engine import engine_func

app = FastAPI()

class Item(BaseModel):
    image_url: str

@app.post("/logodetracker")
def logo_detracker(item: Item):
    result = engine_func(item.image_url)
    return {"code":200, "data": result}

if __name__ == '__main__':
    uvicorn.run(app,host='0.0.0.0',port=4111)
```

###### ps: engine_func为engin内的一个函数
- 改造后的代码
```
# --------新增部分--------
from celery4ai2mg import ctoperate  #  导入模块
ctoperate.update_broker_backend(  #  初始化连接串
    broker_url="amqp://ai2mg:3hasf1v@10.200.16.242/ai2mg-prod",  
    backend_url="celery_amqp_backend.AMQPBackend://ai2mg:hasf1v@10.200.16.242/ai2mg-prod"
)

from engine import engine_func  # 导入需要异步的函数
engine_func_name = ctoperate.create_celery_task(engine_func)  # 创建任务
ctoperate.done()  # 任务定义完成
# --------新增部分--------

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    image_url: str

@app.post("/logodetracker")
def logo_detracker(item: Item):
    task = ctoperate.task_async(func_name=engine_func_name, args=[item.image_url,])
    return {"code":200, "task_id": task.id}

    
if __name__ == '__main__':
    uvicorn.run(app,host='0.0.0.0',port=4111)
```

### 同步类改造示例
###### 有时候, 主要功能函数包含了模型的加载, 这时候可以使用异步类, 将模型加载放在init函数中, 这样就可以只在程序初始化的时候进行模型加载了. 在这个包中, 你需要将主要功能函数命名为**run_process**, 本包会托管这个函数, 并在调用时自动执行

engine文件示例
```
import celery
from bhrl.logoDeTracker import LogoDeTracker
class LogoDeTrackMasker(celery.Task):
    def __init__(self):
        self.model = LogoDeTracker()
    
    def run_process(self, image_url, video_url):
        task_id = self.request.id
        result = self.model(image_url, video_url)
        
        # 结果可以通过数据库或回调的方式返回
        recall_back(task_id, result)
```
main_api.py文件示例
```
# --------新增部分--------
from celery4ai2mg import ctoperate  #  导入模块
ctoperate.update_broker_backend(  #  初始化连接串
    broker_url="amqp://ai2mg:3hasf1v@10.200.16.242/ai2mg-prod",  
    backend_url="celery_amqp_backend.AMQPBackend://ai2mg:hasf1v@10.200.16.242/ai2mg-prod"
)

from engine import LogoDeTrackMasker  # 导入需要异步的函数
engine_class_name = ctoperate.create_celery_task(LogoDeTrackMasker, task_name='task_logdetrack', classbase=True)  # 创建任务(可以指定自己的任务名称, 防止在同一队列中与其他任务干涉), 注意这里需要指定classbase为True
ctoperate.done()  # 任务定义完成
# --------新增部分--------

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    image_url: str

@app.post("/logodetracker")
def logo_detracker(item: Item):
    task = ctoperate.task_async(func_name=engine_class_name, kwargs=item.dict()) # 可以使用多种方式传参
    return {"code":200, "task_id": task.id}

if __name__ == '__main__':
    uvicorn.run(app,host='0.0.0.0',port=4111)
```


### 运行

- api运行时, 任务与之前保持一致

运行的参数内不包含--run_celery选项时，会直接执行业务代码，不会启动celery。如:
```
python main.py
```

- celery命令

运行的参数内包含--run_celery选项时，执行ctoperate.done()之前的代码后，退出程序并执行
--run_celery 后面的参数为celery的其他函数，会补充到命令行的后面。
```
python main.py --run_celery  -c 1 -l info -P prefork
```

