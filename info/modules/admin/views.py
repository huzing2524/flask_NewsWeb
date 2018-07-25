# 后台管理员页面
import time
from datetime import datetime, timedelta
from flask import request, render_template, current_app, redirect, url_for, session, g, jsonify, abort
from info import constants, db
from info.models import User, News, Category
from info.modules.admin import admin_blu
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET


@admin_blu.route("/news_type", methods=["GET", "POST"])
def news_type():
    """新闻分类编辑管理 显示/修改或新增新闻分类"""
    # 1.GET请求查询显示新闻的分类
    if request.method == "GET":
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return render_template("admin/news_type.html", errmsg="查询新闻分类失败")

        category_dict_li = []
        for category in categories:
            category_dict_li.append(category.to_dict())

        # 删除最新的分类
        category_dict_li.pop(0)

        data = {"categories": category_dict_li}

        return render_template("admin/news_type.html", data=data)

    # 2.POST请求方式增加/修改新闻分类
    cname = request.json.get("name")
    # 传入新闻的分类id代表编辑已存在的分类名称
    cid = request.json.get("id")

    if not cname:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 传入cid，说明是修改新闻分类的名称
    if cid:
        try:
            cid = int(cid)
            category = Category.query.get(cid)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="数据库查询失败")

        if not category:
            return jsonify(errno=RET.NODATA, errmsg="未查询到该新闻分类")

        # 修改保存新闻的分类名称
        category.name = cname

    # 没有分类id代表新增新闻的分类
    # 新增新闻分类的名称，初始化ORM对象模型，然后保存、提交
    else:
        category = Category()
        category.name = cname
        db.session.add(category)

    return jsonify(errno=RET.OK, errmsg="OK")


@admin_blu.route("/news_edit_detail", methods=["GET", "POST"])
def news_edit_detail():
    """新闻内容详情展示/版式编辑"""
    # 1.GET请求方式展示新闻内容详情
    if request.method == "GET":
        news_id = request.args.get("news_id")
        if not news_id:
            abort(404)

        try:
            news_id = int(news_id)
        except Exception as e:
            current_app.logger.error(e)
            return render_template("admin/news_edit_detail.html", errmsg="参数错误")

        try:
            # 查询新闻
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)
            return render_template("admin/news_edit_detail.html", errmsg="数据库查询失败")

        if not news:
            return render_template("admin/news_edit_detail.html", errmsg="新闻不存在")

        # 查询显示新闻的分类
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return render_template("admin/news_edit_detail.html", errmsg="数据库查询失败")

        if not categories:
            return render_template("admin/news_edit_detail.html", errmsg="该分类不存在")

        category_dict_li = []
        for category in categories:
            cate_dict = category.to_dict()
            # 遍历到的分类id=当前新闻的分类id
            if category.id == news.category_id:
                # 转换后的分类字典添加被选中的标记键值对,当前新闻显示当前所属的分类
                cate_dict["is_selected"] = True
            category_dict_li.append(cate_dict)

        # 删除索引为0，新闻最新的分类
        category_dict_li.pop(0)

        data = {
            "news": news.to_dict(),
            "categories": category_dict_li
        }

        return render_template("admin/news_edit_detail.html", data=data)

    # 2.POST请求方式编辑提交新闻内容详情
    news_id = request.form.get("news_id")
    title = request.form.get("title")
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image")
    category_id = request.form.get("category_id")

    if not all([title, digest, content, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询失败")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到此新闻")

    if index_image:
        try:
            index_image = index_image.read()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

        # 把新闻标题照片上传到七牛云
        try:
            key = storage(index_image)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.THIRDERR, errmsg="图片上传失败")

        # 把图片的链接存储到mysql
        news.index_image_url = constants.QINIU_DOMIN_PREFIX + key

    # 保存新闻编辑的数据到mysql
    news.title = title
    news.digest = digest
    news.content = content
    news.category_id = category_id

    return jsonify(errno=RET.OK, errmsg="OK")


