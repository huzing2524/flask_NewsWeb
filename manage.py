"""程序入口"""

from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from info import create_app, db, models

# 通过传入的参数名指定配置的不同模式
app = create_app("development")
manager = Manager(app)
# 将app与db关联
Migrate(app, db)
# 设置迁移命令添加到manager中
manager.add_command("db", MigrateCommand)

if __name__ == '__main__':
    manager.run()

