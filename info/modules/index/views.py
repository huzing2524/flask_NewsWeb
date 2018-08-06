from flask import render_template, current_app, request, jsonify, g
from info import constants
from info.models import News, Category
from info.utils.common import user_login_data
from info.utils.response_code import RET
from info.modules.index import index_blu


@index_blu.route("/news_list")
def news_list():
    """显示首页滚动新闻和分类新闻展示"""
    cid = request.args.get("cid", "1")  # 数据表info_category结构中:新闻的分类id,"1"代表分类为最新新闻,"2"代表股市新闻
    page = request.args.get("page", "1")  # 当前页数
    per_page = request.args.get("per_page", "10")  # 每一页加载多少条数据,默认值为10条新闻
    try:
        page = int(page)
        cid = int(cid)
        per_page = int(per_page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 查询新闻,设置过滤条件,只显示已审核通过(status=0)的新闻;审核中和审核不通过的新闻在查询时过滤掉
    # 当前新闻状态 如果为0代表审核通过，1代表审核中，-1代表审核不通过
    filters = [News.status == 0]
    if cid != 1:  # 查询的不是最新分类的数据
        # 数据表info_news中category_id为2,3,4; 此时需要添加条件
        filters.append(News.category_id == cid)

    try:
        # *filters 拆包; 按照创建时间排序; paginate分页查询
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, per_page, False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    # 取当前页的数据
    news_model_list = paginate.items  # 模型对象列表
    total_page = paginate.pages  # 总页数
    current_page = paginate.page  # 当前页

    # 将模型对象列表转成字典列表
    news_dict_li = []
    for news in news_model_list:
        news_dict_li.append(news.to_basic_dict())

    data = {
        "total_page": total_page,
        "current_page": current_page,
        "news_dict_li": news_dict_li
    }

    return jsonify(errno=RET.OK, errmsg="OK", data=data)


@index_blu.route("/")
@user_login_data
def index():
    """显示首页"""
    # 1.如果用户已经登录,将当前登录用户的数据传到模板中,供模板显示
    user = g.user

    # 首页右侧的新闻排行显示
    news_list = []
    try:
        # news_list查询的结果是mysql查询语句,需要循环遍历取出每一条新闻数据
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")

    news_dict_li = []
    # 遍历对象列表，将对象的字典添加到字典列表中
    for news in news_list:
        # news是每条新闻对应的模型对象; to_basic_dict()取类对象的属性转换成字典
        news_dict_li.append(news.to_basic_dict())

    # 查询分类数据，通过模板的形式渲染出来
    categories = Category.query.all()
    category_li = []
    for category in categories:
        category_li.append(category.to_dict())

    data = {
        "user": user.to_dict() if user else None,  # 三元表达式
        "news_dict_li": news_dict_li,
        "category_li": category_li
    }

    # 2.把查询到的用户信息传递给浏览器渲染显示
    return render_template("news/index.html", data=data)


# 在打开网页的时候，浏览器会默认去请求根路径+favicon.ico作网站标签的小图标
# send_static_file 是 flask 去查找指定的静态文件所调用的方法
@index_blu.route("/favicon.ico")
def favicon():
    return current_app.send_static_file("news/favicon.ico")
