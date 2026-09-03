"""快速诊断：查看516房间和几个典型房间的数据库状态"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import create_app
from app.models import db, Student, Room

app = create_app()
with app.app_context():
    # 查看516房间
    room = Room.query.filter(Room.room_number == '516', Room.building == '19号楼').first()
    if not room:
        print("❌ 未找到19号楼516")
        sys.exit(1)
    
    students = Student.query.filter_by(room_id=room.id).all()
    active_students = [s for s in students if s.status == 'active']
    
    print(f"🏠 19号楼-516")
    print(f"   capacity: {room.capacity}")
    print(f"   current_occupancy: {room.current_occupancy}")
    print(f"   status: {room.status}")
    print(f"   学生总数: {len(students)}, active数: {len(active_students)}")
    for s in students:
        print(f"   - {s.name} (ID:{s.id}) | status={s.status} | bed_occupancy={s.bed_occupancy}")
    
    occupied_beds = sum(s.bed_occupancy for s in active_students)
    print(f"   计算 occupied_beds: {occupied_beds}")
    print(f"   计算 empty_beds: {room.capacity - occupied_beds}")
    
    # 再看几个典型房间
    print(f"\n{'='*60}")
    print("📋 其他典型房间抽查：")
    
    # 找有2个学生的房间
    from sqlalchemy import func
    rooms_2 = db.session.query(Room).join(Student).group_by(Room.id).having(func.count(Student.id)==2).limit(3).all()
    for r in rooms_2:
        ss = Student.query.filter_by(room_id=r.id).all()
        print(f"  {r.building}-{r.room_number}: current_occupancy={r.current_occupancy}, capacity={r.capacity}")
        for s in ss:
            print(f"    {s.name} | status={s.status} | bed_occupancy={s.bed_occupancy}")
    
    # 找有1个学生的房间（抽查5个）
    rooms_1 = db.session.query(Room).join(Student).group_by(Room.id).having(func.count(Student.id)==1).limit(5).all()
    print(f"\n  --- 单人住房间抽查 ---")
    for r in rooms_1:
        ss = Student.query.filter_by(room_id=r.id).all()
        print(f"  {r.building}-{r.room_number}: current_occupancy={r.current_occupancy}, capacity={r.capacity}")
        for s in ss:
            print(f"    {s.name} | status={s.status} | bed_occupancy={s.bed_occupancy}")
