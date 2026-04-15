#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化和命令行工具
"""
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, User, FeeStandard, Room, Reservation


def init_db():
    """初始化数据库"""
    app = create_app()
    with app.app_context():
        # 创建所有表
        db.create_all()
        
        # 检查是否需要创建默认收费标准
        if FeeStandard.query.count() == 0:
            default_standards = [
                FeeStandard(name='标准双人间', price=800, unit='月', description='普通双人间配置'),
                FeeStandard(name='高级双人间', price=1200, unit='月', description='带独立卫浴'),
                FeeStandard(name='单人间', price=1500, unit='月', description='独立房间'),
                FeeStandard(name='四人间', price=600, unit='月', description='经济型四人间'),
            ]
            for std in default_standards:
                db.session.add(std)
        
        # 检查是否需要创建示例房间
        if Room.query.count() == 0:
            print('正在创建示例房间...')
            buildings = ['1号楼', '2号楼', '3号楼']
            for building in buildings:
                for floor in range(1, 4):
                    for room_num in range(1, 11):
                        room = Room(
                            building=building,
                            room_number=f'{floor}0{room_num}',
                            floor=floor,
                            capacity=2,
                            status='available'
                        )
                        db.session.add(room)
        
        db.session.commit()
        print('数据库初始化完成！')


def migrate():
    """数据库字段迁移"""
    app = create_app()
    with app.app_context():
        from sqlalchemy import inspect
        
        inspector = inspect(db.engine)
        
        # 迁移 Reservation 表
        reservation_columns = [c['name'] for c in inspector.get_columns('reservations')]
        new_reservation_columns = ['department', 'group_name', 'person_count', 'rooms_needed']
        
        with db.engine.connect() as conn:
            for col, col_type in [
                ('department', 'VARCHAR(100)'),
                ('group_name', 'VARCHAR(200)'),
                ('person_count', 'INTEGER DEFAULT 0'),
                ('rooms_needed', 'INTEGER DEFAULT 1')
            ]:
                if col not in reservation_columns:
                    try:
                        conn.execute(db.text(f'ALTER TABLE reservations ADD COLUMN {col} {col_type}'))
                        conn.commit()
                        print(f'✓ 成功添加字段: reservations.{col}')
                    except Exception as e:
                        print(f'× 添加字段失败: reservations.{col} - {e}')
        
        # 迁移 User 表 - 添加 role 字段
        user_columns = [c['name'] for c in inspector.get_columns('users')]
        if 'role' not in user_columns:
            with db.engine.connect() as conn:
                try:
                    conn.execute(db.text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'read_write'"))
                    conn.commit()
                    print('✓ 成功添加字段: users.role')
                except Exception as e:
                    print(f'× 添加字段失败: users.role - {e}')
        
        # 迁移 Student 表 - 添加 residence_permit_expiry 字段
        student_columns = [c['name'] for c in inspector.get_columns('students')]
        if 'residence_permit_expiry' not in student_columns:
            with db.engine.connect() as conn:
                try:
                    conn.execute(db.text('ALTER TABLE students ADD COLUMN residence_permit_expiry DATE'))
                    conn.commit()
                    print('✓ 成功添加字段: students.residence_permit_expiry')
                except Exception as e:
                    print(f'× 添加字段失败: students.residence_permit_expiry - {e}')
        
        # 迁移 Student 表 - 添加归档相关字段
        if 'deleted_at' not in student_columns:
            with db.engine.connect() as conn:
                try:
                    conn.execute(db.text('ALTER TABLE students ADD COLUMN deleted_at DATETIME'))
                    conn.commit()
                    print('✓ 成功添加字段: students.deleted_at')
                except Exception as e:
                    print(f'× 添加字段失败: students.deleted_at - {e}')
        
        if 'retention_until' not in student_columns:
            with db.engine.connect() as conn:
                try:
                    conn.execute(db.text('ALTER TABLE students ADD COLUMN retention_until DATE'))
                    conn.commit()
                    print('✓ 成功添加字段: students.retention_until')
                except Exception as e:
                    print(f'× 添加字段失败: students.retention_until - {e}')
        
        print('字段迁移完成！')


def create_admin(username='admin', password='admin123', email='admin@example.com'):
    """创建管理员账户"""
    app = create_app()
    with app.app_context():
        # 检查是否已存在
        existing = User.query.filter_by(username=username).first()
        if existing:
            print(f'用户 {username} 已存在')
            return
        
        # 创建管理员
        admin = User(
            username=username,
            email=email,
            is_admin=True,
            role='admin'
        )
        admin.set_password(password)
        
        db.session.add(admin)
        db.session.commit()
        
        print(f'管理员账户创建成功！')
        print(f'用户名: {username}')
        print(f'密码: {password}')
        print(f'邮箱: {email}')


def reset_db():
    """重置数据库（慎用！）"""
    app = create_app()
    with app.app_context():
        confirm = input('确定要删除所有数据吗？此操作不可恢复！(yes/no): ')
        if confirm.lower() == 'yes':
            db.drop_all()
            db.create_all()
            print('数据库已重置！')
        else:
            print('操作已取消')


def seed_demo():
    """添加演示数据"""
    app = create_app()
    with app.app_context():
        from datetime import date, timedelta
        
        # 检查是否已有演示数据
        if Reservation.query.count() > 0:
            print('已有入住计划数据，跳过演示数据创建')
            return
        
        # 创建一些演示入住计划
        demo_reservations = [
            Reservation(
                department='国际交流处',
                group_name='美国交换生团',
                person_count=20,
                rooms_needed=10,
                check_in_date=date.today() + timedelta(days=7),
                check_out_date=date.today() + timedelta(days=100),
                status='pending',
                notes='春季学期交换生'
            ),
            Reservation(
                department='人事处',
                group_name='新入职教师',
                person_count=6,
                rooms_needed=3,
                check_in_date=date.today() + timedelta(days=14),
                check_out_date=date.today() + timedelta(days=180),
                status='pending',
                notes='新学期教师公寓'
            ),
            Reservation(
                department='国际交流处',
                group_name='德国暑期研学团',
                person_count=40,
                rooms_needed=20,
                check_in_date=date.today() + timedelta(days=90),
                check_out_date=date.today() + timedelta(days=120),
                status='pending',
                notes='暑期短期项目'
            ),
        ]
        
        for r in demo_reservations:
            db.session.add(r)
        
        db.session.commit()
        print('演示数据创建完成！')


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='学生公寓管理系统 - 数据库工具')
    parser.add_argument('command', 
                       choices=['init-db', 'create-admin', 'reset-db', 'migrate', 'seed'], 
                       help='命令: init-db=初始化数据库, create-admin=创建管理员, reset-db=重置数据库, migrate=迁移字段, seed=添加演示数据')
    parser.add_argument('--username', default='admin', help='管理员用户名')
    parser.add_argument('--password', default='admin123', help='管理员密码')
    parser.add_argument('--email', default='admin@example.com', help='管理员邮箱')
    
    args = parser.parse_args()
    
    if args.command == 'init-db':
        init_db()
    elif args.command == 'create-admin':
        create_admin(args.username, args.password, args.email)
    elif args.command == 'reset-db':
        reset_db()
    elif args.command == 'migrate':
        migrate()
    elif args.command == 'seed':
        seed_demo()
