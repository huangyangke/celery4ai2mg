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