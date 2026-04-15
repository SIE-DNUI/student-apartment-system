# -*- coding: utf-8 -*-
"""
学生管理路由模块
提供学生信息管理功能
"""
from flask import render_template, Blueprint, redirect, url_for, flash, request, send_file, session
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TextAreaField
from wtforms.validators import DataRequired, Optional
from wtforms.widgets import TextArea
from app.models import db
from app.models import Student, Room, FeeStandard, FeeRecord, Alert
from app.decorators import permission_required
from datetime import datetime, date, timedelta
import io

bp = Blueprint('students', __name__, url_prefix='/students')


class StudentForm(FlaskForm):
    """学生表单"""
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
    residence_permit_expiry = DateField('居留许可到期时间', format='%Y-%m-%d', validators=[Optional()])
    notes = StringField('备注', widget=TextArea(), validators=[Optional()])


@bp.route('/')
@login_required
def index():
    """学生列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    search = request.args.get('search', '')
    filter_status = request.args.get('filter', 'all')  # all, housed, unhoused
    
    # 排除已归档的学生
    query = Student.query.filter(Student.status != 'archived')
    
    if search:
        query = query.filter(
            (Student.name.contains(search)) |
            (Student.student_id.contains(search)) |
            (Student.phone.contains(search))
        )
    
    # 按住宿状态筛选
    if filter_status == 'housed':
        query = query.filter(Student.room_id != None)
    elif filter_status == 'unhoused':
        query = query.filter(Student.room_id == None)
    
    pagination = query.order_by(Student.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    students = pagination.items
    
    # 获取居留许可即将到期的学生数量（排除已归档）
    expiring_count = Student.query.filter(
        Student.status != 'archived',
        Student.residence_permit_expiry != None,
        Student.residence_permit_expiry <= date.today() + timedelta(days=30),
        Student.residence_permit_expiry >= date.today()
    ).count()
    
    return render_template('students/index.html', 
                         title='学生管理',
                         students=students,
                         pagination=pagination,
                         search=search,
                         filter_status=filter_status,
                         expiring_count=expiring_count)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
@permission_required('write')
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
@permission_required('write')
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
@permission_required('write')
def delete(id):
    """删除学生（归档，保留3年）"""
    student = Student.query.get_or_404(id)
    
    # 释放房间
    if student.room_id:
        room = Room.query.get(student.room_id)
        if room:
            room.current_occupancy -= 1
            if room.current_occupancy < room.capacity:
                room.status = 'available'
    
    # 归档学生信息
    student.status = 'archived'
    student.room_id = None
    student.deleted_at = datetime.utcnow()
    student.retention_until = date.today() + timedelta(days=365*3)  # 保留3年
    
    db.session.commit()
    flash(f'学生 {student.name} 已删除并归档，将保留至 {student.retention_until}', 'success')
    return redirect(url_for('students.index'))


@bp.route('/<int:id>/checkout', methods=['POST'])
@login_required
@permission_required('write')
def checkout(id):
    """单个学生退房"""
    student = Student.query.get_or_404(id)
    
    if not student.room_id:
        flash('该学生未入住，无需退房', 'warning')
        return redirect(url_for('students.index'))
    
    # 更新房间入住人数
    room = Room.query.get(student.room_id)
    if room:
        room.current_occupancy -= 1
        if room.current_occupancy < room.capacity:
            room.status = 'available'
    
    # 清空学生的房间信息并归档
    student.room_id = None
    student.check_out_date = date.today()
    student.status = 'archived'
    student.deleted_at = datetime.utcnow()
    student.retention_until = date.today() + timedelta(days=365*3)  # 保留3年
    
    db.session.commit()
    
    flash(f'学生 {student.name} 已退房并归档，将保留至 {student.retention_until}', 'success')
    return redirect(url_for('students.index'))


@bp.route('/batch-checkout', methods=['POST'])
@login_required
@permission_required('write')
def batch_checkout():
    """批量退房"""
    student_ids = request.form.getlist('student_ids')
    
    if not student_ids:
        flash('请选择要退房的学生', 'warning')
        return redirect(url_for('students.index'))
    
    count = 0
    for student_id in student_ids:
        student = Student.query.get(int(student_id))
        if student and student.room_id:
            # 更新房间入住人数
            room = Room.query.get(student.room_id)
            if room:
                room.current_occupancy -= 1
                if room.current_occupancy < room.capacity:
                    room.status = 'available'
            
            # 清空学生的房间信息并归档
            student.room_id = None
            student.check_out_date = date.today()
            student.status = 'archived'
            student.deleted_at = datetime.utcnow()
            student.retention_until = date.today() + timedelta(days=365*3)  # 保留3年
            count += 1
    
    db.session.commit()
    
    flash(f'已成功退房 {count} 名学生', 'success')
    return redirect(url_for('students.index'))


@bp.route('/detail/<int:id>')
@login_required
def detail(id):
    """学生详情"""
    student = Student.query.get_or_404(id)
    fee_records = FeeRecord.query.filter_by(student_id=id).order_by(FeeRecord.payment_date.desc()).all()
    
    return render_template('students/detail.html',
                         title=f'{student.name} - 详情',
                         student=student,
                         fee_records=fee_records)


@bp.route('/batch-import', methods=['GET', 'POST'])
@login_required
@permission_required('write')
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
            from openpyxl import load_workbook
            
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
                    
                    # 处理楼栋号和房间号
                    building = row_data.get('楼栋号', '')
                    room_number = row_data.get('房间号', '')
                    
                    if building and room_number:
                        # 查找对应房间
                        room = Room.query.filter_by(building=building, room_number=room_number).first()
                        if room:
                            if room.current_occupancy < room.capacity:
                                student.room_id = room.id
                                room.current_occupancy += 1
                                if room.current_occupancy >= room.capacity:
                                    room.status = 'full'
                            else:
                                # 房间已满，记录但不分配
                                pass
                    
                    # 处理收费标准
                    fee_standard_name = row_data.get('收费标准', '')
                    if fee_standard_name:
                        fee_standard = FeeStandard.query.filter_by(name=fee_standard_name, is_active=True).first()
                        if fee_standard:
                            student.fee_standard_id = fee_standard.id
                    
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
    """下载学生导入模板（带下拉菜单）"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
    
    wb = Workbook()
    ws = wb.active
    ws.title = '学生导入模板'
    
    # 表头 - 房间号拆成楼栋号和房间号两列
    headers = ['姓名', '性别', '国籍', '护照号码', '专业', '楼栋号', '房间号', '收费标准', '备注']
    
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
    ws.column_dimensions['H'].width = 15
    ws.column_dimensions['I'].width = 20
    
    # 获取所有楼栋号和房间号
    from app.models import Room
    rooms = Room.query.filter(Room.status != 'archived').all()
    
    # 楼栋号列表（去重）
    building_list = sorted(set(r.building for r in rooms if r.building))
    
    # 房间号列表
    room_number_list = sorted(set(r.room_number for r in rooms if r.room_number))
    
    # 获取所有收费标准
    from app.models import FeeStandard
    fee_standards = FeeStandard.query.filter_by(is_active=True).all()
    fee_list = [fs.name for fs in fee_standards if fs.name]
    
    # 添加楼栋号下拉菜单（F列）
    if building_list:
        building_options = ','.join(building_list)
        building_dv = DataValidation(
            type="list",
            formula1=f'"{building_options}"',
            allow_blank=True
        )
        building_dv.error = '请从下拉列表中选择楼栋号'
        building_dv.errorTitle = '无效的楼栋号'
        building_dv.prompt = '请选择楼栋号'
        building_dv.promptTitle = '楼栋号'
        ws.add_data_validation(building_dv)
        building_dv.add('F2:F1000')
    
    # 添加房间号下拉菜单（G列）
    if room_number_list:
        room_options = ','.join(room_number_list)
        room_dv = DataValidation(
            type="list",
            formula1=f'"{room_options}"',
            allow_blank=True
        )
        room_dv.error = '请从下拉列表中选择房间号'
        room_dv.errorTitle = '无效的房间号'
        room_dv.prompt = '请选择房间号'
        room_dv.promptTitle = '房间号'
        ws.add_data_validation(room_dv)
        room_dv.add('G2:G1000')
    
    # 添加收费标准下拉菜单（H列）
    if fee_list:
        fee_options = ','.join(fee_list)
        fee_dv = DataValidation(
            type="list",
            formula1=f'"{fee_options}"',
            allow_blank=True
        )
        fee_dv.error = '请从下拉列表中选择收费标准'
        fee_dv.errorTitle = '无效的收费标准'
        fee_dv.prompt = '请选择收费标准'
        fee_dv.promptTitle = '收费标准'
        ws.add_data_validation(fee_dv)
        fee_dv.add('H2:H1000')
    
    # 添加性别下拉菜单（B列）
    gender_dv = DataValidation(
        type="list",
        formula1='"男,女"',
        allow_blank=True
    )
    ws.add_data_validation(gender_dv)
    gender_dv.add('B2:B1000')
    
    # 添加示例数据
    sample_data = [
        ['张三', '男', '中国', '', '计算机科学与技术', 
         building_list[0] if building_list else '', 
         room_number_list[0] if room_number_list else '', 
         fee_list[0] if fee_list else '', ''],
        ['李四', '女', '美国', 'P1234567', '软件工程', '', '', '', ''],
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


@bp.route('/archived')
@login_required
def archived():
    """归档学生列表（已删除的学生，保留3年）"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    search = request.args.get('search', '')
    
    # 查询已归档的学生
    query = Student.query.filter(Student.status == 'archived')
    
    if search:
        query = query.filter(
            (Student.name.contains(search)) |
            (Student.student_id.contains(search)) |
            (Student.passport_number.contains(search))
        )
    
    pagination = query.order_by(Student.deleted_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    students = pagination.items
    
    return render_template('students/archived.html', 
                         title='归档学生',
                         students=students,
                         pagination=pagination,
                         search=search)
