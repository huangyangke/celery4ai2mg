import sys
import time
import json
import copy
import os, re
import inspect
import importlib
import configparser
from kombu import Queue, Exchange
from celery.result import AsyncResult


class CeleryTaskOperate:
    def __init__(self, celery_app, config_operate, start_worker=False) -> None:
        """
        Celery任务操作类
        参数:
            celery_app: Celery应用实例
            config_operate: 配置操作对象
            start_worker: 是否创建celery worker
        功能:
            - 管理Celery任务的创建和配置
            - 更新任务队列
            - 添加Celery配置
            - 更新broker和backend连接信息
        """
        self.start_worker = start_worker
        self.task_name_dict = {} # 只能通过CeleryTaskOperate的update_celery_task函数更新
        # 操作需要同步
        self.config_operate = config_operate # 每次配置的修改会同步到配置文件中
        self.celery_app = celery_app
        self.sync_broker_backend(config_operate.config) # 同步broker

    def sync_broker_backend(self,config):
        """
        同步broker、backend
        """
        if 'celery' in config:
            self.celery_app.conf.broker_url = config[f'celery']["broker_url"].strip('"').strip("'")
            self.celery_app.conf.result_backend = config[f'celery']["backend_url"].strip('"').strip("'")
            broker_transport_options = config[f'celery'].get("broker_transport_options", None)
            if broker_transport_options is not None:
                broker_transport_options = json.loads(broker_transport_options)
                self.celery_app.conf.broker_transport_options = broker_transport_options
                self.celery_app.conf.result_backend_transport_options = broker_transport_options

    def update_celery_config(self, key, value):
        """
        更新celery配置项。比如broker_url、backend_url等
        section [celery]
        参数:
            key: 配置项名称
            value: 配置项值
        """
        if isinstance(value,  str):
            value_ = value.strip('"').strip("'")
        elif isinstance(value, list) or isinstance(value, dict):
            value_ = copy.deepcopy(value)
            value = json.dumps(value)
        setattr(self.celery_app.conf, key, value_) # 修改celery_app运行时的属性
        self.config_operate.update_config("celery", key, value) # 保存修改到配置文件
     
    def update_broker_backend(self, broker_url,  backend_url, broker_transport_options = None):
        """
        更新Celery的broker和backend连接配置
        参数:
            broker_url: 消息代理的连接URL
            backend_url: 结果后端的连接URL 
            broker_transport_options: 消息代理的传输选项,默认为None
        功能:
            - 更新Celery的broker_url配置
            - 更新Celery的backend_url配置
            - 如果backend_url是amqp连接串,将其转换为celery_amqp_backend格式
            - 如果提供了broker_transport_options,更新相应配置
        示例:
            broker_url = "sentinel://10.43.208.66:7850;sentinel://10.43.208.64:7495;sentinel://10.43.208.65:7493;"
            backend_url = "sentinel://10.43.208.66:7850;sentinel://10.43.208.64:7495;sentinel://10.43.208.65:7493;"
            broker_transport_options = {"master_name":"ad-effect_platform-aliyun-new2-6450"}
            celery_amqp_backend.AMQPBackend://ai2mg:as78113hasf1v@10.200.16.242/ai2mg-prod
        """
        self.update_celery_config('broker_url', broker_url)
        
        # 如果backend_url为amqp开头的连接串，需将其改为celery_amqp_backend
        if backend_url.startswith('amqp://'):
            backend_url = re.sub(r"^amqp://", "celery_amqp_backend.AMQPBackend://", backend_url)
        self.update_celery_config('backend_url', backend_url)
        
        if broker_transport_options is not None:
            self.update_celery_config('broker_transport_options', broker_transport_options)
    
    def reset_config_operate(self, config_file_path):
        """
        重置config_operate
        """
        # 读取配置文件
        config = configparser.ConfigParser()
        config.read(config_file_path)
        # 更新到默认配置文件中
        self.config_operate.config = config
        self.config_operate.save()        
        # 同步broker backend
        self.sync_broker_backend(config)
        # 创建worker时更新队列路由 
        if self.start_worker:
            if 'tasks' in config:
                tasknames = config['tasks']['name_list'].strip().split(',')
                tasknames  = [i for i in tasknames if i!=""]       
                for task_name in tasknames:
                    func_name = config[task_name].get('func_name', task_name)
                    queue_name = config[task_name].get('queue_name', f"ai2mg_{func_name}")   
                    self.update_queue(queue_name) # 更新任务队列配置 
        return config
    
    def batch_create_celery_task(self):
        """
        创建celery任务
        """
        config = self.config_operate.config
        # 更新任务配置
        if 'tasks' in config:
            tasknames = config['tasks']['name_list'].strip().split(',')
            tasknames  = [i for i in tasknames if i!=""]
        # 遍历每一个任务
        for task_name in tasknames:
            # 要绑定的执行函数or类
            func_name = config[task_name].get('func_name', task_name)
            class_name = config[task_name].get('class_name', None)
            importpath = config[task_name].get('importpath', None)
            script = importlib.import_module(importpath)
            try:
                if class_name is not None:
                    func_or_class = getattr(script, class_name)
                else:
                    func_or_class = getattr(script, func_name)
            except AttributeError:
                print(f"Error! cannot find  func_or_class with task_name =={task_name}==")
                continue
            # 获取任务相关配置
            soft_time_limit = config[task_name].get('soft_time_limit', None)
            if soft_time_limit is not None: soft_time_limit = int(soft_time_limit)
            queue_name = config[task_name].get('queue_name', f"ai2mg_{func_name}")
            classbase = config[task_name].getboolean('classbase', fallback=False)
            bind = config[task_name].getboolean('bind', fallback=False)
            self.update_celery_task(func_or_class, task_name=task_name,queue_name=queue_name, soft_time_limit=soft_time_limit, bind=bind,classbase=classbase, create_task=True)

    def update_celery_task(self, func_or_class, task_name="",queue_name="", soft_time_limit=60*60, bind=False,classbase=False, create_task=False):
        """
        添加Celery任务
        外部调用，create_task设置为False，只创建任务到配置文件中，并更新路由队列
        内部调用，比如create_celery_task函数，create_task设置为True，用于启动celery的worker
        参数:
            func_or_class: 要创建任务的函数或类
            task_name: 任务名称,默认为空字符串,会自动生成
            queue_name: 队列名称,默认为空字符串,会自动生成
            soft_time_limit: 软时间限制,默认为1小时
            bind: 是否绑定任务实例,默认为False
            classbase: 是否基于类的任务,默认为False
            create_task: 是否创建任务,默认为True
        返回:
            task_name: 任务名称
        功能:
            - 根据输入的函数或类创建Celery任务
            - 支持普通函数任务和基于类的任务
            - 自动生成任务名称和队列名称
            - 配置任务的软时间限制
            - 更新任务配置和队列信息
        """
        func_name = func_or_class.__name__
        task_name = f"task_{func_name}" if task_name  == "" else task_name
        queue_name = f"ai2mg_{func_name}" if queue_name  == "" else queue_name
        task_full_name = f"{queue_name}.{task_name}"
        
        self.config_operate.update_task(func_or_class, task_name, queue_name, soft_time_limit=soft_time_limit, bind=bind,classbase=classbase) # 更新当前task配置到配置文件中
        self.update_queue(queue_name) # 更新任务队列配置
        self.task_name_dict[task_name] = {"task_name":task_full_name,"soft_time_limit":soft_time_limit} # 更新任务名称字典 
        if not create_task:
            return task_name
        print(f"create task: {task_name}, classbase: {classbase}, bind: {bind}")
        """
        基于类的任务
        设置了最大重试次数为3次
        bind=True 作用是将任务函数的第一个参数绑定为任务实例本身（通常表示为self）。这允许任务函数访问当前任务的上下文和Celery的各种API
        如self.request.id 获取当前任务的id self.request.retries获取当前任务的重试次数      
        name属性用来路由task到指定队列中  
        """
        if classbase:
            @self.celery_app.task(bind=True, base=func_or_class,name=task_full_name, soft_time_limit=soft_time_limit,max_retries=3)
            def celery_task(self, *args, **kwargs):
                return self.run_process(*args, **kwargs)
        elif bind:
            @self.celery_app.task(bind=True, name=task_full_name, soft_time_limit=soft_time_limit)
            def celery_task(self, *args, **kwargs):
                return func_or_class(self, *args, **kwargs)
        else:
            @self.celery_app.task(bind=False, name=task_full_name, soft_time_limit=soft_time_limit)
            def celery_task(*args, **kwargs):
                return func_or_class(*args, **kwargs)   
        return task_name
    
    def send_task(self, func=None,task_name="", args=[],kwargs={} ,priority=5):
        """
        生产者：发送任务到任务队列，可以无需注册函数！！
        func和task_name输入一个即可，推荐输入task_name
        参数:
            func: 任务函数对象,默认为None
            task_name: 任务名称,默认为空字符串
            args: 位置参数列表,默认为空列表
            kwargs: 关键字参数字典,默认为空字典
            priority: 任务优先级,默认为5  范围：0到255之间，对于rabbitmq来说0是最高优先级
        返回:
            task: 任务对象,如果start_worker为True则返回None
        功能:
            - 支持通过函数对象或函数名称执行任务
            - 自动查找任务名称
            - 设置任务优先级
            - 在start_worker为True时不执行任务
        """
        if self.start_worker: return
        if task_name == "" and func is None:
            raise "请输入函数，或者任务名"
        task_name = func.__name__ if task_name == "" else task_name
        # task_full_name = f"{queue_name}.{task_name}" 路由到queue_name队列
        if task_name in self.task_name_dict:
            task_full_name = self.task_name_dict[task_name]['task_name'] 
        elif f"task_{task_name}" in self.task_name_dict:
            task_full_name = self.task_name_dict[f"task_{task_name}"]['task_name']
        else:
            raise "错误的任务名"
        return self.celery_app.send_task(task_full_name, args=args, kwargs=kwargs,priority=priority)

    def update_queue(self, queue_name):
        """
        更新任务队列配置
        参数:
            queue_name: 队列名称
        功能:
            - 将新的队列添加到Celery的路由配置中
            - 使用通配符格式 queue.* 作为路由键
            - 更新后的队列可用于任务路由
        示例：
            {
                'mmapp_pointcube.*': {'queue': 'mmapp_pointcube'},
                'mmapp_schedule.*': {'queue': 'mmapp_schedule'},
            }
        """
        print(f"update queue: {queue_name}")
        # 获取现有的task_routes配置
        existing_routes = self.celery_app.conf.task_routes or {}
        # 添加新的队列配置
        existing_routes[f"{queue_name}.*"] = {'queue': queue_name}
        # 更新配置
        self.celery_app.conf.task_routes.update(existing_routes)

    def async_result(self, taskid):
        if self.start_worker: return
        return AsyncResult(taskid)
    
    def done(self):
        """
        只有启动celery的worker时才会起作用
        """
        if self.start_worker:
            run_command_key_word = "--start_worker"
            extra_args = ' '.join(sys.argv[sys.argv.index(run_command_key_word) + 1:])
            queues = ','.join([i.strip(".*") for i in self.celery_app.conf.task_routes]) 
            print(f'================celery启动命令================')
            self.config_operate.config.write(sys.stdout)
            cmd = f"celery -A celery4ai2mg.tasks worker -Q {queues} {extra_args}" # -Q 参数，让启动的worker只监听指定的队列
            print(f'==celery cmd: {cmd}')
            os.system(cmd)
            exit(0)

