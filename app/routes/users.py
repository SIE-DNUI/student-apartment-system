# -*- coding: utf-8 -*-
"""
用户管理路由模块
提供用户管理功能，包括用户列表、创建、编辑、删除
仅管理员可访问
"""
from flask import render_template, Blueprint, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, PasswordField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional
from app.models import db, User
from app.decorators import admin_required

bp = Blueprint('users', __name__, url_prefix='/users')


class UserForm(FlaskForm):
    """用户表单"""
    username = StringField('用户名', validators=[
        DataRequired(message='请输入用户名'),
        Length(min=3, max=64, message='用户名长度必须在3-64个字符之间')
    ])
    email = StringField('邮箱', validators=[
        DataRequired(message='请输入邮箱'),
        Email(message='请输入有效的邮箱地址')
    ])
    role = SelectField('角色', choices=[
        ('admin', '管理员'),
        ('read_write', '读写用户'),
        ('read_only', '只读用户')
    ], validators=[DataRequired(message='请选择角色')])
    password = PasswordField('密码', validators=[
        Optional(),
        Length(min=6, max=128, message='密码长度必须在6-128个字符之间')
    ])
    password_confirm = PasswordField('确认密码', validators=[
        EqualTo('password', message='两次输入的密码不一致')
    ])


@bp.route('/')
@login_required
@admin_required
def index():
    """用户列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    pagination = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    users = pagination.items
    
    return render_template('users/index.html',
                         title='用户管理',
                         users=users,
                         pagination=pagination)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add():
    """创建用户"""
    form = UserForm()
    
    if form.validate_on_submit():
        # 检查用户名是否已存在
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('用户名已存在', 'danger')
            return render_template('users/add.html', title='创建用户', form=form)
        
        # 检查邮箱是否已存在
        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_email:
            flash('邮箱已被使用', 'danger')
            return render_template('users/add.html', title='创建用户', form=form)
        
        user = User()
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        user.is_admin = (form.role.data == 'admin')
        
        if form.password.data:
            user.set_password(form.password.data)
        else:
            flash('请输入密码', 'danger')
            return render_template('users/add.html', title='创建用户', form=form)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'用户 {user.username} 创建成功！', 'success')
        return redirect(url_for('users.index'))
    
    return render_template('users/add.html', title='创建用户', form=form)


@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(id):
    """编辑用户"""
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    
    # 不显示密码确认字段初始值
    form.password_confirm.data = ''
    
    if form.validate_on_submit():
        # 检查用户名是否与其他用户冲突
        existing_user = User.query.filter(
            User.username == form.username.data,
            User.id != id
        ).first()
        if existing_user:
            flash('用户名已存在', 'danger')
            return render_template('users/edit.html', title='编辑用户', form=form, user=user)
        
        # 检查邮箱是否与其他用户冲突
        existing_email = User.query.filter(
            User.email == form.email.data,
            User.id != id
        ).first()
        if existing_email:
            flash('邮箱已被使用', 'danger')
            return render_template('users/edit.html', title='编辑用户', form=form, user=user)
        
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        user.is_admin = (form.role.data == 'admin')
        
        if form.password.data:
            user.set_password(form.password.data)
        
        db.session.commit()
        
        flash(f'用户 {user.username} 更新成功！', 'success')
        return redirect(url_for('users.index'))
    
    return render_template('users/edit.html', title='编辑用户', form=form, user=user)


@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete(id):
    """删除用户"""
    user = User.query.get_or_404(id)
    
    # 不允许删除自己
    if user.id == current_user.id:
        flash('不能删除当前登录用户', 'danger')
        return redirect(url_for('users.index'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f'用户 {username} 已删除', 'success')
    return redirect(url_for('users.index'))


@bp.route('/profile/<int:id>')
@login_required
def profile(id):
    """用户详情"""
    user = User.query.get_or_404(id)
    return render_template('users/profile.html', title='用户详情', user=user)
