# -*- coding: utf-8 -*-
"""
收费管理路由模块
提供收费相关功能
"""
from flask import render_template, Blueprint, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, DateField
from wtforms.validators import DataRequired, Optional, NumberRange, InputRequired
from app.models import db
from app.models import FeeStandard, FeeRecord, Student, Alert
from app.decorators import permission_required
from datetime import datetime, date, timedelta

bp = Blueprint('fees', __name__, url_prefix='/fees')


# ==================== 收费标准管理 ====================

class FeeStandardForm(FlaskForm):
    name = StringField('标准名称', validators=[DataRequired(message='请输入标准名称')])
    price = FloatField('单价', validators=[InputRequired(message='请输入单价')])
    unit = SelectField('单位', choices=[('月', '月'), ('学期', '学期'), ('年', '年'), ('天', '天')], validators=[DataRequired()])
    description = StringField('备注说明', validators=[Optional()])
    is_active = SelectField('是否启用', choices=[('1', '是'), ('0', '否')])


@bp.route('/standards')
@login_required
def standards():
    """收费标准列表"""
    fee_standards = FeeStandard.query.order_by(FeeStandard.is_active.desc(), FeeStandard.name).all()
    return render_template('fees/standards.html', title='收费标准', fee_standards=fee_standards)


@bp.route('/standards/add', methods=['GET', 'POST'])
@login_required
@permission_required('write')
def add_standard():
    """添加收费标准"""
    form = FeeStandardForm()
    
    if form.validate_on_submit():
        existing = FeeStandard.query.filter_by(name=form.name.data).first()
        if existing:
            flash(f'收费标准 {form.name.data} 已存在', 'danger')
            return redirect(url_for('fees.add_standard'))
        
        standard = FeeStandard()
        form.populate_obj(standard)
        standard.is_active = form.is_active.data == '1'
        
        db.session.add(standard)
        db.session.commit()
        
        flash(f'收费标准 {standard.name} 添加成功！', 'success')
        return redirect(url_for('fees.standards'))
    
    return render_template('fees/add_standard.html', title='添加收费标准', form=form)


@bp.route('/standards/edit/<int:standard_id>', methods=['GET', 'POST'])
@login_required
@permission_required('write')
def edit_standard(standard_id):
    """编辑收费标准"""
    standard = FeeStandard.query.get_or_404(standard_id)
    form = FeeStandardForm(obj=standard)
    
    if form.validate_on_submit():
        existing = FeeStandard.query.filter(
            FeeStandard.name == form.name.data,
            FeeStandard.id != standard_id
        ).first()
        
        if existing:
            flash(f'收费标准 {form.name.data} 已存在', 'danger')
            return redirect(url_for('fees.edit_standard', standard_id=standard_id))
        
        form.populate_obj(standard)
        standard.is_active = form.is_active.data == '1'
        db.session.commit()
        
        flash(f'收费标准 {standard.name} 已更新！', 'success')
        return redirect(url_for('fees.standards'))
    
    return render_template('fees/edit_standard.html', title='编辑收费标准', form=form, standard=standard)


@bp.route('/standards/delete/<int:standard_id>', methods=['POST'])
@login_required
@permission_required('write')
def delete_standard(standard_id):
    """删除收费标准"""
    standard = FeeStandard.query.get_or_404(standard_id)
    
    # 检查是否被使用
    if standard.students.count() > 0:
        flash(f'收费标准 {standard.name} 已被 {standard.students.count()} 名学生使用，无法删除', 'danger')
        return redirect(url_for('fees.standards'))
    
    db.session.delete(standard)
    db.session.commit()
    
    flash(f'收费标准 {standard.name} 已删除', 'success')
    return redirect(url_for('fees.standards'))


# ==================== 缴费记录管理 ====================

