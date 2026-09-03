#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断脚本：显示所有房间和学生的当前状态
帮助用户确认哪些数据被错误修改
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, Room, Student

app = create_app()

with app.app_context():
    rooms = Room.query.order_by(Room.building, Room.room_number).all()
    
    print(f"📊 共有 {len(rooms)} 个房间")
    print("=" * 100)
    
    for room in rooms:
        active_students = Student.query.filter_by(room_id=room.id, status='active').all()
        
        if not active_students:
            continue
        
        # 计算占用床位数
        occupied_beds = sum(s.bed_occupancy for s in active_students)
        empty_beds = room.capacity - occupied_beds
        
        # 判断是否为单人间模式（bed_occupancy=2）
        is_single_mode = any(s.bed_occupancy == 2 for s in active_students)
        mode_str = "单人间" if is_single_mode else "双人间"
        
        print(f"\n🏠 {room.building}-{room.room_number} (容量: {room.capacity})")
        print(f"   当前模式: {mode_str}")
        print(f"   学生数: {len(active_students)}")
        print(f"   current_occupancy: {room.current_occupancy}")
        print(f"   占用床位: {occupied_beds}, 空床位: {empty_beds}")
        
        for s in active_students:
            print(f"   - {s.name}: bed_occupancy={s.bed_occupancy}")
