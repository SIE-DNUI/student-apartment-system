#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为 students 表添加 archived_room_id 字段

用途：解决退房后 room_id 被清空，导致归档学生无法被成本统计的问题

迁移说明：
1. 添加 archived_room_id 字段用于存储归档学生的原房间ID
2. 对于已存在的归档学生（room_id为空但status为archived），需要根据deleted_at和check_in_date推断
3. 新退房/删除的学生会自动保存 archived_room_id

执行方式：
    python migrations/add_archived_room_id.py

回滚方式（如果需要）：
    ALTER TABLE students DROP COLUMN archived_room_id;
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, Student, Room
from datetime import datetime


def upgrade():
    """执行迁移：添加 archived_room_id 字段"""
    app = create_app()
    
    with app.app_context():
        # 检查字段是否已存在
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('students')]
        
        if 'archived_room_id' in columns:
            print("字段 archived_room_id 已存在，跳过迁移。")
            return
        
        # 添加新字段
        print("正在添加 archived_room_id 字段...")
        db.session.execute(db.text('''
            ALTER TABLE students ADD COLUMN archived_room_id INTEGER REFERENCES rooms(id)
        '''))
        db.session.commit()
        print("字段 archived_room_id 添加成功。")
        print("\n迁移完成！")
        print("注意：已归档学生的历史房间信息无法自动恢复，需要手动设置 archived_room_id。")


def downgrade():
    """回滚迁移：删除 archived_room_id 字段"""
    app = create_app()
    
    with app.app_context():
        # 检查字段是否存在
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('students')]
        
        if 'archived_room_id' not in columns:
            print("字段 archived_room_id 不存在，跳过回滚。")
            return
        
        # 删除字段
        print("正在删除 archived_room_id 字段...")
        db.session.execute(db.text('''
            ALTER TABLE students DROP COLUMN archived_room_id
        '''))
        db.session.commit()
        print("字段 archived_room_id 删除成功。")
        print("\n回滚完成！")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--downgrade':
        downgrade()
    else:
        upgrade()
