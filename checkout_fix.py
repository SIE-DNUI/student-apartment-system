import re

# 读取文件
with open('app/routes/students.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修改单个退房函数 - 将checked_out改为archived，并添加retention_until
old_checkout = '''    # 清空学生的房间信息
    student.room_id = None
    student.check_out_date = date.today()
    student.status = 'checked_out'
    
    db.session.commit()
    
    flash(f'学生 {student.name} 已退房', 'success')'''

new_checkout = '''    # 清空学生的房间信息并归档
    student.room_id = None
    student.check_out_date = date.today()
    student.status = 'archived'
    student.deleted_at = datetime.utcnow()
    student.retention_until = date.today() + timedelta(days=365*3)  # 保留3年
    
    db.session.commit()
    
    flash(f'学生 {student.name} 已退房并归档，将保留至 {student.retention_until}', 'success')'''

content = content.replace(old_checkout, new_checkout)

# 修改批量退房函数
old_batch = '''            # 清空学生的房间信息
            student.room_id = None
            student.check_out_date = date.today()
            student.status = 'checked_out'
            count += 1'''

new_batch = '''            # 清空学生的房间信息并归档
            student.room_id = None
            student.check_out_date = date.today()
            student.status = 'archived'
            student.deleted_at = datetime.utcnow()
            student.retention_until = date.today() + timedelta(days=365*3)  # 保留3年
            count += 1'''

content = content.replace(old_batch, new_batch)

# 写回文件
with open('app/routes/students.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("退房函数已修改为归档模式")
