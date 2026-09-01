"""
小修复：清除 SHIRIAEVA OLESIA 的旧 payment_due_date
让系统基于 fee_restart_date 自动重算到期日
在 PythonAnywhere 的 Bash console 里运行：python fix_olesia_due_date.py
"""
from app import create_app
from app.models import db, Student

app = create_app()

with app.app_context():
    olesia = Student.query.filter(Student.name.like('%SHIRIAEVA%')).first()
    if not olesia:
        print("❌ 未找到 SHIRIAEVA OLESIA")
        exit(1)
    
    print(f"学生：SHIRIAEVA OLESIA (ID: {olesia.id})")
    print(f"  修复前 payment_due_date = {olesia.payment_due_date}")
    print(f"  fee_restart_date = {olesia.fee_restart_date}")
    print(f"  收费标准 = {olesia.fee_standard.name}")
    print(f"  total_paid = {olesia.total_paid}")
    
    # 清除旧的手动到期日，让系统自动计算
    old_due = olesia.payment_due_date
    olesia.payment_due_date = None
    db.session.commit()
    
    print(f"\n✅ 已清除 payment_due_date（原值: {old_due}）")
    print(f"  系统将基于 fee_restart_date={olesia.fee_restart_date} 自动计算到期日")
    
    # 验证自动计算的到期日
    auto_due = olesia.calculate_auto_due_date()
    print(f"  自动计算到期日 = {auto_due}")
    
    # 验证欠费
    arrears = olesia.calculate_arrears()
    print(f"  欠费金额 = {arrears}")
    
    if arrears == 0:
        print(f"\n✅ SHIRIAEVA OLESIA 不再显示欠费！")
    else:
        print(f"\n⚠️ 仍有欠费 ¥{arrears:.2f}，请检查数据")
