# 个人用户中心资料展示页面
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
        paginate = News.query.filter(News.user_id == user.id).paginate(page, constants.USER_COLLECTION_MAX_NEWS, False)
        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_li = []
    for news in news_list:
        # to_review_dict() 新闻审核的状态status, 未审核通过的原因reason
        news_dict_li.append(news.to_review_dict())

    data = {
        "news_list": news_dict_li,
        "total_page": total_page,
        "current_page": current_page
    }

    return render_template("news/user_news_list.html", data=data)


@profile_blu.route("/news_release", methods=["GET", "POST"])
@user_login_data
def news_release():
    """新闻发布页面 显示新闻分类/发布新闻(分类、标题、内容)"""
    # ① 显示新闻分类
    if request.method == "GET":
        # 1.数据表模型对象Category查询所有的新闻分类数据
        categories = []
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)

        category_dict_li = []
        for category in categories:
            category_dict_li.append(category.to_dict())
        # 删除索引为0的分类:删除最新的新闻分类.最新的分类是查询所有新闻的create_time排序得到的,发布新闻不允许指定这个分类
        category_dict_li.pop(0)

        return render_template("news/user_news_release.html", data={"categories": category_dict_li})

    # ② 发布新闻(分类、标题、内容)，从表单中获取
    # 新闻标题
    title = request.form.get("title")
    # 新闻来源
    source = "个人发布"
    # 新闻摘要
    digest = request.form.get("digest")
    # 新闻内容
    content = request.form.get("content")
    # 新闻索引图片
    index_image = request.files.get("index_image")
    # 新闻分类id
    category_id = request.form.get("category_id")

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
    # 取出当前的页数,没有数据默认值为第一页
    page = request.args.get("p", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    # 查询用户指定页数收藏的新闻,根据选中页数按钮显示
    user = g.user
    # collection_news 当前用户收藏的所有新闻, lazy="dynamic" 动态查询
    # paginate 分页查询参数: 当前页数, 每页数据数量,是否有错误输出
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
    """修改密码页面"""
    if request.method == "GET":
        return render_template("news/user_pass_info.html")

    old_password = request.json.get("old_password")
    new_password = request.json.get("new_password")

    if not all([old_password, new_password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    user = g.user
    # check_passowrd是数据表模型中哈希加密后的密码与传入的密码进行对比
    # 判断当前使用的旧密码是否正确
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
    # 浏览器GET请求，在g.user查询出个人信息的头像，直接返回
    if request.method == "GET":
        return render_template("news/user_pic_info.html", data={"user": user.to_dict()})

    # 请求方式是"POST"时,修改上传用户图片
    # 1.取用户上传的图片
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

    # 3.保存头像地址在user中
    # QINIU_DOMIN_PREFIX是七牛云的url前缀,本地的图片往七牛云上传时会自动生成一个key,把这个key储存在mysql中,就可以通过key去七牛云请求查找到照片
    user.avatar_url = key
    return jsonify(errno=RET.OK, errmsg="发送成功", data={"avatar_url": constants.QINIU_DOMIN_PREFIX + key})


@profile_blu.route("/base_info", methods=["GET", "POST"])
@user_login_data
def base_info():
    """个人中心网页--->用户信息展示，根据传入的请求方式(GET展示信息/POST修改数据)做不同的事情"""
    # 1.请求方式是GET时,是直接从g.user获取获取用户信息,然后返回给浏览器展示
    if request.method == "GET":
        return render_template("news/user_base_info.html", data={"user": g.user.to_dict()})

    # 2.请求方式是POST时,是要修改用户信息
    nick_name = request.json.get("nick_name")
    signature = request.json.get("signature")
    gender = request.json.get("gender")

    if not all([nick_name, signature, gender]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if gender not in (["WOMAN", "MAN"]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 修改用户信息,签名/昵称/性别，并且传递给(g变量)g.user保存
    user = g.user
    user.signature = signature
    user.nick_name = nick_name
    user.gender = gender

    return jsonify(errno=RET.OK, errmsg="OK")


@profile_blu.route("/info")
@user_login_data
def user_info():
    """个人中心根路由,主页"""
    user = g.user
    if not user:
        # 没有登录，重定向到首页
        return redirect("/")
    data = {"user": user.to_dict()}
    return render_template("news/user.html", data=data)
