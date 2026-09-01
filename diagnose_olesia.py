"""
诊断脚本：检查 SHIRIAEVA OLESIA 换房后的详细状态
"""
from app import create_app
from app.models import db, Student, FeeRecord, FeeStandard
from datetime import date, timedelta

app = create_app()

with app.app_context():
    student = Student.query.filter(Student.name.like('%SHIRIAEVA%')).first()
    
    if not student:
        print("未找到 SHIRIAEVA OLESIA")
    else:
        print("=" * 60)
        print(f"学生：{student.name}")
        print(f"当前房间：{student.room.building + '-' + student.room.room_number if student.room else '无'}")
        print(f"当前收费标准：{student.fee_standard.name if student.fee_standard else '无'}")
        print(f"收费标准价格：{student.fee_standard.price if student.fee_standard else 0} 元/{student.fee_standard.unit if student.fee_standard else ''}")
        print(f"入住日期：{student.check_in_date}")
        print(f"到期日期（数据库）：{student.payment_due_date}")
        print(f"total_paid：{student.total_paid}")
        print(f"calculate_base_paid()：{student.calculate_base_paid()}")
        print(f"bed_occupancy：{student.bed_occupancy}")
        print(f"status：{student.status}")
        print()
        
        # 计算当前应该的费用
        fee_std = student.fee_standard
        if fee_std and student.check_in_date:
            unit_days = fee_std.get_unit_days()
            daily = fee_std.price / unit_days
            print(f"日费率：{fee_std.price} / {unit_days} = {daily:.2f} 元/天")
            
            # 从入住到今天的天数
            today = date(2026, 9, 1)
            total_days = (today - student.check_in_date).days
            billing_days = fee_std.count_billing_days(student.check_in_date, today + timedelta(days=1))
            print(f"从入住到今天的总天数：{total_days} 天")
            print(f"计费天数（跳过假期）：{billing_days} 天")
            print(f"应该消费：{billing_days} x {daily:.2f} = {billing_days * daily:.2f} 元")
            print(f"实际已缴：{student.calculate_base_paid()} 元")
            print(f"差额（正数=欠费，负数=多缴）：{billing_days * daily - student.calculate_base_paid():.2f} 元")
        
        print()
        print("=" * 60)
        print("缴费记录：")
        records = student.fee_records.order_by(FeeRecord.payment_date).all()
        for r in records:
            print(f"  ID={r.id}, 日期={r.payment_date}, 金额={r.amount}, 类型={r.record_type}, 备注={r.notes}")
