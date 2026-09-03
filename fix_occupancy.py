"""
修复所有房间的 current_occupancy
逻辑：current_occupancy = sum(该房间所有active学生的 bed_occupancy)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import create_app
from app.models import db, Student, Room

app = create_app()
with app.app_context():
    print("=" * 60)
    print("🔧 修复所有房间的 current_occupancy")
    print("=" * 60)
    
    rooms = Room.query.all()
    fixed = 0
    
    for room in rooms:
        active_students = Student.query.filter_by(room_id=room.id, status='active').all()
        correct_value = sum(s.bed_occupancy for s in active_students)
        
        if room.current_occupancy != correct_value:
            print(f"  🏠 {room.building}-{room.room_number}: current_occupancy {room.current_occupancy} → {correct_value}")
            room.current_occupancy = correct_value
            fixed += 1
    
    if fixed == 0:
        print("\n✅ 所有房间的 current_occupancy 已正确，无需修复")
    else:
        print(f"\n✅ 共修复 {fixed} 个房间")
        db.session.commit()
        print("✅ 已提交数据库")
    
    # 验证516
    room516 = Room.query.filter(Room.room_number == '516', Room.building == '19号楼').first()
    if room516:
        print(f"\n🔍 验证 19号楼-516:")
        print(f"   current_occupancy: {room516.current_occupancy}")
        print(f"   capacity: {room516.capacity}")
        print(f"   status: {room516.status}")
