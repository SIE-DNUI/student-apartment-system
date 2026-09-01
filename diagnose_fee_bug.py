"""
诊断脚本：检查 MYTSYK ALEKSANDRA 和 SHIRIAEVA OLESIA 的费用数据
在 PythonAnywhere 的 Bash console 里运行：python diagnose_fee_bug.py
"""
from app import create_app
from app.models import db, Student, FeeRecord

app = create_app()

with app.app_context():
    # 查找这两个学生（模糊匹配）
    students = Student.query.filter(
        db.or_(
            Student.name.like('%MYTSYK%'),
            Student.name.like('%ALEKSANDRA%'),
            Student.name.like('%SHIRIAEVA%'),
            Student.name.like('%OLESIA%')
        )
    ).all()
    
    print(f"找到 {len(students)} 个匹配的学生\n")
    
    if not students:
        print("未找到相关学生，列出所有学生供参考：")
        all_students = Student.query.order_by(Student.name).all()
        for s in all_students:
            print(f"  - {s.name} (ID: {s.id}, status: {s.status})")
    else:
        for s in students:
            print("=" * 60)
            print(f"学生：{s.name} (ID: {s.id}, 学号: {s.student_id})")
            print(f"当前房间：{s.room.building + '-' + s.room.room_number if s.room else '无'}")
            print(f"收费标准：{s.fee_standard.name if s.fee_standard else '无'}")
            print(f"total_paid（数据库字段）: {s.total_paid}")
            print(f"calculate_base_paid()（显示值）: {s.calculate_base_paid()}")
            print(f"入住日期：{s.check_in_date}")
            print(f"到期日期：{s.payment_due_date}")
            print(f"bed_occupancy: {s.bed_occupancy}")
            print(f"status: {s.status}")
            print()
            
            # 显示所有缴费记录
            records = s.fee_records.order_by(FeeRecord.payment_date).all()
            print(f"缴费记录（共 {len(records)} 条）：")
            print("-" * 100)
            print(f"{'ID':<6} {'日期':<12} {'类型':<10} {'金额':<12} {'方式':<12} {'备注'}")
            print("-" * 100)
            for r in records:
                print(f"{r.id:<6} {str(r.payment_date):<12} {r.record_type:<10} {r.amount:<12.1f} {(r.payment_method or ''):<12} {r.notes or ''}")
            print("-" * 100)
            
            # 计算各类型记录合计
            payment_sum = sum(r.amount for r in records if r.record_type == 'payment')
            refund_sum = sum(abs(r.amount) for r in records if r.record_type == 'refund')
            print(f"Payment 记录合计：{payment_sum:.1f}")
            print(f"Refund 记录合计：{refund_sum:.1f}")
            print(f"Payment - Refund = {payment_sum - refund_sum:.1f}")
            
            # 标记可疑记录（包含"换房"关键字的）
            suspicious = [r for r in records if r.notes and '换房' in r.notes]
            if suspicious:
                print(f"\n!!! 发现 {len(suspicious)} 条与换房相关的记录：")
                for r in suspicious:
                    print(f"   ID={r.id}, 金额={r.amount:.1f}, 类型={r.record_type}, 备注={r.notes}")
            print()
