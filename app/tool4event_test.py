# from entity import init_database
# from tool4event import EventManager
#
# db = init_database('sqlite://')
# owner = "user"
#
# def test_base():
#     m = EventManager(db)
#     m.add_event("Test Content", owner)
#     items = m.get_today_event(owner)
#     assert len(items) == 1