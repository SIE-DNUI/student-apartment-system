# -*- coding: utf-8 -*-
"""
成本与回款计算工具
"""
from datetime import datetime, date, timedelta
from calendar import monthrange
from sqlalchemy import or_
import pytz
from app.models import db, Student, FeeRecord, MonthlyRent

# 四个业务部门
DEPARTMENTS = [
    "东欧与中亚业务部",
    "日本业务部",
    "业务发展部",
    "国教平台"
]


def get_current_time_info():
    """获取当前时间信息（使用Asia/Shanghai时区）"""
    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(tz)
    current_year = now.year
    current_month = now.month
    
    # 判断是否是12月
    is_december = current_month == 12
    
    # 如果是12月，需要计算到12月31日的统计
    if is_december:
        # 上月末是11月30日
        last_month_end = date(current_year, 11, 30) if current_month == 12 else None
    else:
        # 计算上月末
        if current_month == 1:
            last_month_end = date(current_year - 1, 12, 31)
        else:
            _, last_day = monthrange(current_year, current_month - 1)
            last_month_end = date(current_year, current_month - 1, last_day)
    
    return {
        'current_year': current_year,
        'current_month': current_month,
        'is_december': is_december,
        'last_month_end': last_month_end
    }


def get_year_start():
    """获取今年1月1日"""
    time_info = get_current_time_info()
    return date(time_info['current_year'], 1, 1)


def get_last_month_end():
    """获取上月末日期"""
    time_info = get_current_time_info()
    return time_info['last_month_end']


def get_previous_month():
    """获取上一个月的信息"""
    time_info = get_current_time_info()
    if time_info['current_month'] == 1:
        return time_info['current_year'] - 1, 12
    return time_info['current_year'], time_info['current_month'] - 1


def get_last_month_rent():
    """获取上月房租（手动录入的值）"""
    year, month = get_previous_month()
    rent = MonthlyRent.query.filter_by(year=year, month=month).first()
    return rent.amount if rent else 0.0


def get_year_total_rent():
    """获取截至上月末今年总房租（累计今年各月房租）"""
    time_info = get_current_time_info()
    current_year = time_info['current_year']
    
    # 计算从今年1月到上个月的所有房租
    end_month = time_info['current_month'] - 1 if not time_info['is_december'] else time_info['current_month']
    
    rents = MonthlyRent.query.filter(
        MonthlyRent.year == current_year,
        MonthlyRent.month <= end_month
    ).all()
    
    return sum(rent.amount for rent in rents)


def get_last_month_payment():
    """获取上月住宿费回款（统计上一个月录入的缴费总额）"""
    year, month = get_previous_month()
    first_day = date(year, month, 1)
    _, last_day = monthrange(year, month)
    last_day_date = date(year, month, last_day)
    
    # 如果是12月，还需要额外统计12月当月的数据
    time_info = get_current_time_info()
    if time_info['is_december'] and month == 12:
        # 12月额外统计当月数据 - 但由于我们查询的是上月数据，12月的上月是11月
        pass
    
    # 查询上月的缴费记录
    payments = FeeRecord.query.filter(
        FeeRecord.payment_date >= first_day,
        FeeRecord.payment_date <= last_day_date
    ).all()
    
    return sum(payment.amount for payment in payments)


def get_year_total_payment():
    """获取截至上月末今年住宿费总回款"""
    time_info = get_current_time_info()
    current_year = time_info['current_year']
    last_month_end = time_info['last_month_end']
    
    year_start = date(current_year, 1, 1)
    
    # 如果是12月，统计到12月31日
    if time_info['is_december']:
        last_month_end = date(current_year, 12, 31)
    
    payments = FeeRecord.query.filter(
        FeeRecord.payment_date >= year_start,
        FeeRecord.payment_date <= last_month_end
    ).all()
    
    return sum(payment.amount for payment in payments)


def calculate_room_usage_days(student, start_date, end_date):
    """计算单个学生在指定时间范围内的房间使用天数
    
    Args:
        student: 学生对象
        start_date: 开始日期（今年1月1日）
        end_date: 结束日期（上月末）
    
    Returns:
        使用的天数
    """
    # 获取实际房间ID（优先使用 room_id，若为空则使用 archived_room_id）
    actual_room_id = student.room_id or student.archived_room_id
    if not actual_room_id:
        return 0
    
    # 获取学生的实际入住时间范围
    # 入住日期不能早于开始日期
    if student.check_in_date:
        actual_start = max(start_date, student.check_in_date)
    else:
        actual_start = start_date
    
    # 离开日期不能晚于结束日期
    # 对于归档学生或已退房学生，使用 deleted_at 作为实际退房日期
    # 否则使用预计离开日期(check_out_date)，如果没有则使用结束日期
    if student.status in ('checked_out', 'archived') and student.deleted_at:
        # 归档或退房学生：使用实际退房日期
        actual_end = min(end_date, student.deleted_at.date())
    elif student.check_out_date:
        # 在住学生：使用预计离开日期
        actual_end = min(end_date, student.check_out_date)
    else:
        actual_end = end_date
    
    # 如果开始日期晚于结束日期，返回0
    if actual_start > actual_end:
        return 0
    
    # 计算天数（包含首尾两天）
    return (actual_end - actual_start).days + 1


