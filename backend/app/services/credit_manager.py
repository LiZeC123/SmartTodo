import math
from typing import Sequence, Tuple, List

import sqlalchemy as sal
from sqlalchemy.orm import scoped_session, Session

from ..models.credit import Credit, CreditLog, ExchangeItem, ExchangeLog
from ..tools.time import now, this_week_begin

Database = scoped_session[Session]

def update_credit(db: Database, owner: str, credit: int, reason: str) -> bool:
    """增加或减少积分"""
    stmt = sal.select(Credit).with_for_update().where(Credit.owner == owner)
    account = db.scalar(stmt)
    if account is None:
        account = Credit(owner=owner, credit=0)
        db.add(account)
    
    if account.credit >= 0 and account.credit + credit > 0:
        account.credit += credit
        log = CreditLog(owner=owner, create_time=now(), credit=credit, reason=reason, balance=account.credit)
        db.add(log)
        db.flush()
        return True
    
    return False


def query_credit(db: Database, owner: str) -> int:
    """查询当前剩余积分"""
    stmt = sal.select(Credit).where(Credit.owner == owner)
    account = db.scalar(stmt)
    if account is None:
        return 0
    return account.credit


def query_credit_week(db: Database, owner: str) -> Tuple[int, int]:
    """查询积分变动情况"""
    stmt = sal.select(CreditLog).where(CreditLog.owner == owner, CreditLog.create_time > this_week_begin())
    logs = db.scalars(stmt).all()
    earn = 0
    used = 0

    for log in logs:
        if log.credit > 0:
            earn += log.credit
        else:
            used += -log.credit

    return earn, used

def query_credit_list(db: Database, owner: str) -> List:
    """查询积分变动记录"""
    stmt = sal.select(CreditLog).where(CreditLog.owner == owner).order_by(CreditLog.create_time.desc()).limit(25)
    logs = db.execute(stmt).scalars().all()
    return [log.to_dict() for log in logs]


def query_exchange_item_list(db: Database, owner: str) -> List:
    stmt = sal.select(ExchangeItem)
    items = db.scalars(stmt).all()
    
    rst = []
    for item in items:
        rst.append({'id': item.id, 'name': item.name, 'points': update_price(db, item, owner)})
    return rst


def query_welfare_item_list(db: Database, owner: str) -> List:
    stmt = sal.select(ExchangeItem)
    items = db.scalars(stmt).all()
    
    rst = []
    for item in items:
        rst.append(item.to_dict())
    return rst


def exchange(db: Database, id: int, owner: str) -> str:
    stmt = sal.select(ExchangeItem).where(ExchangeItem.id == id)
    item = db.scalar(stmt)
    if item is None:
        return "兑换项目不存在"
    
    price = update_price(db, item, owner)
    ok = update_credit(db, owner, -price, f'兑换 {item.name}')
    if not ok:
        return "余额不足"
    
    add_echange_item_log(db, item, owner)
    return ""


def add_echange_item_log(db: Database, item: ExchangeItem, owner: str)-> bool:
    log = ExchangeLog(item_id=item.id, name=item.name, owner=owner)
    db.add(log)
    db.flush()
    return True


def add_exchange_item(db: Database, name: str, price:float, cycle: int, factor: float) -> bool:
    """添加项目, 注意进行权限检查, 仅管理员可操作"""
    item = ExchangeItem(name=name, price=price, cycle=cycle, factor=factor)
    db.add(item)
    db.flush()
    return True


def remove_exchange_item(db: Database, id: int) -> bool:
    """删除项目, 注意进行权限检查, 仅管理员可操作"""
    stmt = sal.select(ExchangeItem).where(ExchangeItem.id == id)
    item = db.scalar(stmt)
    if item:
        db.delete(item)
        return True
    return False



def update_price(db: Database, item: ExchangeItem, owner: str) -> int:
    """根据输入的Item项目和用户, 计算浮动价格"""
    stmt = sal.select(ExchangeLog).where(ExchangeLog.item_id == item.id, ExchangeLog.owner == owner).order_by(ExchangeLog.create_time.desc())
    log = db.scalar(stmt)
    if log is None:
        # 如果从未兑换, 则无浮动
        return math.ceil(item.price)
    
    delta_times = now() - log.create_time
    if delta_times.days > item.cycle:
        # 如果已经大于一个周期, 则无浮动
        return math.ceil(item.price)


    factor = (float(item.cycle - delta_times.days) / item.cycle) * item.factor
    return math.ceil(item.price * (1+factor ))