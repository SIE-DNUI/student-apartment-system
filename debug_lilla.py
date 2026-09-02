#!/usr/bin/env python3
"""诊断 LILLA LISA APSA 的缴费记录"""

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
    print(f"   房间：{student.room.name if student.room else '无'}")
    print(f"   收费标准：{student.fee_standard.name if student.fee_standard else '无'}")
    print(f"   入住日期：{student.check_in_date}")
    print(f"   费用起算日期：{student.fee_restart_date or '（未设置，使用入住日期）'}")
    print(f"   fee_start_paid：{student.fee_start_paid}")
    print(f"   total_paid：{student.total_paid}")
    print(f"   payment_due_date：{student.payment_due_date}")
    print()
    
    # 查询缴费记录
    records = FeeRecord.query.filter_by(student_id=student.id).order_by(FeeRecord.payment_date).all()
    
    print(f"📋 缴费记录（共 {len(records)} 条）：")
    print("-" * 100)
    print(f"{'日期':<12} {'类型':<10} {'金额':>10} {'方式':<15} {'备注'}")
    print("-" * 100)
    
    total_amount = 0
    for r in records:
        rtype = '退费' if r.is_refund() else ('结算' if r.record_type == 'adjustment' else '缴费')
        print(f"{str(r.payment_date):<12} {rtype:<10} ¥{r.amount:>9.2f} {r.payment_method or '-':<15} {r.notes or '-'}")
        total_amount += r.amount
    
    print("-" * 100)
    print(f"缴费记录总和：¥{total_amount:.2f}")
    print(f"total_paid：¥{student.total_paid:.2f}")
    
    if abs(total_amount - (student.total_paid or 0)) > 0.01:
        print(f"\n⚠️  警告：缴费记录总和（¥{total_amount:.2f}）与 total_paid（¥{student.total_paid:.2f}）不一致！")
        print(f"   差额：¥{total_amount - (student.total_paid or 0):.2f}")
    else:
        print(f"\n✅ 缴费记录总和与 total_paid 一致")
