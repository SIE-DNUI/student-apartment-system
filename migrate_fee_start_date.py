"""
数据库迁移脚本：新增 fee_start_date 字段，并初始化数据
在 PythonAnywhere 的 Bash console 里运行：python migrate_fee_start_date.py
"""
from app import create_app
from app.models import db, Student
from datetime import date

app = create_app()

with app.app_context():
    # 1. 给数据库表新增 fee_start_date 列（如果不存在）
    try:
        db.engine.execute("ALTER TABLE students ADD COLUMN fee_start_date DATE")
        print("✅ 已新增 fee_start_date 列")
    except Exception as e:
        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
            print("⏭️  fee_start_date 列已存在，跳过创建")
        else:
            print(f"❌ 新增列失败：{e}")
            raise
    
    # 2. 给所有 fee_start_date 为空的学生，设置为 check_in_date
    students_updated = 0
    students = Student.query.filter(Student.fee_start_date.is_(None), Student.check_in_date.isnot(None)).all()
    for s in students:
        s.fee_start_date = s.check_in_date
        students_updated += 1
    
    db.session.commit()
    print(f"✅ 已为 {students_updated} 个学生初始化 fee_start_date = check_in_date")
    
    # 3. 修复 SHIRIAEVA OLESIA 的数据（换房日期 2026-09-01，fee_start_date 应为 2026-09-02）
    olesia = Student.query.filter(Student.name.like('%SHIRIAEVA%')).first()
    if olesia:
        olesia.fee_start_date = date(2026, 9, 2)
        db.session.commit()
        print(f"✅ 已修复 SHIRIAEVA OLESIA 的 fee_start_date = 2026-09-02")
        print(f"   当前状态：收费标准={olesia.fee_standard.name}, total_paid={olesia.total_paid}, 到期日={olesia.payment_due_date}")
        print(f"   fee_start_date={olesia.fee_start_date}")
    else:
        print("⚠️  未找到 SHIRIAEVA OLESIA，跳过修复")
    
    # 4. 验证
    print("\n" + "=" * 60)
    print("验证结果：")
    all_students = Student.query.filter(Student.status != 'archived').order_by(Student.name).all()
    null_count = sum(1 for s in all_students if s.fee_start_date is None)
    print(f"  在住学生总数：{len(all_students)}")
    print(f"  fee_start_date 为空的数量：{null_count}")
    if null_count == 0:
        print("  ✅ 所有在住学生都有 fee_start_date")
    else:
        print("  ⚠️  仍有学生缺少 fee_start_date")
    print("=" * 60)
