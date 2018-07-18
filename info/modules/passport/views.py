import random
import re
from datetime import datetime
from flask import request, abort, current_app, make_response, json, jsonify, session
from info import redis_store, constants, db
from info.libs.yuntongxun.sms import CCP
from info.models import User
from info.utils.response_code import RET
from . import passport_blu
from info.utils.captcha.captcha import captcha


@passport_blu.route("/logout", methods=["GET", "POST"])
def logout():
    """退出登录"""
    # pop删除redis服务器中session,保持登录状态结束
    # pop会有一个返回值,如果要移除的key不存在,会返回第二个参数None
    session.pop("user_id", None)
    session.pop("mobile", None)
    session.pop("nick_name", None)
    return jsonify(errno=RET.OK, errmsg="退出登录成功")


@passport_blu.route("/login", methods=["POST"])
def login():
    """登录账号"""
    # 1.获取参数
    param_dict = request.json
    mobile = param_dict.get("mobile")
    password = param_dict.get("password")
    # 2.校验参数
    if not all([mobile, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if not re.match("1[35678]\\d{9}", mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="手机号格式错误")
    # 3.在Mysql数据库查询是否存在这个用户
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as error:
        current_app.logger.error(error)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")
    # 4.判断用户是否存在
    if not user:
        return jsonify(errno=RET.NODATA, errmsg="用户不存在")
    # 5.校验密码是否正确,调用models中的实例方法把密文密码和明文密码进行比对
    if not user.check_passowrd(password):
        return jsonify(errno=RET.PWDERR, errmsg="密码错误")
    # 6.往session中添加保存数据保持登录状态
    session["user_id"] = user.id
    session["mobile"] = user.mobile
    session["nick_name"] = user.nick_name
    # 7.记录用户最后一次登录的时间
    user.last_login = datetime.now()
    # 如果在视图函数中，对模型的属性有修改，那么需要commit提交到数据库保存；
    # 如果事先对SQLAlchemy进行过配置，那么就不用写commit()
    # 8. 成功的响应
    return jsonify(errno=RET.OK, errmsg="登录成功")


@passport_blu.route("/register", methods=["POST"])
def register():
    """注册账号"""
    # 1.获取参数
    param_dict = request.json
    mobile = param_dict.get("mobile")
    smscode = param_dict.get("smscode")
    password = param_dict.get("password")
    # 2.校验参数
    if not all([mobile, smscode, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不够")
    if not re.match("1[35678]\\d{9}", mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="手机号格式错误")
    # 3. 获取服务器保存的真实短信验证码内容
    try:
        real_sms_code = redis_store.get("SMS_" + mobile)
    except Exception as error:
        current_app.logger.error(error)
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")
    # 4.校验用户输入的短信验证码内容和数据库内容是否一致
    if not real_sms_code:
        return jsonify(errno=RET.NODATA, errmsg="验证码已过期")
    if real_sms_code != smscode:
        return jsonify(errno=RET.DATAERR, errmsg="验证码输入错误")
    # 5.如果比对后数据一致,初始化User模型,并且赋值属性
    user = User()
    user.mobile = mobile
    # 暂时没有昵称,使用手机号代替
    user.nick_name = mobile
    # user对象调用password属性时,就会调用装饰器@password.setter方法,把值传递给value
    # 1.设置user表模型添加password字段并且加密; 2.给info_user表格中password_hash字段赋值
    user.password = password
    # 记录用户最后一次登录的时间
    user.last_login = datetime.now()
    # 6.添加到数据库
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as error:
        current_app.logger.error(error)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据保存失败")
    # 7.往session中添加保存数据保持登录状态
    session["user_id"] = user.id
    session["mobile"] = user.mobile
    session["nick_name"] = user.nick_name
    # 8.返回响应
    return jsonify(errno=RET.OK, errmsg="注册成功")


@passport_blu.route("/sms_code", methods=["POST"])
def send_sms_code():
    """短信验证码处理"""
    # 1.获取参数:手机号/图片验证码内容/图片验证码的编号(随机值)
    # loads() 把字符串转换成json字典格式
    params_dict = json.loads(request.data)
    # params_dict = request.json
    mobile = params_dict.get("mobile")
    image_code = params_dict.get("image_code")
    image_code_id = params_dict.get("image_code_id")
    # 2.校验参数(参数是否符合规则,判断是否有值)
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if not re.match("1[35678]\\d{9}", mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="手机号格式错误")
    # 3.先从redis中取出验证码文本内容
    try:
        real_image_code = redis_store.get("ImageCodeId_" + image_code_id)
    except Exception as error:
        current_app.logger.error(error)
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")
    if not real_image_code:
        return jsonify(errno=RET.NODATA, errmsg="图片验证码已过期")
    # 4.与用户的验证码内容进行对比,如果对比不一致,那么返回验证码输入错误
    if real_image_code.upper() != image_code.upper():
        return jsonify(errno=RET.DATAERR, errmsg="验证码输入错误")
    # 5.如果一致,生成6位验证码的内容(随机值)
    sms_code_str = "%06d" % random.randint(0, 999999)
    # 6.发送短信验证码
    current_app.logger.debug("短信验证码的内容是:%s" % sms_code_str)
    # result = CCP().send_template_sms(mobile, [sms_code_str, constants.SMS_CODE_REDIS_EXPIRES / 5], "1")
    # if result != 0:
    #     return jsonify(errno=RET.THIRDERR, errmsg="发送短信失败")
    # 7.保存到验证码内容到redis数据库
    try:
        redis_store.set("SMS_" + mobile, sms_code_str, constants.SMS_CODE_REDIS_EXPIRES)
    except Exception as error:
        current_app.logger.error(error)
        return jsonify(errno=RET.DBERR, errmsg="数据保存失败")
    # 8.告知发送结束
    return jsonify(errno=RET.OK, errmsg="发送成功!")


@passport_blu.route("/image_code")
def get_image_code():
    """生成图片验证码并返回"""
    # 1.取出参数
    image_code_id = request.args.get("imageCodeId", None)
    # 2.判断参数是否有值
    if not image_code_id:
        return abort(403)
    # 3.生成图片验证码
    name, text, image = captcha.generate_captcha()
    current_app.logger.debug("图片验证码内容是:%s" % text)
    # 4.保存图片验证码文字内容到redis
    try:
        redis_store.set("ImageCodeId_" + image_code_id, text, constants.IMAGE_CODE_REDIS_EXPIRES)
    except Exception as error:
        current_app.logger.debug(error)
        abort(500)
    # 5.返回图片验证码
    response = make_response(image)
    # 设置浏览器headers中的格式
    response.headers["Content-Type"] = "image/jpg"
    return response
