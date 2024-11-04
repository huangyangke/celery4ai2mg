import celery
import time

def engine_func(self, image_url):
    task_id = self.request.id
    time.sleep(10)
    print(f"process with {image_url}")


class LogoDeTrackMasker(celery.Task):
    def __init__(self):
        # self.model = LogoDeTracker()
        pass
    
    def run_process(self, image_url):
        task_id = self.request.id
        time.sleep(10)
        print(f"process with {image_url}")

        # result = self.model(image_url)
        # # 结果可以通过数据库或回调的方式返回
        # recall_back(task_id, result)