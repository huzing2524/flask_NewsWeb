# 新闻详情页
from flask import render_template, current_app, g, jsonify, abort, request
from info import constants, db
from info.models import News, Comment, CommentLike, User
from info.modules.news import news_blu
from info.utils.common import user_login_data
from info.utils.response_code import RET


@news_blu.route("/followed_user", methods=["POST"])
@user_login_data
def followed_user():
    """新闻详情页 关注/取消关注用户"""
    user = g.user  # 登录用户
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    user_id = request.json.get("user_id")  # 当前新闻的作者用户
    action = request.json.get("action")

    if not all([user_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if action not in (["follow", "unfollow"]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        other = User.query.get(user_id)  # 查询新闻作者的用户信息
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询失败")

    if not other:
        return jsonify(errno=RET.NODATA, errmsg="未查询到新闻作者")

    # 点击的是关注按钮
    if action == "follow":
        # user.followed 取到该用户关注的所有人
        # 新闻作者不在用户关注列表中才去添加关注
        if other not in user.followed:
            # append(other) 该用户的关注列表添加该新闻的作者用户
            user.followed.append(other)
        else:
            return jsonify(errno=RET.DATAEXIST, errmsg="当前用户已被关注")
    # 点击的是取消关注按钮
    else:
        if other in user.followed:
            # 该用户关注者中移除当前作者
            user.followed.remove(other)
        else:
            return jsonify(errno=RET.DATAEXIST, errmsg="当前用户未被关注")

    return jsonify(errno=RET.OK, errmsg="OK")


@news_blu.route("/comment_like", methods=["POST"])
@user_login_data
def comment_like():
    """评论点赞/取消点赞"""
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    comment_id = request.json.get("comment_id")
    action = request.json.get("action")

    if not all([comment_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if action not in (["add", "remove"]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        comment_id = int(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        # 通过传入的comment_id评论id在Comment模型表中查找到当前对应的评论
        comment = Comment.query.get(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")
    if not comment:
        return jsonify(errno=RET.NODATA, errmsg="评论不存在")

    # 点赞评论
    if action == "add":
        # 在中间表CommentLike中根据过滤条件(用户id,查询出的评论id)查询
        comment_like_model = CommentLike.query.filter(CommentLike.user_id == user.id,
                                                      CommentLike.comment_id == comment.id).first()
        # 查询结果为空，说明评论是处于非点赞状态，增加两个字段user_id，comment_id的值，add使其变为点赞状态
        if not comment_like_model:
            comment_like_model = CommentLike()
            comment_like_model.user_id = user.id
            comment_like_model.comment_id = comment.id
            db.session.add(comment_like_model)
            # 更新添加点赞次数
            comment.like_count += 1
    else:
        # 取消点赞
        comment_like_model = CommentLike.query.filter(CommentLike.user_id == user.id,
                                                      CommentLike.comment_id == comment.id).first()
        # 查询结果有值，说明当前评论处于点赞状态，要delete删除点赞状态
        if comment_like_model:
            db.session.delete(comment_like_model)
            # 更新点赞次数
            comment.like_count -= 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库操作失败")

    return jsonify(errno=RET.OK, errmsg="OK")


@news_blu.route("/news_comment", methods=["POST"])
@user_login_data
def comment_news():
    """评论新闻或者回复某条新闻下指定的评论，包括主评论和子评论"""
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    # 1. 取到请求参数
    news_id = request.json.get("news_id")
    comment_content = request.json.get("comment")
    parent_id = request.json.get("parent_id")

    # 2. 判断参数
    if not all([news_id, comment_content]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        news_id = int(news_id)
        if parent_id:
            parent_id = int(parent_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 3.查询新闻，并判断新闻是否存在.只有当前新闻存在的时候才允许评论，可以执行下面的代码
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到新闻数据")

    # 4. 初始化一个评论模型，并且赋值
    comment = Comment()
    comment.user_id = user.id
    comment.news_id = news_id
    comment.content = comment_content

    # 主评论的parent_id为None，子评论的parent_id字段有值，为主评论的主键id
    if parent_id:
        # 子评论
        comment.parent_id = parent_id

    # 在函数return返回结束之前就需要传入参数comment的用户id，新闻id，评论内容
    # 但是自动提交是在函数运行结束之后才会提交。所以需要手动try...commit()...except...rollback()
    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()

    return jsonify(errno=RET.OK, errmsg="OK", data=comment.to_dict())


@news_blu.route("/news_collect", methods=["POST"])
@user_login_data
def collect_news():
    """收藏/取消新闻"""
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    # 1. 接受参数
    news_id = request.json.get("news_id")
    action = request.json.get("action")

    # 2. 判断参数
    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if action not in ["collect", "cancel_collect"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        news_id = int(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 3.查询新闻，并判断新闻是否存在
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到新闻数据")

    # 4. 收藏以及取消收藏
    if action == "cancel_collect":
        # 取消收藏
        if news in user.collection_news:
            user.collection_news.remove(news)
    else:
        # 收藏新闻
        if news not in user.collection_news:
            # 添加到用户的新闻收藏列表
            user.collection_news.append(news)

    return jsonify(errno=RET.OK, errmsg="收藏/取消收藏成功")


@news_blu.route("/<int:news_id>")
@user_login_data
def news_detail(news_id):
    """新闻详情页"""
    # 查询用户登录信息
    user = g.user

    # 右侧的新闻排行的展示
    news_list = []
    try:
        # news_list是查询语句
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)

    # 定义一个空的字典列表，里面装的就是字典
    news_dict_li = []
    # 遍历对象列表，将对象的字典添加到字典列表中
    for news in news_list:
        # news是每条新闻对应的模型对象; to_basic_dict()取类对象的属性转换成字典
        news_dict_li.append(news.to_basic_dict())

    # 查询新闻数据
    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)

    if not news:
        # 报404错误，404错误统一显示页面后续再处理
        abort(404)

    # 更新新闻的点击次数
    news.clicks += 1

    # 是否是收藏　
    is_collected = False

    # 判断用户是否登录
    if user:
        # 判断当前新闻是否在数据库中的收藏表中
        # user.collection_news结果是一个sql语句(模型对象)，不用添加user.collection_news.all()立即查询出结果；
        # 在成员判断语句if x in X:或者循环语句for x in X中，因为设置了lazy="dynamic",所以会自动运行 sql语句.all() 查询出结果
        if news in user.collection_news:
            is_collected = True

    # 去查询新闻详情页某个新闻的所有评论内容
    comments = []
    try:
        comments = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)

    # 查询当前用户在当前新闻里面点赞了哪些评论
    comment_like_ids = []
    if g.user:
        try:
            # 1.查询出当前新闻的所有评论id，得到列表[1, 2, 3, 4, 5]，其中包括多个用户对当前新闻的评论，包括多个点赞和未点赞的评论
            comment_ids = [comment.id for comment in comments]  # 列表推导式
            # 2.在User和Comment的中间关系表CommentLike中查询出 当前用户 的 所有点赞评论 的id
            # 过滤条件①：已经点赞的评论id(CommentLike.comment_id)在所有当前新闻的评论id中(comment_ids)，满足这个条件才取出，剔除其它没有点赞的评论
            # 过滤条件②：中间关系表CommentLike中的用户 是 浏览当前新闻的登录登录用户，满足这个条件才取出，剔除其它无关用户
            # 结果是CommentLike关系表中查询出来的模型对象
            comment_likes = CommentLike.query.filter(CommentLike.comment_id.in_(comment_ids),
                                                     CommentLike.user_id == g.user.id).all()
            # 3.循环遍历通过comment_id字段取到所有被点赞的评论的id
            comment_like_ids = [comment_like.comment_id for comment_like in comment_likes]  # 查询出[3, 5]
        except Exception as e:
            current_app.logger.error(e)

    comment_dict_li = []
    for comment in comments:
        comment_dict = comment.to_dict()
        # 默认全部添加了未点赞的状态
        comment_dict["is_like"] = False
        # 从数据库中查询每一条评论是 点赞/未点赞 的状态
        # 如果 每一条评论的id 都在 被点赞的评论id列表中comment_like_ids
        if comment.id in comment_like_ids:
            # 给评论字典comment_dict添加 "is_like" 点赞的状态
            comment_dict["is_like"] = True
        comment_dict_li.append(comment_dict)

    # 新闻详情页右侧 当前新闻的作者未关注
    is_followed = False

    # 新闻有作者 & 访问网站用户已登录
    if news.user and user:
        # 判断 新闻的作者 是否在 登录用户的关注者中
        if news.user in user.followed:
            # 把关注状态设置为 已关注该新闻作者
            is_followed = True

    data = {
        "user": user.to_dict() if user else None,  # 三元表达式
        "news_dict_li": news_dict_li,
        "news": news.to_dict(),
        "is_collected": is_collected,
        "is_followed": is_followed,
        "comments": comment_dict_li
    }

    return render_template("news/detail.html", data=data)
