#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
紧急恢复脚本：恢复被错误修改的数据
规则：capacity=2且只住1人的房间，恢复为单人间模式（bed_occupancy=2）
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, Room, Student

app = create_app()

with app.app_context():
    print("🚨 开始紧急恢复数据...")
    print("=" * 80)
    
    rooms = Room.query.all()
    fixed_count = 0
    
    for room in rooms:
        active_students = Student.query.filter_by(room_id=room.id, status='active').all()
        
        if not active_students:
            continue
        
        # 修复 current_occupancy
        correct_current_occupancy = len(active_students)
        if room.current_occupancy != correct_current_occupancy:
            print(f"🏠 {room.building}-{room.room_number}: current_occupancy {room.current_occupancy} → {correct_current_occupancy}")
            room.current_occupancy = correct_current_occupancy
        
        # 如果只住1人且capacity=2，恢复为单人间模式
        if len(active_students) == 1 and room.capacity == 2:
            student = active_students[0]
            if student.bed_occupancy != 2:
                print(f"   学生 {student.name}: bed_occupancy {student.bed_occupancy} → 2 (单人间)")
                student.bed_occupancy = 2
                fixed_count += 1
    
    db.session.commit()
    
    print("\n" + "=" * 80)
    print(f"✅ 已恢复 {fixed_count} 名学生的 bed_occupancy")
    print("✅ 请刷新页面验证")
