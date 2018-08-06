from flask import Blueprint, session, redirect, url_for, request

# 创建蓝图对象
admin_blu = Blueprint("admin", __name__)

from . import views


@admin_blu.before_request
def check_admin():
    """每次登录管理员后台之前进行权限校验"""
    # 管理员用户，返回True；普通用户，返回False
    is_admin = session.get("is_admin", False)
    # 不是管理员 不是访问127.0.0.1:5000/admin.login管理员登录页面 就跳转url拒绝访问
    # 是管理员/访问管理员login界面就不进入if，执行其它视图函数
    if not is_admin and not request.url.endswith(url_for("admin.login")):
        # 跳转到新闻首页
        return redirect(url_for("/"))
