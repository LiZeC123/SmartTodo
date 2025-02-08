# from tool4time import this_week_begin
# from entity import init_database
# from tool4report import *
#
# db_session = init_database('sqlite://')
#
# manager = ReportManager(db_session)
# owner = "user"
#
# def test_summary_base():
#     # 初始查询今日总结为空
#     assert manager.get_today_summary(owner) == ""
#
#     assert manager.update_summary("Hello", owner)
#
#     assert manager.get_today_summary(owner) == "Hello"
#
#     assert manager.update_summary("Hello World", owner)
#
#     assert manager.get_today_summary(owner) == "Hello World"
#
#     assert manager.get_summary_from(this_week_begin())