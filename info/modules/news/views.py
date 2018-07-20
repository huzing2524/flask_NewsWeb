# 新闻详情页
from flask import render_template, current_app, g, jsonify, abort, request
from info import constants, db
from info.models import News, Category, Comment
from info.modules.news import news_blu
from info.utils.common import user_login_data
from info.utils.response_code import RET


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

    # 3.查询新闻，并判断新闻是否存在
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

    # 右侧的新闻排行的逻辑
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

    # 去查询评论数据

    data = {
        "user": user.to_dict() if user else None,  # 三元表达式
        "news_dict_li": news_dict_li,
        "news": news.to_dict(),
        "is_collected": is_collected
    }

    return render_template("news/detail.html", data=data)
