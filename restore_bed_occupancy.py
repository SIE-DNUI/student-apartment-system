"""
恢复脚本：修复 fix_all_rooms.py 造成的数据破坏
问题：fix_all_rooms.py 错误地将63名选择单人间（bed_occupancy=2）的学生改为 bed_occupancy=1
本脚本：将这些学生的 bed_occupancy 恢复为 2，并重新计算所有房间的 current_occupancy
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, Student, Room

app = create_app()

with app.app_context():
    print("=" * 80)
    print("🔄 开始恢复被 fix_all_rooms.py 破坏的数据")
    print("=" * 80)
    
    # ===== 第一步：恢复 bed_occupancy =====
    # 查找所有"只有1个学生、且该学生 bed_occupancy=1"的房间
    # 这些学生的 bed_occupancy 被脚本从 2 错误改成了 1，需要恢复为 2
    
    # 先统计哪些房间只有1个学生
    from sqlalchemy import func
    
    rooms_with_one_student = db.session.query(
        Room.id, Room.building, Room.room_number
    ).join(
        Student, Student.room_id == Room.id
    ).group_by(
        Room.id, Room.building, Room.room_number
    ).having(
        func.count(Student.id) == 1
    ).all()
    
    print(f"\n📋 只有1个学生的房间：{len(rooms_with_one_student)} 个")
    
    # 在这些房间中，找到 bed_occupancy=1 的学生（被脚本改过的）
    room_ids_one_student = [r[0] for r in rooms_with_one_student]
    
    affected_students = Student.query.filter(
        Student.room_id.in_(room_ids_one_student),
        Student.bed_occupancy == 1
    ).all()
    
    print(f"⚠️  需要恢复的学生：{len(affected_students)} 名")
    print(f"   （bed_occupancy 从 1 恢复为 2）\n")
    
    if len(affected_students) == 0:
        print("✅ 没有需要恢复的学生，数据可能已经正确")
        sys.exit(0)
    
    # 列出将被恢复的学生
    for s in affected_students:
        room = Room.query.get(s.room_id)
        print(f"  🔄 {s.name} (ID:{s.id}) | 房间: {room.building}-{room.room_number} | bed_occupancy: 1 → 2")
    
    print(f"\n确认恢复以上 {len(affected_students)} 名学生？(y/n): ", end="")
    confirm = input().strip().lower()
    
    if confirm != 'y':
        print("❌ 已取消")
        sys.exit(0)
    
    # 执行恢复
    for s in affected_students:
        s.bed_occupancy = 2
    
    print(f"\n✅ 已恢复 {len(affected_students)} 名学生的 bed_occupancy 为 2")
    
    # ===== 第二步：重新计算所有房间的 current_occupancy =====
    print(f"\n📊 重新计算所有房间的 current_occupancy...")
    
    rooms = Room.query.all()
    updated_count = 0
    
    for room in rooms:
        students = Student.query.filter_by(room_id=room.id).all()
        correct_occupancy = sum(s.bed_occupancy for s in students)
        
        if room.current_occupancy != correct_occupancy:
            print(f"  🏠 {room.building}-{room.room_number}: current_occupancy {room.current_occupancy} → {correct_occupancy}")
            room.current_occupancy = correct_occupancy
            updated_count += 1
    
    if updated_count == 0:
        print("  ✅ 所有房间的 current_occupancy 已正确")
    else:
        print(f"\n✅ 已更新 {updated_count} 个房间的 current_occupancy")
    
    # ===== 提交 =====
    db.session.commit()
    
    # ===== 验证 =====
    print(f"\n{'=' * 80}")
    print("🔍 验证结果")
    print("=" * 80)
    
    total_students = Student.query.filter(Student.room_id.isnot(None)).count()
    total_rooms = Room.query.filter(Room.id.in_(
        db.session.query(Student.room_id).distinct()
    )).count()
    
    print(f"  总学生数（有房间的）：{total_students}")
    print(f"  总房间数（有学生的）：{total_rooms}")
    
    # 检查有没有 occupied_beds > capacity 的异常房间
    problem_rooms = []
    for room in Room.query.all():
        students = Student.query.filter_by(room_id=room.id).all()
        occupied = sum(s.bed_occupancy for s in students)
        if occupied > room.capacity:
            problem_rooms.append((room, occupied))
    
    if problem_rooms:
        print(f"\n⚠️  发现 {len(problem_rooms)} 个超员房间：")
        for room, occ in problem_rooms:
            print(f"  {room.building}-{room.room_number}: 占用{occ}床 / 容量{room.capacity}床")
    else:
        print(f"\n✅ 没有超员房间，数据正常")
    
    print(f"\n{'=' * 80}")
    print("✅ 恢复完成！请在系统中检查确认")
    print("=" * 80)
