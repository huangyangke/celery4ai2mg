import celery

def engine_func(self, image_url):
    task_id = self.request.id
    import time
    time.sleep(10)
    print(f"process with {image_url}")