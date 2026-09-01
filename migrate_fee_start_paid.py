"""
迁移脚本：新增 fee_start_paid 字段，并初始化数据
fee_start_paid = 当前收费标准下的期初已缴金额（total_paid 中可用于当前标准的金额）

在 PythonAnywhere 的 Bash console 里运行：python migrate_fee_start_paid.py
"""
from app import create_app
from app.models import db, Student, FeeStandard
from datetime import date

app = create_app()

with app.app_context():
    # 1. 新增 fee_start_paid 列
    try:
        db.session.execute(db.text("ALTER TABLE students ADD COLUMN fee_start_paid FLOAT DEFAULT 0"))
        print("✅ 已新增 fee_start_paid 列")
    except Exception as e:
        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
            print("⏭️  fee_start_paid 列已存在，跳过创建")
        else:
            print(f"❌ 新增列失败：{e}")
            raise
    
    # 2. 默认初始化：所有 fee_start_paid 为空的学生，设为 total_paid
    # （未换房的学生，fee_start_paid = total_paid）
    students_updated = 0
    students = Student.query.filter(
        Student.fee_start_paid.is_(None),
        Student.fee_start_date.isnot(None)
    ).all()
    for s in students:
        s.fee_start_paid = s.total_paid or 0
        students_updated += 1
    db.session.commit()
    print(f"✅ 已为 {students_updated} 个学生初始化 fee_start_paid = total_paid")
    
    # 3. 修复 SHIRIAEVA OLESIA 的数据
    # 情况：第一学年住双人间(6000/年)，已消费6000，剩余0
    # 换到单人间后，fee_start_paid 应为 0
    olesia = Student.query.filter(Student.name.like('%SHIRIAEVA%')).first()
    if olesia:
        olesia.fee_start_paid = 0  # 第一学年6000已全部消费，无剩余
        db.session.commit()
        print(f"\n✅ 修复 SHIRIAEVA OLESIA (ID:{olesia.id})")
        print(f"   fee_start_paid = 0（第一学年已消费6000，无剩余）")
        print(f"   total_paid = {olesia.total_paid}")
        print(f"   fee_start_date = {olesia.fee_start_date}")
        arrears = olesia.calculate_arrears()
        auto_due = olesia.calculate_auto_due_date()
        print(f"   欠费 = {arrears}")
        print(f"   自动到期日 = {auto_due}")
    else:
        print("⚠️  未找到 SHIRIAEVA OLESIA")
    
    # 4. 修复 MYTSYK ALEKSANDRA 的数据
    # 情况：第一学年住双人间(6000/年)，已消费6000，剩余12000
    # 换到单人间后，fee_start_paid 应为 12000
    mytsyk = Student.query.filter(Student.name.like('%MYTSYK%')).first()
    if mytsyk:
        mytsyk.fee_start_paid = 12000  # 第一学年消费6000，剩余12000
        db.session.commit()
        print(f"\n✅ 修复 MYTSYK ALEKSANDRA (ID:{mytsyk.id})")
        print(f"   fee_start_paid = 12000（第一学年已消费6000，剩余12000）")
        print(f"   total_paid = {mytsyk.total_paid}")
        print(f"   fee_start_date = {mytsyk.fee_start_date}")
        arrears = mytsyk.calculate_arrears()
        auto_due = mytsyk.calculate_auto_due_date()
        print(f"   欠费 = {arrears}")
        print(f"   自动到期日 = {auto_due}")
    else:
        print("⚠️  未找到 MYTSYK ALEKSANDRA")
    
    # 5. 验证
    print("\n" + "=" * 60)
    print("验证结果：")
    all_students = Student.query.filter(Student.status != 'archived').order_by(Student.name).all()
    null_count = sum(1 for s in all_students if s.fee_start_paid is None)
    print(f"  在住学生总数：{len(all_students)}")
    print(f"  fee_start_paid 为空的数量：{null_count}")
    if null_count == 0:
        print("  ✅ 所有在住学生都有 fee_start_paid")
    else:
        print("  ⚠️  仍有学生缺少 fee_start_paid")
    
    # 检查欠费学生
    arrears_list = [s for s in all_students if s.has_arrears()]
    if arrears_list:
        print(f"\n  当前欠费学生（{len(arrears_list)}人）：")
        for s in arrears_list:
            print(f"    {s.name}: 欠费 ¥{s.calculate_arrears():.2f}")
    else:
        print("\n  ✅ 无欠费学生")
    print("=" * 60)
