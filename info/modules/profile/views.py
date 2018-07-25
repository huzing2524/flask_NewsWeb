from flask import render_template, g, redirect, request, jsonify, current_app, abort
from info import constants, db
from info.models import News, Category, User
from info.modules.profile import profile_blu
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET


@profile_blu.route("/other_news_list")
def other_news_list():
    """个人中心 点击其他人卡片跳转到其它用户新闻收藏列表"""
    other_id = request.args.get("user_id")
    page = request.args.get("p", 1)

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        other = User.query.get(other_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")

    if not other:
        return jsonify(errno=RET.NODATA, errmsg="当前用户不存在")

    try:
        # User.news_list 当前用户所发布的新闻
        paginate = other.news_list.paginate(page, constants.USER_COLLECTION_MAX_NEWS, False)
        news_li = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")

    news_dict_li = []
    for news_item in news_li:
        news_dict_li.append(news_item.to_basic_dict())

    data = {
        "news_list": news_dict_li,
        "total_page": total_page,
        "current_page": current_page
    }

    return jsonify(errno=RET.OK, errmsg="OK", data=data)


@profile_blu.route("/other_info")
@user_login_data
def other_info():
    """个人中心 关注用户卡片 点击跳转其他人信息"""
    user = g.user

    # 查询其它用户信息
    other_id = request.args.get("user_id")
    if not other_id:
        abort(404)

    try:
        other = User.query.get(other_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")

    if not other:
        abort(404)

    is_followed = False

    # 当前新闻有作者 & 当前用户已登录
    if other and user:
        # 当前新闻作者 在 登录用户关注者中
        if other in user.followed:
            is_followed = True

    data = {
        "is_followed": is_followed,
        "user": g.user.to_dict() if g.user else None,
        "other_info": other.to_dict()
    }

    return render_template("news/other.html", data=data)


@profile_blu.route("/user_follow")
@user_login_data
def user_follow():
    """个人中心 我的关注"""
    p = request.args.get("p", 1)
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    user = g.user

    follows = []
    current_page = 1
    total_page = 1

    try:
        # 从当前用户的所有关注者中分页查询
        paginate = user.followed.paginate(p, constants.USER_FOLLOWED_MAX_COUNT, False)
        follows = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    user_dict_li = []
    for follow_user in follows:
        user_dict_li.append(follow_user.to_dict())

    data = {
        "users": user_dict_li,
        "total_page": total_page,
        "current_page": current_page
    }

    return render_template("news/user_follow.html", data=data)


@profile_blu.route("/news_list")
@user_login_data
def user_news_list():
    """个人中心 新闻列表"""
    page = request.args.get("p", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    user = g.user
    news_list = []
    current_page = 1
    total_page = 1
    try:
        paginate = News.query.filter(News.user_id == user.id).paginate(page, constants.USER_COLLECTION_MAX_NEWS,
                                                                       False)
        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_li = []
    for news in news_list:
        news_dict_li.append(news.to_review_dict())

    data = {
        "news_list": news_dict_li,
        "total_page": total_page,
        "current_page": current_page,
    }

    return render_template("news/user_news_list.html", data=data)


@profile_blu.route("/news_release", methods=["GET", "POST"])
@user_login_data
def news_release():
    """新闻发布页面 显示新闻分类/发布新闻(分类、标题、内容)"""
    # ① 显示新闻分类
    if request.method == "GET":
        categories = []
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)

        category_dict_li = []
        for category in categories:
            category_dict_li.append(category.to_dict())
        # 删除索引为0，最新的分类。最新的分类是所有新闻按照create_time排序查询得到，发布的时候不能指定这个分类
        category_dict_li.pop(0)

        return render_template("news/user_news_release.html", data={"categories": category_dict_li})

    # ② 发布新闻(分类、标题、内容)，从表单中获取
    title = request.form.get("title")  # 标题
    source = "个人发布"  # 新闻来源
    digest = request.form.get("digest")  # 摘要
    content = request.form.get("content")  # 新闻内容
    index_image = request.files.get("index_image")  # 新闻索引图片
    category_id = request.form.get("category_id")  # 分类id

    if not all([title, source, digest, content, index_image, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        category_id = int(category_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        index_image_data = index_image.read()
        # 把图片上传到七牛云存储
        key = storage(index_image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 往数据库增加数据，1.初始化ORM模型对象 2.add()添加 commit()提交
    news = News()
    news.title = title
    news.digest = digest
    news.source = source
    news.content = content
    # 存储图片url时：前缀 + key
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    news.category_id = category_id
    news.user_id = g.user.id
    # 当前新闻状态 如果为0代表审核通过，1代表审核中，-1代表审核不通过
    # 发布新闻必须把状态设置为1，需要审核
    news.status = 1
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据保存失败")

    return jsonify(errno=RET.OK, errmsg="OK")


@profile_blu.route("/collection")
@user_login_data
def user_collection():
    """个人中心 用户新闻收藏"""
    # 从url地址中获取页数 location.href = "/user/collection?p=" + current
    page = request.args.get("p", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    user = g.user
    news_list = []
    total_page = 1
    current_page = 1
    try:
        paginate = user.collection_news.paginate(page, constants.USER_COLLECTION_MAX_NEWS, False)
        current_page = paginate.page
        total_page = paginate.pages
        news_list = paginate.items
    except Exception as e:
        current_app.logger.error(e)

    news_dict_li = []
    for news in news_list:
        news_dict_li.append(news.to_basic_dict())

    data = {
        "total_page": total_page,
        "current_page": current_page,
        "collections": news_dict_li
    }

    return render_template("news/user_collection.html", data=data)


@profile_blu.route("/pass_info", methods=["GET", "POST"])
@user_login_data
def pass_info():
    if request.method == "GET":
        return render_template("news/user_pass_info.html")

    old_password = request.json.get("old_password")
    new_password = request.json.get("new_password")

    if not all([old_password, new_password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 从原来的用户信息中查询原有密码和现在输入的old_password进行对比
    user = g.user
    if not user.check_password(old_password):
        return jsonify(errno=RET.PWDERR, errmsg="原密码错误")

    # 设置新密码,保存在g.user全局变量中，不需要再传递data
    user.password = new_password

    return jsonify(errno=RET.OK, errmsg="保存成功")


@profile_blu.route("/pic_info", methods=["GET", "POST"])
@user_login_data
def pic_info():
    """个人中心网页展示/修改用户头像"""
    user = g.user
    if request.method == "GET":
        # 浏览器GET请求，在g.user查询出个人信息的头像，直接返回
        return render_template("news/user_pic_info.html", data={"user": user.to_dict()})

    # 浏览器POST请求，修改头像
    # 1.获取上传的图片
    try:
        avatar = request.files.get("avatar").read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 2.上传头像
    try:
        # storage()自定义函数，调用七牛云第三方云存储
        key = storage(avatar)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="上传头像失败")

    # 3.保存头像图片的地址
    user.avatar_url = key
    return jsonify(errno=RET.OK, errmsg="OK", data={"avatar_url": constants.QINIU_DOMIN_PREFIX + key})


@profile_blu.route("/base_info", methods=["GET", "POST"])
@user_login_data
def base_info():
    """个人中心网页，根据传入的请求方式(GET展示信息/POST修改数据)做不同的事情"""
    if request.method == "GET":
        # 浏览器GET请求，在g.user查询出个人信息，直接返回
        return render_template("news/user_base_info.html", data={"user": g.user.to_dict()})

    # 浏览器POST请求，修改个人信息
    nick_name = request.json.get("nick_name")
    signature = request.json.get("signature")
    gender = request.json.get("gender")

    if not all([nick_name, signature, gender]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if gender not in (["WOMAN", "MAN"]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 修改用户信息，并且传递给(g变量)g.user保存
    user = g.user
    user.signature = signature
    user.nick_name = nick_name
    user.gender = gender

    return jsonify(errno=RET.OK, errmsg="OK")


@profile_blu.route("/info")
@user_login_data
def user_info():
    user = g.user
    if not user:
        # 没有登录，重定向到首页
        return redirect("/")
    data = {"user": user.to_dict()}
    return render_template("news/user.html", data=data)
