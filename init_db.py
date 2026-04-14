#!/usr/bin/env python3
"""
数据库初始化和命令行工具
"""
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, User, FeeStandard


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
        
        db.session.commit()
        print('数据库初始化完成！')


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
            is_admin=True
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


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='学生公寓管理系统 - 数据库工具')
    parser.add_argument('command', choices=['init-db', 'create-admin', 'reset-db'], 
                       help='命令: init-db=初始化数据库, create-admin=创建管理员, reset-db=重置数据库')
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
