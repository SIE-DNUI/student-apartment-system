"""
修复脚本：删除错误的换房缴费记录，修正 total_paid
在 PythonAnywhere 的 Bash console 里运行：python fix_fee_bug.py
"""
from app import create_app
from app.models import db, Student, FeeRecord

app = create_app()

with app.app_context():
    print("=" * 60)
    print("开始修复 MYTSYK ALEKSANDRA 的数据...")
    print("=" * 60)
    
    # 查找 MYTSYK ALEKSANDRA
    student = Student.query.filter(Student.name.like('%MYTSYK%')).first()
    
    if not student:
        print("❌ 未找到 MYTSYK ALEKSANDRA")
    else:
        print(f"学生：{student.name} (ID: {student.id})")
        print(f"修复前 total_paid: {student.total_paid}")
        
        # 查找错误的 fee_record (ID=123)
        wrong_record = FeeRecord.query.get(123)
        
        if not wrong_record:
            print("❌ 未找到 ID=123 的缴费记录")
        elif wrong_record.student_id != student.id:
            print(f"❌ ID=123 的记录不属于该学生（属于 student_id={wrong_record.student_id}）")
        else:
            print(f"\n找到错误记录：")
            print(f"  ID: {wrong_record.id}")
            print(f"  金额: {wrong_record.amount}")
            print(f"  类型: {wrong_record.record_type}")
            print(f"  备注: {wrong_record.notes}")
            
            # 删除错误记录
            db.session.delete(wrong_record)
            print(f"\n✅ 已删除 ID=123 的记录")
            
            # 修正 total_paid
            old_total_paid = student.total_paid
            student.total_paid = 18000.0  # 6000 + 12000
            print(f"✅ 已将 total_paid 从 {old_total_paid} 修正为 {student.total_paid}")
            
            db.session.commit()
            print(f"\n✅ 修复完成！")
            
            # 验证修复结果
            print(f"\n修复后验证：")
            print(f"  total_paid: {student.total_paid}")
            print(f"  calculate_base_paid(): {student.calculate_base_paid()}")
            
            records = student.fee_records.order_by(FeeRecord.payment_date).all()
            print(f"  剩余缴费记录（{len(records)} 条）：")
            for r in records:
                print(f"    ID={r.id}, 金额={r.amount}, 备注={r.notes}")
    
    print("\n" + "=" * 60)
    print("清理 SHIRIAEVA OLESIA 的冗余记录...")
    print("=" * 60)
    
    # 查找 SHIRIAEVA OLESIA
    student2 = Student.query.filter(Student.name.like('%SHIRIAEVA%')).first()
    
    if not student2:
        print("❌ 未找到 SHIRIAEVA OLESIA")
    else:
        print(f"学生：{student2.name} (ID: {student2.id})")
        
        # 查找冗余的 fee_record (ID=122，金额为0)
        redundant_record = FeeRecord.query.get(122)
        
        if not redundant_record:
            print("❌ 未找到 ID=122 的缴费记录")
        elif redundant_record.student_id != student2.id:
            print(f"❌ ID=122 的记录不属于该学生")
        elif redundant_record.amount != 0:
            print(f"⚠️  ID=122 的记录金额不是 0（金额={redundant_record.amount}），跳过删除")
        else:
            print(f"\n找到冗余记录（金额为0）：")
            print(f"  ID: {redundant_record.id}")
            print(f"  金额: {redundant_record.amount}")
            print(f"  备注: {redundant_record.notes}")
            
            # 删除冗余记录
            db.session.delete(redundant_record)
            db.session.commit()
            print(f"\n✅ 已删除 ID=122 的冗余记录")
    
    print("\n" + "=" * 60)
    print("修复完成！请在系统中验证数据是否正确。")
    print("=" * 60)
