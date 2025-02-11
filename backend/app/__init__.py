from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from app.services.config_manager import ConfigManager
from app.models.base import Base
from app.services.interpreter import OpInterpreter
from app.services.item_manager import ItemManager
from app.services.task_manager import TaskManager
from app.services.tomato_manager import TomatoManager, TomatoRecordManager
from app.tools.token import generate_token_str

# 初始化数据库对象
engine = create_engine(url='sqlite:///data/data.db', echo=True, future=True)

# 定义一个基于线程的Session: https://docs.sqlalchemy.org/en/20/orm/contextual.html
# scoped_session内部使用线程局部变量对每个线程维护一个独立的Session对象. 通常将scoped_session的返回值视为一个函数, 通过函数调用获得内部维护的属于当前线程的Session对象
# 但scoped_session的返回值本身也进行了代理操作, 可以直接视为一个Session对象
# autocommit: 是否在执行完操作后立即自动提交, 通常由于多个操作需要构成一个事务, 因此关闭自动提交
# autoflush: 是否在必要的时候执行自动刷新. 从文档看可以开, 不过现在保持关闭也可以
db = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

# 初始化Server层
config_manager = ConfigManager()
item_manager = ItemManager(db)
op_interpreter = OpInterpreter(item_manager)
tomato_manager = TomatoManager(db, item_manager)
tomato_record_manager = TomatoRecordManager(db, item_manager)

# 初始化定时任务
task_manager = TaskManager()
task_manager.add_daily_task("垃圾回收", item_manager.garbage_collection, "01:00")
task_manager.add_daily_task("重置可重复任务", item_manager.reset_daily_task, "01:10")
task_manager.add_daily_task("重置未完成的今日任务", item_manager.reset_today_task, "01:20")
task_manager.add_daily_task("重置已完成的周期性任务", item_manager.renew_sp_task, "01:30")


def create_app():
    # 创建Flask应用实例
    app = Flask(__name__)
    app.secret_key = generate_token_str()

    # 导入并注册蓝图
    from app.views.file import file_bp
    from app.views.item import item_bp
    from app.views.login import login_bp
    from app.views.meta import meta_bp
    from app.views.note import note_bp
    from app.views.tomato import tomato_bp
    from app.views.weight import weight_bp
    from app.views.credit import credit_bp
    app.register_blueprint(file_bp)
    app.register_blueprint(item_bp)
    app.register_blueprint(login_bp)
    app.register_blueprint(meta_bp)
    app.register_blueprint(note_bp)
    app.register_blueprint(tomato_bp)
    app.register_blueprint(weight_bp)
    app.register_blueprint(credit_bp)

    # 初始化所有的表
    Base.metadata.create_all(engine)

    # 启动定时任务
    task_manager.start()

    return app
