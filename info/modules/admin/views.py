# 后台管理员页面
import time
from datetime import datetime, timedelta
from flask import request, render_template, current_app, redirect, url_for, session, g
from info.models import User
from info.modules.admin import admin_blu
from info.utils.common import user_login_data


@admin_blu.route("/user_count")
def user_count():
    """用户人数统计/折线图"""
    total_count = 0
    try:
        # 总人数
        total_count = User.query.filter(User.is_admin == False).count()
    except Exception as e:
        current_app.logger.error(e)

    mon_count = 0
    t = time.localtime()  # 取出当前时间
    # 把字符串转成datetime对象
    begin_mon_date = datetime.strptime(("%d-%02d-01" % (t.tm_year, t.tm_mon)), "%Y-%m-%d")
    try:
        # 月新增人数
        mon_count = User.query.filter(User.is_admin == False, User.create_time > begin_mon_date).count()
    except Exception as e:
        current_app.logger.error(e)

    day_count = 0
    # 日新增人数
    begin_day_date = datetime.strptime(("%d-%02d-%02d" % (t.tm_year, t.tm_mon, t.tm_mday)), "%Y-%m-%d")
    try:
        day_count = User.query.filter(User.is_admin == False, User.create_time > begin_day_date).count()
    except Exception as e:
        current_app.logger.error(e)

    # 折线图数据
    active_time = []
    active_count = []
    # 取到今天的时间字符串
    today_date_str = ("%d-%02d-%02d" % (t.tm_year, t.tm_mon, t.tm_mday))
    # 转换成datetime时间对象
    today_date = datetime.strptime(today_date_str, "%Y-%m-%d")

    for i in range(0, 31):
        # 取到某一天的0点0分
        begin_date = today_date - timedelta(days=i)  # timedelta：第i天的24个小时的时间
        # 取到下一天(i-1)的0点0分
        end_date = today_date - timedelta(days=(i - 1))
        # 每天的活跃人数统计数据是：最后登录时间大于昨天的0:00，小于今天的24:00
        count = User.query.filter(User.is_admin == False, User.last_login >= begin_date,
                                  User.last_login <= end_date).count()
        active_count.append(count)
        active_time.append(begin_date.strftime("%Y-%m-%d"))
        # 反转,让最近的一天显示在最右边(最后)
        active_count.reverse()
        active_time.reverse()

    data = {
        "total_count": total_count,
        "mon_count": mon_count,
        "day_count": day_count,
        "active_count": active_count,
        "active_time": active_time
    }
    return render_template("admin/user_count.html", data=data)


@admin_blu.route("/index")
@user_login_data
def index():
    """后台管理员主页"""
    user = g.user
    return render_template("admin/index.html", user=user.to_dict())


@admin_blu.route("/login", methods=["GET", "POST"])
def login():
    """后台管理员账号登录界面"""
    # ① GET获取方式展示登录界面
    if request.method == "GET":
        # 如果管理员已经登录，重定向到index管理员主页
        user_id = session.get("user_id", None)
        is_admin = session.get("is_admin", False)
        if user_id and is_admin:
            return redirect(url_for("admin.index"))

        return render_template("admin/login.html")

    # ② POST提交方式管理员登录
    username = request.form.get("username")
    password = request.form.get("password")

    if not all([username, password]):
        return render_template("admin/login.html", errmsg="参数错误")

    try:
        user = User.query.filter(User.mobile == username, User.is_admin == True).first()
    except Exception as e:
        current_app.logger.error(e)
        return render_template("admin/login.html", errmsg="用户信息查询失败")

    if not user:
        return render_template("admin/login.html", errmsg="未查询到该用户")
    if not user.check_passowrd(password):
        return render_template("admin/login.html", errmsg="密码错误")

    session["user_id"] = user.id
    session["mobile"] = user.mobile
    session["nick_name"] = user.nick_name
    session["is_admin"] = user.is_admin

    # 只能重定向，不能渲染模板网页，因为登录成功后要跳转到管理员主页，url地址要从login变化成index，渲染模板只能返回数据，url地址不会变
    return redirect(url_for("admin.index"))  # admin模块下的index视图函数