@admin_blu.route("/news_edit")
def news_edit():
    """新闻版式编辑"""
    page = request.args.get("p", 1)
    keywords = request.args.get("keywords", None)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    news_list = []
    current_page = 1
    total_page = 1

    filters = [News.status == 0]  # 审核通过的新闻
    if keywords:
        # 如果有关键字,那么向过滤条件中添加
        filters.append(News.title.contains(keywords))

    try:
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page,
                                                                                          constants.ADMIN_NEWS_PAGE_MAX_COUNT,
                                                                                          False)
        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_list = []
    for news in news_list:
        news_dict_list.append(news.to_basic_dict())

    context = {
        "total_page": total_page,
        "current_page": current_page,
        "news_list": news_dict_list
    }

    return render_template("admin/news_edit.html", data=context)


@admin_blu.route("/news_review_action", methods=["POST"])
def news_review_action():
    """新闻内容审核--->通过/拒绝(拒绝原因)"""
    news_id = request.json.get("news_id")
    action = request.json.get("action")

    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if action not in (["accept", "reject"]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="未查询到此新闻")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="没有此新闻")

    # 新闻审核通过
    if action == "accept":
        # 当前新闻状态 如果为0代表审核通过，1代表审核中，-1代表审核不通过
        news.status = 0  # 审核通过
    else:
        # 新闻审核拒绝
        reason = request.json.get("reason")  # 获取拒绝原因
        if not reason:
            return jsonify(errno=RET.PARAMERR, errmsg="请输入拒绝原因")
        news.status = -1  # 新闻审核拒绝
        news.reason = reason  # 保存拒绝原因

    return jsonify(errno=RET.OK, errmsg="OK")


@admin_blu.route("/news_review_detail/<int:news_id>")
def news_review_detail(news_id):
    """新闻管理--->新闻内容审核"""
    news = None
    try:
        # 通过html传入的news_id=news.id查询新闻
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)

    if not news:
        return render_template("admin/news_review_detail.html", data={"errmsg": "未查询到此新闻"})

    data = {"news": news.to_dict()}
    return render_template("admin/news_review_detail.html", data=data)


@admin_blu.route("/news_review")
def news_review():
    """新闻管理--->新闻审核"""
    page = request.args.get("p", 1)
    keywords = request.args.get("keywords", None)  # 取到搜索的关键字
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    news_list = []
    current_page = 1
    total_page = 1

    # 当前新闻状态 如果为0代表审核通过，1代表审核中，-1代表审核不通过
    # 数据库查询过滤条件:新闻状态不为0,只显示审核中和审核不通过的新闻
    filters = [News.status != 0]
    if keywords:
        # 把关键字添加到过滤条件(新闻标题中)
        filters.append(News.title.contains(keywords))

    try:
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page,
                                                                                          constants.ADMIN_NEWS_PAGE_MAX_COUNT,
                                                                                          False)
        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_list = []
    for news in news_list:
        news_dict_list.append(news.to_review_dict())

    context = {
        "total_page": total_page,
        "current_page": current_page,
        "news_list": news_dict_list
    }

    return render_template("admin/news_review.html", data=context)


