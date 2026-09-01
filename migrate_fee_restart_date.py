"""
数据库迁移脚本：将 fee_start_date 改名为 fee_restart_date，并修正数据语义
fee_restart_date = 换房/换收费标准后的新起算日期（未换过房则为空）
计算时：billing_start = fee_restart_date or check_in_date

在 PythonAnywhere 的 Bash console 里运行：python migrate_fee_restart_date.py
"""
from app import create_app
from app.models import db, Student
from datetime import date

app = create_app()

with app.app_context():
    # 1. 新增 fee_restart_date 列
    try:
        db.session.execute(db.text("ALTER TABLE students ADD COLUMN fee_restart_date DATE"))
        print("✅ 已新增 fee_restart_date 列")
    except Exception as e:
        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
            print("⏭️  fee_restart_date 列已存在，跳过创建")
        else:
            print(f"❌ 新增列失败：{e}")
            raise
    
    # 2. 给所有 fee_restart_date 为空的学生，默认设为 None（不设置值）
    # 大多数学生没有换过房，fee_restart_date 应该为空，计算时用 check_in_date
    print("\n✅ 大多数学生的 fee_restart_date 保持为空（未换过房）")
    
    # 3. 修复 SHIRIAEVA OLESIA 的数据（换房日期 2026-09-01，fee_restart_date 应为 2026-09-02）
    olesia = Student.query.filter(Student.name.like('%SHIRIAEVA%')).first()
    if olesia:
        olesia.fee_restart_date = date(2026, 9, 2)
        olesia.fee_start_paid = 6000  # 第一学年已消费6000（双人间6000/年，住满一年）
        db.session.commit()
        print(f"\n✅ 修复 SHIRIAEVA OLESIA (ID:{olesia.id})")
        print(f"   fee_restart_date = 2026-09-02（换房次日）")
        print(f"   fee_start_paid = 6000（第一学年已消费6000）")
        print(f"   total_paid = {olesia.total_paid}")
        print(f"   available = {olesia.total_paid - olesia.fee_start_paid}")
        arrears = olesia.calculate_arrears()
        auto_due = olesia.calculate_auto_due_date()
        print(f"   欠费 = {arrears}")
        print(f"   自动到期日 = {auto_due}")
    else:
        print("⚠️  未找到 SHIRIAEVA OLESIA")
    
    # 4. 修复 MYTSYK ALEKSANDRA 的数据
    mytsyk = Student.query.filter(Student.name.like('%MYTSYK%')).first()
    if mytsyk:
        mytsyk.fee_restart_date = date(2026, 9, 2)
        mytsyk.fee_start_paid = 6000  # 第一学年已消费6000
        db.session.commit()
        print(f"\n✅ 修复 MYTSYK ALEKSANDRA (ID:{mytsyk.id})")
        print(f"   fee_restart_date = 2026-09-02（换房次日）")
        print(f"   fee_start_paid = 6000（第一学年已消费6000）")
        print(f"   total_paid = {mytsyk.total_paid}")
        print(f"   available = {mytsyk.total_paid - mytsyk.fee_start_paid}")
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
    restart_not_null = sum(1 for s in all_students if s.fee_restart_date is not None)
    print(f"  在住学生总数：{len(all_students)}")
    print(f"  fee_restart_date 不为空的数量：{restart_not_null}（换过房的学生）")
    print(f"  fee_restart_date 为空的数量：{len(all_students) - restart_not_null}（未换过房，计算时用check_in_date）")
    
    # 检查欠费学生
    arrears_list = [s for s in all_students if s.has_arrears()]
    if arrears_list:
        print(f"\n  当前欠费学生（{len(arrears_list)}人）：")
        for s in arrears_list:
            print(f"    {s.name}: 欠费 ¥{s.calculate_arrears():.2f}")
    else:
        print("\n  ✅ 无欠费学生")
    print("=" * 60)
