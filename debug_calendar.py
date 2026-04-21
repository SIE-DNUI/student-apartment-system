#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试脚本：检查房间日历计算"""
import sys
sys.path.insert(0, '/home/SIEDNUI/student-apartment-system')

from app import create_app
from app.models import db, Reservation, Room, Student
from datetime import date, timedelta
from calendar import monthrange

app = create_app()
with app.app_context():
    print("=" * 60)
    print("【房间日历调试 - 2026年4月】")
    print("=" * 60)
    
    # 1. 总房间数
    total_rooms = Room.query.count()
    print(f"\n总房间数: {total_rooms}")
    
    # 2. 当前实际入住学生数
    active_students = Student.query.filter(
        Student.status == 'active',
        Student.room_id != None
    ).all()
    
    room_students = {}
    for s in active_students:
        if s.room_id:
            if s.room_id not in room_students:
                room_students[s.room_id] = []
            room_students[s.room_id].append(s)
    
    # 当前占用房间数
    current_occupied = 0
    for room_id, students in room_students.items():
        has_active = any(
            s.check_in_date <= date.today() and (s.check_out_date is None or s.check_out_date > date.today())
            for s in students
        )
        if has_active:
            current_occupied += 1
    
    print(f"当前实际入住学生数: {len(active_students)}")
    print(f"当前占用房间数: {current_occupied}")
    print(f"当前剩余房间数: {total_rooms - current_occupied}")
    
    # 3. 4月份的入住计划
    year, month = 2026, 4
    _, days_in_month = monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, days_in_month)
    
    print(f"\n4月时间范围: {month_start} ~ {month_end}")
    
    # 查询入住计划
    reservations = Reservation.query.filter(
        Reservation.check_in_date <= month_end,
        db.or_(
            Reservation.check_out_date >= month_start,
            Reservation.check_out_date == None
        ),
        Reservation.status != 'cancelled'
    ).all()
    
    print(f"\n4月份入住计划查询结果: {len(reservations)}个")
    for r in reservations:
        print(f"  - ID:{r.id}, {r.group_name or r.student_name}: {r.check_in_date} ~ {r.check_out_date or '未定'}, {r.rooms_needed}间, 状态:{r.status}")
    
    # 4. 检查4月23日的数据
    test_date = date(2026, 4, 23)
    print(f"\n【4月23日详细检查】")
    
    # 计算入住计划占用
    plan_occupied = 0
    for r in reservations:
        if r.check_in_date <= test_date:
            if r.check_out_date is None or r.check_out_date > test_date:
                plan_occupied += r.rooms_needed
                print(f"  有效计划: {r.group_name or r.student_name}, 占用{r.rooms_needed}间")
    print(f"  计划占用房间总数: {plan_occupied}")
    
    # 计算学生占用
    student_occupied = 0
    for room_id, students in room_students.items():
        active_students_in_room = [
            s for s in students
            if s.check_in_date <= test_date and (s.check_out_date is None or s.check_out_date > test_date)
        ]
        if active_students_in_room:
            student_occupied += 1
            print(f"  房间{room_id}有学生: {[s.name for s in active_students_in_room]}")
    
    print(f"  学生占用房间总数: {student_occupied}")
    
    # 最终占用
    final_occupied = max(plan_occupied, student_occupied)
    print(f"\n  最终占用: max({plan_occupied}, {student_occupied}) = {final_occupied}")
    print(f"  剩余房间: {total_rooms} - {final_occupied} = {total_rooms - final_occupied}")
    
    print("\n" + "=" * 60)
