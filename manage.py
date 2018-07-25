"""程序入口，启动文件"""

from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from info import create_app, db, models

# 通过传入的参数名指定配置的不同模式
from info.models import User

app = create_app("development")
manager = Manager(app)
# 将app与db关联
Migrate(app, db)
# 设置迁移命令添加到manager中
manager.add_command("db", MigrateCommand)


# "-n"为键，"-name"为值；把dest取到指定的值"name"传递给函数形参name
# python3 manage.py createsuperuser -n admin -p 12345678
@manager.option("-n", "-name", dest="name")
@manager.option("-p", "-password", dest="password")
def createsuperuser(name, password):
    """创建管理员账户"""
    if not all([name, password]):
        print("参数不足")

    user = User()
    user.nick_name = name
    user.mobile = name
    user.password = password
    # 表示权限是管理员账户
    user.is_admin = True  # True值为1，False值为0

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(e)

    print("添加成功")


if __name__ == '__main__':
    manager.run()
