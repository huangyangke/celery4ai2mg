# 默认celery配置

# result_persistent = False # 结果是否持久化保存到磁盘
# result_exchange = 'celery_result' # 定义用于存储任务结果的AMQP交换机名称
# result_exchange_type = 'direct' # 交换机的类型为direct

worker_concurrency = 1  # 并发worker数，表示同时执行任务的worker数量
task_time_limit = 120 * 60  # 任务的硬时间限制，以秒为单位。如果这个时间限制被超过，处理任务的工作单元进程将会被杀死并使用一个新的替代。
task_soft_time_limit = 110 * 60  # 任务的软时间限制，以秒为单位。如果这个时间限制被超过，worker会收到一个SoftTimeLimitExceeded异常。
timezone = 'Asia/Shanghai'  # 时区设置
CELERYD_FORCE_EXECV = True  # 强制Celery worker在执行新任务时创建新的进程,而不是重用现有进程。这可以防止由于Python的全局解释器锁(GIL)或其他资源竞争导致的死锁问题。当worker处理的任务涉及多线程或存在资源竞争时,这个设置特别重要。
worker_prefetch_multiplier = 1  # worker预取的任务数量
result_serializer = 'json'  # 结果序列化格式
# worker_max_tasks_per_child = 5  # 每个worker最多执行5个任务就会被销毁，可防止内存泄露 默认不限制
worker_disable_rate_limits = True  # 禁用速率限制
task_routes = {}  # 任务路由
task_reject_on_worker_lost = False  # worker丢失时任务是否拒绝 默认为False 
worker_cancel_long_running_tasks_on_connection_loss = False # 默认为False 是否当worker丢失与消息代理的连接时取消正在执行的任务
task_track_started = True  # 任务开始时是否跟踪
task_queue_max_priority = 10  # 任务队列最大优先级
task_default_priority = 5  # 任务默认优先级
broker_heartbeat = 86400  # broker心跳
broker_heartbeat_checkrate = 10  # broker心跳检查频率

# 均设置为True 适用场景：即使失败也不需要重试，或者失败后不希望自动重试的任务
# 均设置为False 适用场景：适用于那些需要高可靠性，即使任务失败也需要确保重新执行的任务
task_acks_late = True  # 任务确认延迟，只有任务成功执行并完成后，消息才会从队列中移除
task_acks_on_failure_or_timeout = True  # 任务失败或超时时确认，即使任务失败或者超时，任务也会被确认

"""
修改过期时间：
/root/miniconda3/lib/python3.8/site-packages/celery_amqp_backend/backend.py
line 62: func store_result:
在producer.publish内增加参数 
expiration=5, # 控制任务结果在消息队列中的存活时间 这里设置为5s后，如果消息没有被消费，将会自动从队列中删除
"""