@admin_blu.route("/user_list")
def user_list():
    """用户信息列表"""
    # 从当前浏览页面的请求中获取当前页数,默认值是第一页
    page = request.args.get("page", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1  # 有异常置为第一页

    users = []
    current_page = 1
    total_page = 1

    try:
        paginate = User.query.filter(User.is_admin == False).paginate(page, constants.ADMIN_USER_PAGE_MAX_COUNT, False)
        users = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    user_dict_li = []
    for user in users:
        user_dict_li.append(user.to_admin_dict())

    data = {
        "users": user_dict_li,
        "total_page": total_page,
        "current_page": current_page
    }

    return render_template("admin/user_list.html", data=data)


@admin_blu.route("/user_count")
def user_count():
    """用户人数统计/折线图"""
    total_count = 0
    try:
        # 总人数
        total_count = User.query.filter(User.is_admin == False).count()
    except Exception as e:
        current_app.logger.error(e)

    mon_count = 0  # 月新增人数
    t = time.localtime()  # 取出当前时间 time.struct_time(tm_year=2018, tm_mon=7, tm_mday=22, tm_hour=1, tm_min=58, tm_sec=53, tm_wday=6, tm_yday=203, tm_isdst=1)
    # strptime 把时间格式的字符串 转换成 时间对象
    # 生成每个月的第一天
    begin_mon_date = datetime.strptime(("%d-%02d-01" % (t.tm_year, t.tm_mon)), "%Y-%m-%d")  # 2018-07-01 00:00:00
    try:
        # 月新增人数
        mon_count = User.query.filter(User.is_admin == False, User.create_time > begin_mon_date).count()
    except Exception as e:
        current_app.logger.error(e)

    day_count = 0  # 日新增人数
    begin_day_date = datetime.strptime(("%d-%02d-%02d" % (t.tm_year, t.tm_mon, t.tm_mday)),
                                       "%Y-%m-%d")  # 2018-07-22 00:00:00
    try:
        day_count = User.query.filter(User.is_admin == False, User.create_time > begin_day_date).count()
    except Exception as e:
        current_app.logger.error(e)

    # 折线图,按照天数统计活跃人数
    active_time = []  # 用户最后一次登录的时间
    active_count = []  # 登录的用户人数
    # 取到今天的时间字符串
    today_date_str = ("%d-%02d-%02d" % (t.tm_year, t.tm_mon, t.tm_mday))
    # 转换成datetime时间对象 今天的时间 年-月-日 时:分:秒 2018-07-22 00:00:00
    today_date = datetime.strptime(today_date_str, "%Y-%m-%d")

    for i in range(0, 31):  # 在一个月31天内循环
        # print(timedelta(days=2))------2 days, 0:00:00
        # timedelta：第i天的24个小时的时间
        # 取到某一天的0点0分
        begin_date = today_date - timedelta(days=i)  # 每次循环,begin_today_date的天数-i天的时间,时间向前减少i天
        # 取到下一天(i-1)的0点0分
        end_date = today_date - timedelta(days=(i - 1))  # 每次循环,begin_today_date的天数-(i-1),时间向前减少i-1天,比上面的天数推后一天

        # 查询今天活跃的用户数量,过滤条件是:最后一次登录时间,大于昨天0: 00, 小于24: 00
        count = User.query.filter(User.is_admin == False, User.last_login >= begin_date,
                                  User.last_login < end_date).count()
        active_count.append(count)
        # strftime：把datetime时间对象类型转换成字符串
        active_time.append(begin_date.strftime("%Y-%m-%d"))

    # 反转,让最近的一天显示在最右边(最后)
    active_time.reverse()
    active_count.reverse()

    data = {
        "total_count": total_count,
        "mon_count": mon_count,
        "day_count": day_count,
        "active_time": active_time,
        "active_count": active_count
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
    # GET获取方式展示登录界面
    if request.method == "GET":
        user_id = session.get("user_id", None)
        is_admin = session.get("is_admin", False)
        # 如果管理员已经登录，重定向到index管理员主页
        if user_id and is_admin:
            return redirect(url_for("admin.index"))

        return render_template("admin/login.html")

    # 登录界面是form表单
    username = request.form.get("username")
    password = request.form.get("password")

    if not all([username, password]):
        # 如果是ajax请求,返回jsonify; 通过form表单提交,错误直接返回原网页,带上错误信息
        return render_template("admin/login.html", errmsg="参数错误")

    try:
        user = User.query.filter(User.mobile == username, User.is_admin == True).first()
    except Exception as e:
        current_app.logger.error(e)
        return render_template("admin/login.html", errmsg="用户信息查询失败")

    if not user:
        return render_template("admin/login.html", errmsg="未查询到该用户")

    if not user.check_password(password):
        return render_template("admin/login.html", errmsg="密码错误")

    session["user_id"] = user.id
    session["mobile"] = user.mobile
    session["nick_name"] = user.nick_name
    session["is_admin"] = user.is_admin

    # 根据视图函数名称得到当前所指向的url,需要指定是admin包下面的index视图函数
    # 不能使用render_template,因为它是渲染模板,传递数据返回当前页面,url地址并没有跳转
    # 只能使用redirect跳转到后台管理员主页面.url地址要从login变化成index
    return redirect(url_for("admin.index"))
