from typing import Sequence, Tuple

import sqlalchemy as sal
from sqlalchemy.orm import scoped_session, Session

from ..models.credit import Credit, CreditLog
from ..tools.time import now


Database = scoped_session[Session]

# 增加或减少积分
def update_credit(db: Database, owner: str, credit: int, reason: str):
    stmt = sal.select(Credit).with_for_update().where(Credit.owner == owner)
    account = db.execute(stmt).scalars().first()
    if account is None:
        account = Credit(owner=owner, credit=0)
        db.add(account)
    if account.credit >= 0 and account.credit + credit > 0:
        account.credit += credit
        log = CreditLog(owner=owner, create_time=now(), credit=credit, reason=reason, balance=account.credit)
        db.add(log)

    db.flush()


# 查询当前剩余积分
def query_credit(db: Database, owner: str) -> int:
    stmt = sal.select(Credit).where(Credit.owner == owner)
    account = db.execute(stmt).scalars().first()
    if account is None:
        return 0
    return account.credit

# 查询积分变动情况
def query_credit_week(db: Database, owner: str) -> Tuple[int, int]:
    return 0, 0

# 查询积分变动记录
def query_credit_list(db: Database, owner: str) -> Sequence[CreditLog]:
    stmt = sal.select(CreditLog).where(Credit.owner == owner).order_by(CreditLog.create_time.desc()).limit(15)
    return db.execute(stmt).scalars().all()






# 兑换项目管理
# 获取兑换项目列表
# 兑换项目
# 新增项目
# 项目价格计算
