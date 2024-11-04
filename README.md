# celery ai2mg
###### 本包基于celery, 将常用不会变的配置封装进了包内, 并简化了异步改造的流程. 用户只需简单的几步即可完成同步代码的celery异步化.


### 安装
```
git clone https://github.com/huangyangke/celery4ai2mg.git
cd celery_ai2mg
pip install . -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host mirrors.aliyun.com --default-timeout=100
```
### 同步函数or类改造示例

- 以fastapi的一个服务为例, 现有代码为
```
main_api.py   # 程序api的入口
projects/example/engine.py     # 主要功能函数或类的代码部分
```
main_api.py
```
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
class Item(BaseModel):
    image_url: str

@app.post("/func_call")
def func_call(item: Item):
    task = cyoperate.send_task(task_name=task_name1, args=[item.image_url,]) # 此方法会将任务放到队列中
    return {"code":200, "task_id": task.id}

@app.post("/class_call")
def class_call(item: Item):
    task = cyoperate.send_task(task_name=task_name2, args=[item.image_url,]) # 此方法会将任务放到队列中
    return {"code":200, "task_id": task.id}

if __name__ == '__main__':
    print('=========================创建fastapi服务=========================')
    uvicorn.run(app,host='0.0.0.0',port=4111)
```

- 改造后的代码
```
# --------celery--------
from celery4ai2mg import cyoperate  
cyoperate.update_broker_backend( 
    broker_url='redis://127.0.0.1:6379/1',
    backend_url='redis://127.0.0.1:6379/2',
)
from projects.example.engine import engine_func, LogoDeTrackMasker
task_name1 = cyoperate.update_celery_task(engine_func, bind=True) 
task_name2 = cyoperate.update_celery_task(LogoDeTrackMasker, classbase=True) 
cyoperate.done()  # 任务定义完成
#--------celery--------
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
class Item(BaseModel):
    image_url: str

@app.post("/func_call")
def func_call(item: Item):
    task = cyoperate.send_task(task_name=task_name1, args=[item.image_url,]) # 此方法会将任务放到队列中
    return {"code":200, "task_id": task.id}

@app.post("/class_call")
def class_call(item: Item):
    task = cyoperate.send_task(task_name=task_name2, args=[item.image_url,]) # 此方法会将任务放到队列中
    return {"code":200, "task_id": task.id}

if __name__ == '__main__':
    print('=========================创建fastapi服务=========================')
    uvicorn.run(app,host='0.0.0.0',port=4111)
```


### 运行

- 启动接口

```
python main.py
```

- 启动worker

```
python main.py --start_worker  -c 1 -l info -P prefork
```

