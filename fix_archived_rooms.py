#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复已归档学生的 archived_room_id

由于之前归档时 room_id 被清空，需要手动补充历史房间信息。
运行此脚本可以：
1. 查看哪些归档学生缺少 archived_room_id
2. 交互式地为他们设置房间
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, Student, Room
from datetime import date

app = create_app()

def show_archived_without_room():
    """显示缺少 archived_room_id 的归档学生"""
    with app.app_context():
        students = Student.query.filter(
            Student.status == 'archived',
            Student.archived_room_id.is_(None)
        ).order_by(Student.deleted_at.desc()).all()
        
        if not students:
            print("没有需要处理的归档学生")
            return []
        
        print(f"\n找到 {len(students)} 名缺少房间信息的归档学生：")
        print("-" * 80)
        print(f"{'ID':<6} {'姓名':<10} {'部门':<20} {'入住日期':<12} {'归档时间':<18}")
        print("-" * 80)
        
        for s in students:
            check_in = s.check_in_date.strftime('%Y-%m-%d') if s.check_in_date else '未知'
            deleted = s.deleted_at.strftime('%Y-%m-%d %H:%M') if s.deleted_at else '未知'
            print(f"{s.id:<6} {s.name:<10} {s.department or '未知':<20} {check_in:<12} {deleted:<18}")
        
        return students

def show_all_rooms():
    """显示所有房间"""
    with app.app_context():
        rooms = Room.query.order_by(Room.building, Room.room_number).all()
        print("\n所有房间列表：")
        print("-" * 40)
        for r in rooms:
            print(f"ID: {r.id:<4} {r.building}-{r.room_number}")
        print("-" * 40)

def set_archived_room(student_id, room_id):
    """设置归档学生的 archived_room_id"""
    with app.app_context():
        student = Student.query.get(student_id)
        if not student:
            print(f"错误：找不到学生ID {student_id}")
            return False
        
        if student.status != 'archived':
            print(f"错误：学生 {student.name} 不是归档状态")
            return False
        
        room = Room.query.get(room_id)
        if not room:
            print(f"错误：找不到房间ID {room_id}")
            return False
        
        student.archived_room_id = room_id
        db.session.commit()
        print(f"✓ 已设置 {student.name} 的归档房间为 {room.building}-{room.room_number}")
        return True

def batch_set_from_dict(room_dict):
    """批量设置归档学生的房间
    room_dict: {student_id: room_id, ...}
    """
    with app.app_context():
        success_count = 0
        for student_id, room_id in room_dict.items():
            student = Student.query.get(student_id)
            if student and student.status == 'archived':
                student.archived_room_id = room_id
                success_count += 1
        db.session.commit()
        print(f"✓ 批量设置了 {success_count} 名学生的归档房间")

if __name__ == '__main__':
    print("=" * 60)
    print("归档学生房间信息修复工具")
    print("=" * 60)
    
    while True:
        print("\n选项：")
        print("1. 查看缺少房间信息的归档学生")
        print("2. 查看所有房间")
        print("3. 设置单个学生的归档房间（格式: set 学生ID 房间ID）")
        print("4. 退出")
        
        cmd = input("\n请输入选项: ").strip()
        
        if cmd == '1':
            show_archived_without_room()
        elif cmd == '2':
            show_all_rooms()
        elif cmd.startswith('set '):
            try:
                parts = cmd.split()
                student_id = int(parts[1])
                room_id = int(parts[2])
                set_archived_room(student_id, room_id)
            except (IndexError, ValueError):
                print("格式错误，请使用: set 学生ID 房间ID")
        elif cmd == '4':
            print("退出")
            break
        else:
            print("无效选项")
