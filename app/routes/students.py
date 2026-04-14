from flask import render_template, Blueprint, redirect, url_for, flash, request, current_app
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TextAreaField
from wtforms.validators import DataRequired, Optional
from wtforms.widgets import TextArea
from app import db
from app.models import Student, Room, FeeStandard, FeeRecord, Alert
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename
import pandas as pd
import os

bp = Blueprint('students', __name__, url_prefix='/students')


class StudentForm(FlaskForm):
    student_id = StringField('学号', validators=[Optional()])
    name = StringField('姓名', validators=[DataRequired(message='请输入姓名')])
    gender = SelectField('性别', choices=[('男', '男'), ('女', '女'), ('其他', '其他')], validators=[Optional()])
    nationality = StringField('国籍', validators=[Optional()])
    passport_number = StringField('护照号码', validators=[Optional()])
    phone = StringField('手机号', validators=[Optional()])
    email = StringField('邮箱', validators=[Optional()])
    id_card = StringField('身份证号', validators=[Optional()])
    major = StringField('专业', validators=[Optional()])
    grade = StringField('年级', validators=[Optional()])
    room_id = SelectField('分配房间', coerce=int, validators=[Optional()])
    check_in_date = DateField('入住日期', format='%Y-%m-%d', validators=[Optional()])
    check_out_date = DateField('预计离开日期', format='%Y-%m-%d', validators=[Optional()])
    fee_standard_id = SelectField('收费标准', coerce=int, validators=[Optional()])
    payment_due_date = DateField('缴费到期日期', format='%Y-%m-%d', validators=[Optional()])
    notes = StringField('备注', widget=TextArea(), validators=[Optional()])


@bp.route('/')
@login_required
def index():
    """学生列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    search = request.args.get('search', '')
    
    query = Student.query
    if search:
        query = query.filter(
            (Student.name.contains(search)) |
            (Student.student_id.contains(search)) |
            (Student.phone.contains(search))
        )
    
    pagination = query.order_by(Student.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    students = pagination.items
    
    return render_template('students/index.html', 
                         title='学生管理',
                         students=students,
                         pagination=pagination,
                         search=search)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加学生"""
    form = StudentForm()
    
    # 填充房间选择
    available_rooms = Room.query.filter(Room.current_occupancy < Room.capacity).all()
    form.room_id.choices = [(0, '未分配')] + [(r.id, f'{r.building}-{r.room_number}') for r in available_rooms]
    
    # 填充收费标准选择
    fee_standards = FeeStandard.query.filter_by(is_active=True).all()
    form.fee_standard_id.choices = [(0, '未选择')] + [(f.id, f'{f.name} ({f.price}/{f.unit})') for f in fee_standards]
    
    if form.validate_on_submit():
        student = Student()
        form.populate_obj(student)
        
        if student.room_id == 0:
            student.room_id = None
        
        if student.fee_standard_id == 0:
            student.fee_standard_id = None
        
        if student.room_id:
            room = Room.query.get(student.room_id)
            if room:
                room.current_occupancy += 1
                if room.current_occupancy >= room.capacity:
                    room.status = 'full'
        
        student.status = 'active'
        db.session.add(student)
        db.session.commit()
        
        flash(f'学生 {student.name} 添加成功！', 'success')
        return redirect(url_for('students.index'))
    
    return render_template('students/add.html', title='添加学生', form=form)


