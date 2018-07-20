# 公用的自定义工具类
from flask import session, current_app, g
from info.models import User
import functools


def do_index_class(index):
    """返回指定索引对应的类选择器值"""
    if index == 0:
        return "first"
    elif index == 1:
        return "second"
    elif index == 2:
        return "third"
    return ""


# 使用@functools.wraps(f)去装饰内层函数，可以保持内层函数的函数__name__名不变，
# 否则使用@user_login_data装饰其它函数都会变成wrapper的名称，url_map的路由和函数名映射关系就会重复导致出错
def user_login_data(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id", None)
        user = None
        if user_id:
            try:
                user = User.query.get(user_id)
            except Exception as e:
                current_app.logger.error(e)
        # g变量是全局变量，把查询出来的用户信息保存，然后在所有地方都能使用
        g.user = user
        return f(*args, **kwargs)
    return wrapper
