from redis import StrictRedis
import os
import base64
import logging


class Config(object):
    """项目的配置基类"""
    # 设置48位随机生成的密钥
    key = base64.b64encode(os.urandom(48))
    SECRET_KEY = str(key)
    # 为mysql添加配置
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:mysql@127.0.0.1:3306/flask_newsweb"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 如果指定此配置为True，在视图函数请求结束后，数据库修改后开启自动提交的功能，自动执行db.session.commit()
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    # Redis服务器配置
    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379
    # 指定session保存在redis服务器中
    SESSION_TYPE = "redis"
    # 开启session签名
    SESSION_USE_SIGNER = True
    SESSION_REDIS = StrictRedis(host=REDIS_HOST, port=REDIS_PORT)
    # 设置成需要过期功能
    SESSION_PERMANENT = False
    # 设置过期时间
    PERMANENT_SESSION_LIFETIME = 86400 * 2
    # 设置日志等级
    LOG_LEVEL = logging.DEBUG


class DevelopmentConfig(Config):
    """开发环境下项目的配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境下项目的配置"""
    DEBUG = False
    LOG_LEVEL = logging.WARNING


class TestingConfig(Config):
    """单元测试环境下项目的配置"""
    DEBUG = True
    TESTING = True


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig
}

