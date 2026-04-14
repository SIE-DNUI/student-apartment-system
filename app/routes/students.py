from flask import render_template, Blueprint, redirect, url_for, flash, request, current_app, send_file
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TextAreaField
from wtforms.validators import DataRequired, Optional
from wtforms.widgets import TextArea
from app.models import db
from app.models import Student, Room, FeeStandard, FeeRecord, Alert
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
import os
import io

bp = Blueprint('students', __name__, url_prefix='/students')


class StudentForm(FlaskForm):
    name = StringField('姓名', validators=[DataRequired(message='请输入姓名')])
    gender = SelectField('性别', choices=[('男', '男'), ('女', '女'), ('其他', '其他')], validators=[Optional()])
    nationality = StringField('国籍', validators=[Optional()])
    passport_number = StringField('护照号码', validators=[Optional()])
    major = StringField('专业', validators=[Optional()])
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
    
    available_rooms = Room.query.filter(Room.current_occupancy < Room.capacity).all()
    form.room_id.choices = [(0, '未分配')] + [(r.id, f'{r.building}-{r.room_number}') for r in available_rooms]
    
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
        
        flash('学生添加成功！', 'success')
        return redirect(url_for('students.index'))
    
    return render_template('students/add.html', title='添加学生', form=form)


@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """编辑学生"""
    student = Student.query.get_or_404(id)
    form = StudentForm(obj=student)
    
    available_rooms = Room.query.filter(
        (Room.current_occupancy < Room.capacity) | (Room.id == student.room_id)
    ).all()
    form.room_id.choices = [(0, '未分配')] + [(r.id, f'{r.building}-{r.room_number}') for r in available_rooms]
    
    fee_standards = FeeStandard.query.filter_by(is_active=True).all()
    form.fee_standard_id.choices = [(0, '未选择')] + [(f.id, f'{f.name} ({f.price}/{f.unit})') for f in fee_standards]
    
    if form.validate_on_submit():
        old_room_id = student.room_id
        
        form.populate_obj(student)
        
        if student.room_id == 0:
            student.room_id = None
        
        if student.fee_standard_id == 0:
            student.fee_standard_id = None
        
        if old_room_id != student.room_id:
            if old_room_id:
                old_room = Room.query.get(old_room_id)
                if old_room:
                    old_room.current_occupancy -= 1
                    old_room.status = 'available'
            
            if student.room_id:
                new_room = Room.query.get(student.room_id)
                if new_room:
                    new_room.current_occupancy += 1
                    if new_room.current_occupancy >= new_room.capacity:
                        new_room.status = 'full'
        
        db.session.commit()
        flash('学生信息更新成功！', 'success')
        return redirect(url_for('students.index'))
    
    return render_template('students/edit.html', title='编辑学生', form=form, student=student)


@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """删除学生（归档）"""
    student = Student.query.get_or_404(id)
    student.status = 'archived'
    student.actual_leave_date = date.today()
    
    if student.room_id:
        room = Room.query.get(student.room_id)
        if room:
            room.current_occupancy -= 1
            room.status = 'available'
    
    db.session.commit()
    flash('学生已归档！', 'success')
    return redirect(url_for('students.index'))


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
        
        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('只支持 Excel 文件 (.xlsx, .xls)', 'danger')
            return redirect(request.url)
        
        try:
            wb = load_workbook(file)
            ws = wb.active
            
            headers = [cell.value for cell in ws[1] if cell.value]
            
            success_count = 0
            error_count = 0
            
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row[0]:
                    continue
                
                row_data = dict(zip(headers, row))
                
                try:
                    student = Student()
                    student.name = row_data.get('姓名', '')
                    student.gender = row_data.get('性别', '')
                    student.nationality = row_data.get('国籍', '')
                    student.passport_number = row_data.get('护照号码', '')
                    student.major = row_data.get('专业', '')
                    
                    if row_data.get('入住日期'):
                        if isinstance(row_data['入住日期'], date):
                            student.check_in_date = row_data['入住日期']
                        else:
                            student.check_in_date = datetime.strptime(str(row_data['入住日期']), '%Y-%m-%d').date()
                    
                    if row_data.get('预计离开日期'):
                        if isinstance(row_data['预计离开日期'], date):
                            student.check_out_date = row_data['预计离开日期']
                        else:
                            student.check_out_date = datetime.strptime(str(row_data['预计离开日期']), '%Y-%m-%d').date()
                    
                    student.notes = row_data.get('备注', '')
                    student.status = 'active'
                    
                    db.session.add(student)
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    continue
            
            db.session.commit()
            flash(f'导入完成！成功: {success_count} 条，失败: {error_count} 条', 'success')
            return redirect(url_for('students.index'))
            
        except Exception as e:
            flash(f'导入失败: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('students/batch_import.html', title='批量导入学生')


@bp.route('/<int:id>/fees')
@login_required
def student_fees(id):
    """学生缴费记录"""
    student = Student.query.get_or_404(id)
    fee_records = FeeRecord.query.filter_by(student_id=id).order_by(FeeRecord.payment_date.desc()).all()
    
    return render_template('students/student_fees.html', 
                         title=f'{student.name} - 缴费记录',
                         student=student,
                         fee_records=fee_records)


@bp.route('/export-template')
@login_required
def export_template():
    """下载学生导入模板"""
    wb = Workbook()
    ws = wb.active
    ws.title = '学生导入模板'
    
    # 表头
    headers = ['姓名', '性别', '国籍', '护照号码', '专业', '房间号', '收费标准', '备注']
    
    # 设置表头样式
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
    
    # 设置列宽
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 8
    ws.column_dimensions['C'].width = 10
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 12
    ws.column_dimensions['G'].width = 12
    ws.column_dimensions['H'].width = 20
    
    # 添加示例数据
    sample_data = [
        ['张三', '男', '中国', '', '计算机科学与技术', '1-101', '标准双人间', ''],
        ['李四', '女', '美国', 'P1234567', '软件工程', '', '', ''],
    ]
    
    for row_idx, row_data in enumerate(sample_data, 2):
        for col_idx, value in enumerate(row_data, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)
    
    # 保存到内存
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='学生导入模板.xlsx'
    )
