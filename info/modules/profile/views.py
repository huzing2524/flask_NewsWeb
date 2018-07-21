from flask import render_template, g, redirect, request, jsonify, current_app
from info import constants
from info.modules.profile import profile_blu
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET


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
    else:
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
        return redirect("/")
    data = {
        "user": user.to_dict()
    }
    return render_template("news/user.html", data=data)
