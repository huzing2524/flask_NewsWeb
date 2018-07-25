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
    """新闻分类管理"""
    # 1.GET请求方式展示新闻分类
    if request.method == "GET":
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return render_template("admin/news_type.html", errmsg="数据库查询失败")

        category_dict_li = []
        for category in categories:
            category_dict_li.append(category.to_dict())

        # 删除最新的分类
        category_dict_li.pop(0)

        data = {"categories": category_dict_li}
        return render_template("admin/news_type.html", data=data)

    # 2.POST请求方式增加/修改新闻分类
    cname = request.json.get("name")
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
            return jsonify(errno=RET.NODATA, errmsg="未查询到分类数据")

        # 保存分类的名称
        category.name = cname

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

        try:
            # 查询新闻分类
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
                # 记录当前分类被选中的状态，方便直接显示某个新闻的分类
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
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到此新闻")

    if index_image:
        try:
            index_image = index_image.read()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

        try:
            key = storage(index_image)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.THIRDERR, errmsg="上传图片失败")

        news.index_image_url = constants.QINIU_DOMIN_PREFIX + key

    news.title = title
    news.digest = digest
    news.content = content
    news.category_id = category_id

    return jsonify(errno=RET.OK, errmsg="OK")


@admin_blu.route("/news_edit")
def news_edit():
    """新闻编辑"""
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

    filters = [News.status == 0]
    if keywords:
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

    # 过滤条件：新闻状态不为0，剔除审核通过的新闻
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
    """用户统计列表"""
    page = request.args.get("page", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

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

    # 用户登录活跃人数 折线图数据
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
@user_login_data
def login():
    """后台管理员账号登录界面"""
    # ① GET获取方式展示登录界面
    if request.method == "GET":
        user_id = session.get("user_id", None)
        is_admin = session.get("is_admin", False)
        # 如果管理员已经登录，重定向到index管理员主页
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

    if not user.check_password(password):
        return render_template("admin/login.html", errmsg="密码错误")

    session["user_id"] = user.id
    session["mobile"] = user.mobile
    session["nick_name"] = user.nick_name
    session["is_admin"] = user.is_admin

    # 只能重定向，不能渲染模板网页，因为登录成功后要跳转到管理员主页，url地址要从login变化成index，渲染模板只能返回数据，url地址不会变
    return redirect(url_for("admin.index"))  # admin模块下的index视图函数
