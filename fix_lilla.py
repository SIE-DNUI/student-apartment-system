#!/usr/bin/env python3
"""修复 LILLA LISA APSA 的缴费记录：删除补差价记录，重置 total_paid"""

import sys
sys.path.insert(0, '/home/SIE-DNUI/student-apartment-system')

from app import create_app
from app.models import db, Student, FeeRecord

app = create_app()

with app.app_context():
    # 查找学生
    student = Student.query.filter(Student.name.like('%LILLA%')).first()
    
    if not student:
        print("❌ 未找到学生 LILLA LISA APSA")
        sys.exit(1)
    
    print(f"✅ 找到学生：{student.name} (ID: {student.id})")
    print(f"   修复前 total_paid：¥{student.total_paid:.2f}")
    
    # 查找并删除"补差价"记录
    bad_records = FeeRecord.query.filter(
        FeeRecord.student_id == student.id,
        FeeRecord.notes.like('%换房型补差价%')
    ).all()
    
    if not bad_records:
        print("✅ 未找到需要删除的补差价记录")
    else:
        total_refund = 0
        for r in bad_records:
            print(f"   🗑️  删除记录：{r.payment_date} ¥{r.amount:.2f} - {r.notes}")
            total_refund += r.amount
            db.session.delete(r)
        
        # 重置 total_paid
        student.total_paid = (student.total_paid or 0) - total_refund
        print(f"   💰 退还补差价金额：¥{total_refund:.2f}")
        print(f"   💰 修复后 total_paid：¥{student.total_paid:.2f}")
    
    db.session.commit()
    print("\n✅ 修复完成！")
    
    # 验证
    records = FeeRecord.query.filter_by(student_id=student.id).order_by(FeeRecord.payment_date).all()
    print(f"\n📋 修复后缴费记录（共 {len(records)} 条）：")
    for r in records:
        print(f"   {r.payment_date} ¥{r.amount:.2f} - {r.notes or '-'}")
    print(f"   total_paid：¥{student.total_paid:.2f}")
