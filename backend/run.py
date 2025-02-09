# @app.post('/api/summary/getReport')
# @authority_check()
# def get_summary_items(owner:str):
#     return tomato_record_manager.get_time_line_summary(owner)
# #
# # @app.post('/api/summary/getEventLine')
# # @authority_check()
# # def get_summary_event_line(owner:str):
# #     rst = event_manager.get_today_event(owner)
# #     return [i.to_dict() for i in rst]
# #
# #
# # @app.post('/api/summary/getNote')
# # @authority_check()
# # def get_summary_note(owner:str):
# #     return report_manager.get_today_summary(owner)
# #
# # @app.post('/api/summary/updateNode')
# # @authority_check()
# # def update_summary_note(owner:str):
# #     content = request.get_json().get("content")
# #     return report_manager.update_summary(content, owner)
# #
# # @app.get("/api/summary/getWeeklySummary")
# # @authority_check()
# # def get_report(owner:str):
# #     summarys = report_manager.get_summary_from(this_week_begin())
# #     return [s.to_dict() for s in summarys]

# @app.post('/api/summary/getSmartReport')
# @authority_check()
# def get_smart_analysis_report(owner:str):
#     return tomato_record_manager.get_smart_analysis_report(owner)




# TODO: Task

        



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