class FeeRecordForm(FlaskForm):
    student_id = SelectField('学生', coerce=int, validators=[DataRequired(message='请选择学生')])
    amount = FloatField('缴费金额', validators=[DataRequired(message='请输入金额'), NumberRange(min=0.01)])
    payment_date = DateField('缴费日期', format='%Y-%m-%d', validators=[DataRequired(message='请选择日期')])
    payment_method = SelectField('缴费方式', choices=[
        ('', '请选择'),
        ('现金', '现金'),
        ('转账', '转账'),
        ('微信', '微信支付'),
        ('支付宝', '支付宝'),
        ('刷卡', '银行卡')
    ], validators=[Optional()])
    payment_period_start = DateField('缴费期间开始', format='%Y-%m-%d', validators=[Optional()])
    payment_period_end = DateField('缴费期间结束', format='%Y-%m-%d', validators=[Optional()])
    receipt_number = StringField('收据编号', validators=[Optional()])
    operator = StringField('经办人', validators=[Optional()])
    notes = StringField('备注', validators=[Optional()])


@bp.route('/records')
@login_required
def records():
    """缴费记录列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 30
    
    search = request.args.get('search', '')
    
    query = FeeRecord.query
    
    if search:
        query = query.join(Student).filter(
            Student.name.contains(search) | Student.student_id.contains(search)
        )
    
    pagination = query.order_by(FeeRecord.payment_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    fee_records = pagination.items
    
    return render_template('fees/records.html', title='缴费记录',
                         fee_records=fee_records, pagination=pagination, search=search)


@bp.route('/records/add', methods=['GET', 'POST'])
@login_required
@permission_required('write')
def add_record():
    """添加缴费记录"""
    form = FeeRecordForm()
    
    # 填充学生选择
    students = Student.query.filter_by(status='active').order_by(Student.name).all()
    form.student_id.choices = [(s.id, f'{s.name} ({s.student_id or "无学号"})') for s in students]
    
    # 设置默认日期为今天
    form.payment_date.data = date.today()
    
    if form.validate_on_submit():
        student = Student.query.get(form.student_id.data)
        
        # 计算到期日期
        due_date = student.calculate_payment_due_date(form.amount.data)
        
        fee_record = FeeRecord()
        form.populate_obj(fee_record)
        
        if due_date:
            fee_record.payment_period_end = due_date
            if student.payment_due_date:
                # 累加到现有到期日期
                student.payment_due_date = due_date
            else:
                student.payment_due_date = due_date
        
        # 设置当前用户为经办人
        if not fee_record.operator:
            fee_record.operator = current_user.username
        
        student.payment_status = 'paid'
        
        db.session.add(fee_record)
        db.session.commit()
        
        flash(f'缴费记录已添加，到期日期更新为 {due_date}', 'success')
        return redirect(url_for('fees.records'))
    
    return render_template('fees/add_record.html', title='添加缴费记录', form=form)


@bp.route('/records/edit/<int:record_id>', methods=['GET', 'POST'])
@login_required
@permission_required('write')
def edit_record(record_id):
    """编辑缴费记录"""
    record = FeeRecord.query.get_or_404(record_id)
    form = FeeRecordForm(obj=record)
    
    # 填充学生选择
    students = Student.query.filter_by(status='active').order_by(Student.name).all()
    form.student_id.choices = [(s.id, f'{s.name} ({s.student_id or "无学号"})') for s in students]
    
    if form.validate_on_submit():
        form.populate_obj(record)
        db.session.commit()
        
        flash('缴费记录已更新！', 'success')
        return redirect(url_for('fees.records'))
    
    return render_template('fees/edit_record.html', title='编辑缴费记录', form=form, record=record)


@bp.route('/records/delete/<int:record_id>', methods=['POST'])
@login_required
@permission_required('write')
def delete_record(record_id):
    """删除缴费记录"""
    record = FeeRecord.query.get_or_404(record_id)
    
    # 重新计算到期日期
    student = record.student
    db.session.delete(record)
    
    # 重新计算最新的到期日期
    latest_record = FeeRecord.query.filter_by(student_id=student.id).order_by(FeeRecord.payment_period_end.desc()).first()
    if latest_record:
        student.payment_due_date = latest_record.payment_period_end
    else:
        student.payment_due_date = None
    
    db.session.commit()
    
    flash('缴费记录已删除', 'success')
    return redirect(url_for('fees.records'))


# ==================== 缴费计算器 ====================

@bp.route('/calculator')
@login_required
def calculator():
    """缴费计算器"""
    student_id = request.args.get('student_id', type=int)
    amount = request.args.get('amount', type=float)
    
    student = None
    calculated_due_date = None
    fee_standard = None
    
    if student_id:
        student = Student.query.get(student_id)
        if student and student.fee_standard_id:
            fee_standard = FeeStandard.query.get(student.fee_standard_id)
    
    if student and amount and amount > 0:
        calculated_due_date = student.calculate_payment_due_date(amount)
    
    students = Student.query.filter_by(status='active').order_by(Student.name).all()
    
    return render_template('fees/calculator.html', title='缴费计算器',
                         students=students, student=student, fee_standard=fee_standard,
                         amount=amount, calculated_due_date=calculated_due_date)


@bp.route('/calculate', methods=['POST'])
@login_required
def calculate():
    """AJAX计算缴费到期日期"""
    student_id = request.form.get('student_id', type=int)
    amount = request.form.get('amount', type=float)
    
    if not student_id or not amount or amount <= 0:
        return {'error': '请选择学生并输入有效金额'}
    
    student = Student.query.get(student_id)
    if not student:
        return {'error': '学生不存在'}
    
    due_date = student.calculate_payment_due_date(amount)
    
    if not due_date:
        return {'error': '无法计算，请先为学生设置收费标准'}
    
    return {
        'due_date': due_date.strftime('%Y-%m-%d'),
        'student_name': student.name
    }


# ==================== 到期提醒管理 ====================

@bp.route('/reminders')
@login_required
def reminders():
    """缴费到期提醒"""
    today = date.today()
    reminder_days = 7  # 提前7天提醒
    
    # 即将到期（7天内）
    due_soon = Student.query.filter(
        Student.payment_due_date != None,
        Student.payment_due_date <= today + timedelta(days=reminder_days),
        Student.payment_due_date >= today,
        Student.status == 'active'
    ).order_by(Student.payment_due_date).all()
    
    # 已过期
    overdue = Student.query.filter(
        Student.payment_due_date != None,
        Student.payment_due_date < today,
        Student.status == 'active'
    ).order_by(Student.payment_due_date.desc()).all()
    
    # 未设置到期日期
    no_due_date = Student.query.filter(
        Student.payment_due_date == None,
        Student.room_id != None,
        Student.status == 'active'
    ).all()
    
    return render_template('fees/reminders.html', title='缴费提醒',
                         due_soon=due_soon, overdue=overdue, no_due_date=no_due_date,
                         today=today, reminder_days=reminder_days)


@bp.route('/generate-alerts')
@login_required
@permission_required('write')
def generate_alerts():
    """生成到期提醒"""
    today = date.today()
    reminder_days = 7
    
    # 清除旧的未读提醒
    Alert.query.filter_by(alert_type='payment_due', is_read=False).delete()
    
    alerts_created = 0
    
    # 生成即将到期的提醒
    students_due_soon = Student.query.filter(
        Student.payment_due_date != None,
        Student.payment_due_date <= today + timedelta(days=reminder_days),
        Student.payment_due_date >= today,
        Student.status == 'active'
    ).all()
    
    for student in students_due_soon:
        alert = Alert(
            student_id=student.id,
            alert_type='payment_due',
            title=f'学生 {student.name} 缴费即将到期',
            message=f'缴费到期日期: {student.payment_due_date}，还有 {student.days_until_due()} 天',
            priority='high' if student.days_until_due() <= 3 else 'normal',
            due_date=student.payment_due_date
        )
        db.session.add(alert)
        alerts_created += 1
    
    # 生成已过期的提醒
    students_overdue = Student.query.filter(
        Student.payment_due_date != None,
        Student.payment_due_date < today,
        Student.status == 'active'
    ).all()
    
    for student in students_overdue:
        alert = Alert(
            student_id=student.id,
            alert_type='payment_overdue',
            title=f'学生 {student.name} 缴费已过期',
            message=f'缴费到期日期: {student.payment_due_date}，已过期 {abs(student.days_until_due())} 天',
            priority='urgent',
            due_date=student.payment_due_date
        )
        db.session.add(alert)
        alerts_created += 1
    
    db.session.commit()
    
    flash(f'已生成 {alerts_created} 条提醒', 'success')
    return redirect(url_for('fees.reminders'))
