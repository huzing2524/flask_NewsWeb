from flask import render_template, current_app, session, request, jsonify
from info import redis_store, constants
from info.models import User, News
from info.utils.response_code import RET
from . import index_blu


@index_blu.route("/news_list", methods=["GET"])
def news_list():
    """显示首页滚动新闻和分类新闻展示"""
    cid = request.args.get("cid", "1")
    page = request.args.get("page", "1")
    per_page = request.args.get("per_page", "10")
    try:
        cid = int(cid)
        page = int(page)
        per_page = int(per_page)
    except Exception as error:
        current_app.logger.error(error)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    filters = []
    if cid != 1:
        filters.append(News.category_id == cid)
    try:
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, per_page, False)
    except Exception as error:
        current_app.logger.error(error)
        return jsonify(errno=RET.DBERR, errmsg="查询失败")
    news_models_list = paginate.items
    total_page = paginate.pages
    current_page = paginate.page
    news_dict_li = []
    for news in news_models_list:
        news_dict_li.append(news.to_basic_dict())
    data = {
        "total_page": total_page,
        "current_page": current_page,
        "news_dict_li": news_dict_li
    }
    return jsonify(errno=RET.OK, errmsg="OK", data=data)


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

    # 右侧的新闻排行的逻辑
    news_list = []
    try:
        # news_list是查询语句
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as error:
        current_app.logger.error(error)
    news_dict_li = []
    for news in news_list:
        # news是每条新闻对应的模型对象; to_basic_dict()取类对象的属性转换成字典
        news_dict_li.append(news.to_basic_dict())
    data = {
        # 三元表达式
        "user_info": user.to_dict() if user else None,
        "news_dict_li": news_dict_li
    }

    # 2.把查询到的用户信息传递给浏览器渲染显示
    return render_template("news/index.html", data=data)


# send_static_file是flask去查找指定静态文件所调用的方法
@index_blu.route("/favicon.ico")
def favicon():
    return current_app.send_static_file("news/favicon.ico")
