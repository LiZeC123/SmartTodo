from app import create_app, db
from app.tools.log import logger

app = create_app()

@app.teardown_appcontext
def remove_session(exception=None):
    if exception is None:
        db.commit()
    else:
        logger.exception(f"清理Session: 此Session中存在异常 {exception}")
    # remove操作默认回滚, 如果之前未进行commit, 则本次会话所有操作均回滚
    db.remove()



if __name__ == '__main__':
        # init_task_manager()
    app.run("localhost", 4231, threaded=True)
