# -*- coding: utf-8 -*-
"""
权限装饰器模块
提供基于用户角色的权限控制装饰器
"""
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def admin_required(f):
    """
    管理员权限装饰器
    只有管理员（role='admin' 或 is_admin=True）可以访问
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_admin_role():
            flash('您没有权限访问此页面', 'danger')
            return redirect(url_for('dashboard.index'))
        
        return f(*args, **kwargs)
    return decorated_function


def permission_required(permission='read'):
    """
    权限控制装饰器
    permission: 'read' - 只读权限
                'write' - 读写权限
    
    用法:
    @permission_required('read')  # 需要至少读权限
    @permission_required('write') # 需要写权限
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('请先登录', 'warning')
                return redirect(url_for('auth.login'))
            
            if permission == 'read':
                if not current_user.can_read():
                    flash('您没有权限访问此页面', 'danger')
                    return redirect(url_for('dashboard.index'))
            elif permission == 'write':
                if not current_user.can_write():
                    flash('您没有权限执行此操作', 'danger')
                    return redirect(url_for('dashboard.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def read_only_block(f):
    """
    阻止只读用户执行POST请求
    只读用户只能访问GET请求
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login'))
        
        if current_user.role == 'read_only':
            flash('只读用户无权执行此操作', 'warning')
            return redirect(url_for('dashboard.index'))
        
        return f(*args, **kwargs)
    return decorated_function
