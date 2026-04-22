# -*- coding: utf-8 -*-
from app import create_app
from app.models import Student, Room
from datetime import date, timedelta
from sqlalchemy import or_

app = create_app()
with app.app_context():
    # 时间范围
    start_date = date(2026, 1, 1)
    end_date = date(2026, 3, 31)
    
    # 查询东欧与中亚业务部的所有学生
    students = Student.query.filter(
        Student.department == '东欧与中亚业务部',
        or_(
            Student.room_id.isnot(None),
            Student.archived_room_id.isnot(None)
        )
    ).all()
    
    print(f"=== 东欧与中亚业务部学生列表 ===")
    print(f"时间范围: {start_date} 至 {end_date}")
    print(f"找到 {len(students)} 名学生\n")
    
    for s in students:
        room_id = s.room_id or s.archived_room_id
        room = Room.query.get(room_id) if room_id else None
        room_str = f"{room.building}-{room.room_number}" if room else "无房间"
        deleted_str = s.deleted_at.date() if s.deleted_at else "无"
        print(f"ID:{s.id} 姓名:{s.name} 部门:{s.department}")
        print(f"  房间:{room_str} 入住:{s.check_in_date} 预计离开:{s.check_out_date}")
        print(f"  状态:{s.status} deleted_at:{deleted_str}")
        print()