@bp.route('/edit/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit(student_id):
    """编辑学生"""
    student = Student.query.get_or_404(student_id)
    form = StudentForm(obj=student)
    
    # 填充房间选择
    available_rooms = Room.query.filter(
        (Room.current_occupancy < Room.capacity) | (Room.id == student.room_id)
    ).all()
    form.room_id.choices = [(0, '未分配')] + [(r.id, f'{r.building}-{r.room_number} ({r.available_beds}床位)') for r in available_rooms]
    
    # 填充收费标准选择
    fee_standards = FeeStandard.query.filter_by(is_active=True).all()
    form.fee_standard_id.choices = [(0, '未选择')] + [(f.id, f'{f.name} ({f.price}/{f.unit})') for f in fee_standards]
    
    if form.validate_on_submit():
        old_room_id = student.room_id
        
        form.populate_obj(student)
        
        if student.room_id == 0:
            student.room_id = None
        
        if student.fee_standard_id == 0:
            student.fee_standard_id = None
        
        # 处理房间变更
        if old_room_id != student.room_id:
            # 退还原房间
            if old_room_id:
                old_room = Room.query.get(old_room_id)
                if old_room:
                    old_room.current_occupancy -= 1
                    if old_room.current_occupancy < old_room.capacity:
                        old_room.status = 'available'
            
            # 分配新房间
            if student.room_id:
                new_room = Room.query.get(student.room_id)
                if new_room:
                    new_room.current_occupancy += 1
                    if new_room.current_occupancy >= new_room.capacity:
                        new_room.status = 'full'
        
        db.session.commit()
        flash(f'学生 {student.name} 信息已更新！', 'success')
        return redirect(url_for('students.index'))
    
    return render_template('students/edit.html', title='编辑学生', form=form, student=student)


@bp.route('/delete/<int:student_id>', methods=['POST'])
@login_required
def delete(student_id):
    """删除学生"""
    student = Student.query.get_or_404(student_id)
    
    # 释放房间床位
    if student.room_id:
        room = Room.query.get(student.room_id)
        if room:
            room.current_occupancy -= 1
            if room.current_occupancy < room.capacity:
                room.status = 'available'
    
    db.session.delete(student)
    db.session.commit()
    
    flash(f'学生 {student.name} 已删除', 'success')
    return redirect(url_for('students.index'))


@bp.route('/detail/<int:student_id>')
@login_required
def detail(student_id):
    """学生详情"""
    student = Student.query.get_or_404(student_id)
    fee_records = FeeRecord.query.filter_by(student_id=student_id).order_by(FeeRecord.payment_date.desc()).all()
    
    return render_template('students/detail.html', title=f'{student.name} - 详情', 
                         student=student, fee_records=fee_records)


@bp.route('/batch-import', methods=['GET', 'POST'])
@login_required
def batch_import():
    """批量导入学生"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('请选择要上传的文件', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('请选择要上传的文件', 'danger')
            return redirect(request.url)
        
        if not allowed_file(file.filename):
            flash('只支持 Excel 文件 (.xlsx, .xls)', 'danger')
            return redirect(request.url)
        
        try:
            # 保存文件
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # 读取Excel
            df = pd.read_excel(filepath)
            
            # 清理列名（去除空格等）
            df.columns = df.columns.str.strip()
            
            # 验证必要列
            required_cols = ['姓名']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                flash(f'缺少必要列: {", ".join(missing_cols)}', 'danger')
                return redirect(request.url)
            
            # 导入学生
            imported = 0
            errors = []
            
            for idx, row in df.iterrows():
                try:
                    student = Student()
                    student.name = str(row.get('姓名', '')).strip()
                    
                    if not student.name:
                        errors.append(f'第{idx+2}行: 姓名为空')
                        continue
                    
                    student.student_id = str(row.get('学号', '')).strip() or None
                    student.gender = str(row.get('性别', '')).strip() or None
                    student.nationality = str(row.get('国籍', '')).strip() or None
                    student.passport_number = str(row.get('护照号码', '')).strip() or None
                    student.phone = str(row.get('手机号', '')).strip() or None
                    student.email = str(row.get('邮箱', '')).strip() or None
                    student.id_card = str(row.get('身份证号', '')).strip() or None
                    student.major = str(row.get('专业', '')).strip() or None
                    student.grade = str(row.get('年级', '')).strip() or None
                    student.notes = str(row.get('备注', '')).strip() or None
                    student.status = 'active'
                    
                    # 处理房间分配
                    room_info = str(row.get('房间号', '')).strip()
                    if room_info:
                        room = Room.query.filter(
                            (Room.building + '-' + Room.room_number == room_info) |
                            (Room.room_number == room_info)
                        ).first()
                        if room and room.is_available:
                            student.room_id = room.id
                            room.current_occupancy += 1
                            if room.current_occupancy >= room.capacity:
                                room.status = 'full'
                    
                    # 处理收费标准
                    fee_name = str(row.get('收费标准', '')).strip()
                    if fee_name:
                        fee_std = FeeStandard.query.filter(
                            (FeeStandard.name == fee_name) |
                            (FeeStandard.name.contains(fee_name))
                        ).first()
                        if fee_std:
                            student.fee_standard_id = fee_std.id
                    
                    db.session.add(student)
                    imported += 1
                    
                except Exception as e:
                    errors.append(f'第{idx+2}行: {str(e)}')
            
            db.session.commit()
            
            # 清理上传文件
            os.remove(filepath)
            
            message = f'成功导入 {imported} 名学生'
            if errors:
                message += f'，失败 {len(errors)} 条'
                flash(message, 'warning')
                # 可以返回错误详情
                for err in errors[:10]:  # 只显示前10条
                    flash(err, 'info')
            else:
                flash(message, 'success')
            
            return redirect(url_for('students.index'))
            
        except Exception as e:
            flash(f'导入失败: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('students/batch_import.html', title='批量导入学生')


@bp.route('/export-template')
@login_required
def export_template():
    """导出导入模板"""
    # 创建模板DataFrame
    template = pd.DataFrame({
        '姓名': [''],
        '学号': [''],
        '性别': ['', '男', '女'],
        '国籍': [''],
        '护照号码': [''],
        '手机号': [''],
        '邮箱': [''],
        '身份证号': [''],
        '专业': [''],
        '年级': [''],
        '房间号': [''],
        '收费标准': [''],
        '备注': ['']
    })
    
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'student_import_template.xlsx')
    template.to_excel(filepath, index=False)
    
    from flask import send_file
    return send_file(filepath, as_attachment=True, download_name='student_import_template.xlsx')


@bp.route('/<int:student_id>/fees')
@login_required
def student_fees(student_id):
    """学生缴费记录"""
    student = Student.query.get_or_404(student_id)
    fee_records = FeeRecord.query.filter_by(student_id=student_id).order_by(FeeRecord.payment_date.desc()).all()
    
    return render_template('students/student_fees.html', title=f'{student.name} - 缴费记录',
                         student=student, fee_records=fee_records)


def allowed_file(filename):
    """检查文件扩展名"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']