class ConfigOperate:
    def __init__(self, base_dir) -> None:
        """
        配置操作类，用于管理celery任务的配置信息
        参数:
            base_dir: 项目根目录路径
        功能:
            - 在项目根目录下创建.celery文件夹存储配置
            - 构建config.ini文件
        """
        self.base_dir = base_dir
        tmp_dir = os.path.join(self.base_dir, ".celery") # 将celery相关的配置文件保存到{self.base_dir}/.celery下
        os.makedirs(tmp_dir, exist_ok=True)
        self.local_config_path = os.path.join(tmp_dir, "config.ini")
        self.config = configparser.ConfigParser()
        self.config.read(self.local_config_path)
        if not os.path.exists(self.local_config_path):
            self.save()
    
    def update_task(self, function, tname, qname, soft_time_limit=None, bind=False,classbase=False):
        """
        更新函数配置信息到config.ini  
        section [tasks]
        section [tname]
        参数:
            function: 需要注册的函数对象
            tname: 注册的任务名称
            qname: 任务队列名称
            soft_time_limit: 任务超时时间限制,可选
            bind: 
            classbase: 
        功能:
            - 更新配置文件中的任务列表
            - 保存函数相关配置信息
        """
        file_path = inspect.getfile(function)
        relpath =  os.path.relpath(file_path, self.base_dir)
        assert relpath.endswith(".py")
        importpath = '.'.join(relpath[:-3].split('/'))
        func_name = function.__name__

        # 更新任务列表
        if 'tasks' in self.config:
            name_list = self.config.get('tasks', 'name_list').strip().split(',')
            name_list = [i for i in name_list if i != ""] + [tname]
            name_list = list(set(name_list))
        else:
            self.config.add_section('tasks')
            name_list = [tname]
        self.config.set('tasks', 'name_list', ','.join(name_list))
        
        # 更新函数配置
        if tname not in self.config:
            self.config.add_section(tname)
        self.config.set(tname, 'importpath', importpath)
        self.config.set(tname, 'func_name', func_name)
        self.config.set(tname, 'bind', str(bind)) # bool值，读取时必须使用.getboolean读取
        self.config.set(tname, 'classbase', str(classbase)) # bool值，读取时必须使用.getboolean读取
        self.config.set(tname, 'queue_name', qname)
        if soft_time_limit is not None:
            self.config.set(tname, 'soft_time_limit', str(soft_time_limit))
        self.save()

    def update_config(self, section, key, value):
        if section not in self.config:
            self.config.add_section(section)
        self.config.set(section, key, value)
        self.save()
    
    def save(self):
        # 写入 INI 文件
        with open(self.local_config_path, 'w') as configfile:
            self.config.write(configfile)
        
    def lastest_config(self):
        config = configparser.ConfigParser()
        config.read(self.local_config_path)
        return config
    
def health():
    print(f"package health")