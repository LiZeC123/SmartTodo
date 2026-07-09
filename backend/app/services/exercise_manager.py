from app.services.event_log_manager import EventManager
from app.tools.exercise import generate_rowing_workout


class ExerciseManager:
    def __init__(self, em: EventManager) -> None:
        self.db = em.db
        self.event_manager = em

    def add_record(self, exercise_type: str, time: int, extra: dict, owner: str) -> bool:
        msg = f"用户完成运动: {exercise_type}, 时长: {time / 60:.1} 分钟, 附加信息: {extra}"
        return self.event_manager.add_event_log(owner, msg)

    def plan_rowing(self, owner: str) -> dict:
        frequency, resistance = generate_rowing_workout()
        return {"frequency": frequency, "resistance": resistance}