def get_department_room_usage_days(department, start_date, end_date):
    """获取某部门在指定时间范围内的房间使用总天数
    
    注意：
    1. 双人间同一时间段只计算一次，不重复计算
    2. 同一房间不同时间段的占用应该累加
    3. 归档学生也要统计在内，只要在时间范围内占用过房间
    """
    # 查询所有学生（包括归档学生），只要在该时间范围内占用过房间
    students = Student.query.filter(
        Student.department == department,
        or_(
            Student.room_id.isnot(None),
            Student.archived_room_id.isnot(None)
        )
    ).all()
    
    # 按房间分组，收集每个房间的所有入住时间段
    room_periods = {}  # {room_id: [(start, end), ...]}
    
    for student in students:
        # 获取实际房间ID
        actual_room_id = student.room_id or student.archived_room_id
        if not actual_room_id:
            continue
        
        # 计算该学生的入住时间段
        if student.check_in_date:
            period_start = max(start_date, student.check_in_date)
        else:
            period_start = start_date
        
        # 确定结束日期
        if student.status in ('checked_out', 'archived') and student.deleted_at:
            period_end = min(end_date, student.deleted_at.date())
        elif student.check_out_date:
            period_end = min(end_date, student.check_out_date)
        else:
            period_end = end_date
        
        # 如果时间段有效，添加到对应房间
        if period_start <= period_end:
            if actual_room_id not in room_periods:
                room_periods[actual_room_id] = []
            room_periods[actual_room_id].append((period_start, period_end))
    
    # 计算每个房间的总占用天数（合并重叠时间段）
    total_days = 0
    for room_id, periods in room_periods.items():
        # 按开始日期排序
        periods.sort(key=lambda x: x[0])
        
        # 合并重叠的时间段
        merged = []
        for start, end in periods:
            if merged and start <= merged[-1][1] + timedelta(days=1):
                # 与前一个时间段重叠或连续，合并
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        
        # 计算合并后的总天数
        for start, end in merged:
            total_days += (end - start).days + 1
    
    return total_days


def get_total_room_usage_days(start_date, end_date):
    """获取四个部门房间使用总天数之和"""
    total = 0
    for dept in DEPARTMENTS:
        total += get_department_room_usage_days(dept, start_date, end_date)
    return total


def get_department_rent_cost(department, total_rent, start_date, end_date):
    """计算某部门的分摊房租成本
    
    公式：截至上月末今年总房租 / 四个部门占用房间的总天数之和 * 某部门房间使用总天数
    """
    dept_days = get_department_room_usage_days(department, start_date, end_date)
    total_days = get_total_room_usage_days(start_date, end_date)
    
    if total_days == 0:
        return 0.0
    
    return (total_rent / total_days) * dept_days


def get_department_payment(department, start_date, end_date):
    """获取某部门的住宿费回款
    
    注意：归档学生的缴费记录也要统计在内
    """
    # 找到该部门的所有学生（包括归档学生）
    students = Student.query.filter(
        Student.department == department
    ).all()
    
    student_ids = [s.id for s in students]
    
    if not student_ids:
        return 0.0
    
    # 查找这些学生的缴费记录
    payments = FeeRecord.query.filter(
        FeeRecord.student_id.in_(student_ids),
        FeeRecord.payment_date >= start_date,
        FeeRecord.payment_date <= end_date
    ).all()
    
    return sum(payment.amount for payment in payments)


def get_department_profit(department, total_rent, start_date, end_date):
    """计算某部门的盈利情况
    
    公式：各部门截至上月末分摊房租成本 - 各部门截至上月末住宿费回款额
    注意：盈利为负表示亏损
    """
    rent_cost = get_department_rent_cost(department, total_rent, start_date, end_date)
    payment = get_department_payment(department, start_date, end_date)
    
    return payment - rent_cost


def get_all_department_stats():
    """获取所有部门的统计数据"""
    time_info = get_current_time_info()
    current_year = time_info['current_year']
    
    # 如果是12月，计算到12月31日
    if time_info['is_december']:
        end_date = date(current_year, 12, 31)
    else:
        end_date = time_info['last_month_end']
    
    start_date = date(current_year, 1, 1)
    year_total_rent = get_year_total_rent()
    
    stats = []
    for dept in DEPARTMENTS:
        room_days = get_department_room_usage_days(dept, start_date, end_date)
        rent_cost = get_department_rent_cost(dept, year_total_rent, start_date, end_date)
        payment = get_department_payment(dept, start_date, end_date)
        profit = payment - rent_cost
        
        stats.append({
            'department': dept,
            'room_days': room_days,
            'rent_cost': rent_cost,
            'payment': payment,
            'profit': profit
        })
    
    return stats


def get_summary_data():
    """获取四个统计指标"""
    return {
        'last_month_rent': get_last_month_rent(),
        'year_total_rent': get_year_total_rent(),
        'last_month_payment': get_last_month_payment(),
        'year_total_payment': get_year_total_payment()
    }
