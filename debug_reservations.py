#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试脚本：检查入住计划数据"""
import sys
sys.path.insert(0, '/home/SIEDNUI/student-apartment-system')

from app import create_app
from app.models import db, Reservation, Room
from datetime import date
from calendar import monthrange

app = create_app()
with app.app_context():
    print("=" * 60)
    print("【入住计划数据检查】")
    print("=" * 60)
    
    # 1. 检查总房间数
    total_rooms = Room.query.count()
    print(f"\n总房间数: {total_rooms}")
    
    # 2. 检查所有入住计划
    all_res = Reservation.query.filter(Reservation.status != 'cancelled').all()
    print(f"\n有效入住计划总数: {len(all_res)}")
    
    # 3. 按月份显示
    print("\n【按入住月份统计】")
    monthly = {}
    for r in all_res:
        if r.check_in_date:
            key = r.check_in_date.strftime('%Y-%m')
            if key not in monthly:
                monthly[key] = []
            monthly[key].append(r)
    
    for month_key in sorted(monthly.keys()):
        plans = monthly[month_key]
        total_rooms_needed = sum(r.rooms_needed for r in plans)
        print(f"  {month_key}: {len(plans)}个计划, 共{total_rooms_needed}间房")
        for r in plans:
            print(f"    - {r.group_name or r.student_name}: {r.check_in_date} ~ {r.check_out_date or '未定'}, {r.rooms_needed}间, 状态:{r.status}")
    
    # 4. 检查6月份日历数据
    print("\n【6月份日历检查】")
    year, month = 2026, 6
    _, days_in_month = monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, days_in_month)
    
    # 查询6月份的入住计划
    june_res = Reservation.query.filter(
        Reservation.check_in_date <= month_end,
        db.or_(
            Reservation.check_out_date >= month_start,
            Reservation.check_out_date == None
        ),
        Reservation.status != 'cancelled'
    ).all()
    
    print(f"查询条件: check_in <= {month_end}, (check_out >= {month_start} OR check_out IS NULL)")
    print(f"查询结果: {len(june_res)}个计划")
    for r in june_res:
        print(f"  - {r.group_name or r.student_name}: {r.check_in_date} ~ {r.check_out_date or '未定'}, {r.rooms_needed}间")
    
    # 5. 检查6月1日的占用
    print("\n【6月1日占用检查】")
    test_date = date(2026, 6, 1)
    occupied = 0
    for r in june_res:
        if r.check_in_date <= test_date:
            if r.check_out_date is None or r.check_out_date > test_date:
                occupied += r.rooms_needed
                print(f"  有效: {r.group_name or r.student_name}, 占用{r.rooms_needed}间")
    print(f"6月1日总占用: {occupied}间房")
    
    print("\n" + "=" * 60)
