from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


from app.services.config_manager import ConfigManager
from app.services.token_manager import TokenManager
from app.models.base import Base



def create_db(url: str= 'sqlite:///data/data.db'):
    engine = create_engine(url=url, echo=True, future=True)
    # 定义一个基于线程的Session: https://docs.sqlalchemy.org/en/20/orm/contextual.html
    # scoped_session内部使用线程局部变量对每个线程维护一个独立的Session对象. 通常将scoped_session的返回值视为一个函数, 通过函数调用获得内部维护的属于当前线程的Session对象
    # 但scoped_session的返回值本身也进行了代理操作, 可以直接视为一个Session对象
    # TODO: 分析一下这两个auto功能的效果
    return scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))



# 初始化数据库对象
engine = create_engine(url='sqlite:///data/data.db', echo=True, future=True)
db = create_db()

config_manager = ConfigManager() 
token_manager = TokenManager()

# 初始化所有的表
Base.metadata.create_all(engine)

def create_app():
    # 创建Flask应用实例
    app = Flask(__name__)
    # 加载配置
    # app.config.from_object(Config)

    # 初始化数据库
    # db.init_app(app)

    # 导入并注册蓝图
    from app.views.file import file_bp
    from app.views.item import item_bp
    from app.views.login import login_bp
    from app.views.meta import meta_bp
    from app.views.note import note_bp
    from app.views.tomato import tomato_bp
    app.register_blueprint(file_bp)
    app.register_blueprint(item_bp)
    app.register_blueprint(login_bp)
    app.register_blueprint(meta_bp)
    app.register_blueprint(note_bp)
    app.register_blueprint(tomato_bp)

    return app