from flask import render_template, current_app, session
from info import redis_store
from info.models import User
from . import index_blu


@index_blu.route("/")
def index():
    """显示首页"""
    # 1.如果用户已经登录,将当前登录用户的数据传到模板中,供模板显示
    user_id = session.get("user_id", None)
    user = None
    if user_id:
        try:
            user = User.query.get(user_id)
        except Exception as error:
            current_app.logger.error(error)
    data = {
        # 三元表达式
        "user_info": user.to_dict() if user else None
    }

    # 2.把查询到的用户信息传递给浏览器渲染显示
    return render_template("news/index.html", data=data)


# send_static_file是flask去查找指定静态文件所调用的方法
@index_blu.route("/favicon.ico")
def favicon():
    return current_app.send_static_file("news/favicon.ico")
