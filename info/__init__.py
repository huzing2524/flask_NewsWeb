from logging.handlers import RotatingFileHandler
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask_wtf import CSRFProtect
# from flask.ext.wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from redis import StrictRedis
from config import config
from info.utils.common import do_index_class

# 初始化数据库
db = SQLAlchemy()
# python3.6新功能,给变量或者函数增加智能补全提示的2种方法,类型标识
redis_store = None  # type: StrictRedis
# redis_store: StrictRedis = None


def create_app(config_name):
    # 配置log日志
    setup_log(config_name)
    # 创建Flask对象
    app = Flask(__name__)
    # 加载配置
    app.config.from_object(config[config_name])
    # 通过init_app初始化
    db.init_app(app)
    # 初始化redis存储对象
    global redis_store
    redis_store = StrictRedis(host=config[config_name].REDIS_HOST, port=config[config_name].REDIS_PORT, decode_responses=True)
    # 开启CSRF保护flask已实现的功能：1.从cookie中取出随机值；2.从表单中取出随机值。然后进行对比校验，并且响应校验结果
    # 需要做的事情：1.在返回响应的时候，往cookie中添加一个csrf_token；2.往表单中添加一个隐藏的csrf_token或者在ajax中添加csrf_token
    CSRFProtect(app)
    Session(app)
    # 在index.html中添加自定义过滤器
    app.add_template_filter(do_index_class, "index_class")

    @app.after_request
    def after_request(response):
        # flask中generate_csrf()生成随机的csrf_token
        csrf_token = generate_csrf()
        # 往cookie中设置csrf_token
        response.set_cookie("csrf_token", csrf_token)
        return response

    # 导入蓝图
    from info.modules.index import index_blu
    from info.modules.passport import passport_blu
    # 注册蓝图
    app.register_blueprint(index_blu)
    app.register_blueprint(passport_blu)
    return app


def setup_log(config_name):
    # 设置日志的记录等级
    logging.basicConfig(level=config[config_name].LOG_LEVEL)  # 调试debug级别
    # 创建日志记录器,指明日志保存的路径,每个日志文件的最大容量,保存的日志文件个数上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
    # 创建日志记录的格式,日志等级,输入日志信息的文件名,行数,日志信息
    formatter = logging.Formatter("%(levelname)s %(filename)s:%(lineno)d %(message)s")
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象(flask app使用的)添加日志记录器
    logging.getLogger().addHandler(file_log_handler)
