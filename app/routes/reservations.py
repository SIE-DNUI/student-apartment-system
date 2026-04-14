from flask import render_template, Blueprint, redirect, url_for, flash, request, current_app
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Optional, NumberRange
from app import db
from app.models import Reservation, Room, Student
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename
import pandas as pd
import os

bp = Blueprint('reservations', __name__, url_prefix='/reservations')


class ReservationForm(FlaskForm):
    student_name = StringField('学生姓名', validators=[DataRequired(message='请输入学生姓名')])
    student_id = StringField('学号', validators=[Optional()])
    phone = StringField('手机号', validators=[Optional()])
    nationality = StringField('国籍', validators=[Optional()])
    gender = SelectField('性别', choices=[('男', '男'), ('女', '女'), ('', '不限')], validators=[Optional()])
    room_type = SelectField('房间类型偏好', choices=[
        ('', '不限'),
        ('双人间', '双人间'),
        ('单人间', '单人间')
    ], validators=[Optional()])
    check_in_date = DateField('计划入住日期', format='%Y-%m-%d', validators=[DataRequired(message='请选择入住日期')])
    check_out_date = DateField('计划离开日期', format='%Y-%m-%d', validators=[Optional()])
    beds_needed = IntegerField('需要床位数', validators=[DataRequired(), NumberRange(min=1, max=10)])
    notes = StringField('备注', validators=[Optional()])


@bp.route('/')
@login_required
def index():
    """入住计划列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    status_filter = request.args.get('status', '')
    date_filter = request.args.get('date', '')
    
    query = Reservation.query
    
    if status_filter:
        query = query.filter(Reservation.status == status_filter)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Reservation.check_in_date == filter_date)
        except:
            pass
    
    pagination = query.order_by(Reservation.check_in_date).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    reservations = pagination.items
    
    return render_template('reservations/index.html', title='入住计划',
                         reservations=reservations, pagination=pagination,
                         status_filter=status_filter, date_filter=date_filter)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加入住计划"""
    form = ReservationForm()
    
    if form.validate_on_submit():
        reservation = Reservation()
        form.populate_obj(reservation)
        
        if reservation.check_out_date and reservation.check_in_date:
            duration = (reservation.check_out_date - reservation.check_in_date).days
            reservation.duration_days = duration
        
        reservation.status = 'pending'
        db.session.add(reservation)
        db.session.commit()
        
        flash(f'入住计划已添加！', 'success')
        return redirect(url_for('reservations.index'))
    
    return render_template('reservations/add.html', title='添加入住计划', form=form)


@bp.route('/edit/<int:reservation_id>', methods=['GET', 'POST'])
@login_required
def edit(reservation_id):
    """编辑入住计划"""
    reservation = Reservation.query.get_or_404(reservation_id)
    form = ReservationForm(obj=reservation)
    
    if form.validate_on_submit():
        form.populate_obj(reservation)
        
        if reservation.check_out_date and reservation.check_in_date:
            duration = (reservation.check_out_date - reservation.check_in_date).days
            reservation.duration_days = duration
        
        db.session.commit()
        
        flash('入住计划已更新！', 'success')
        return redirect(url_for('reservations.index'))
    
    return render_template('reservations/edit.html', title='编辑入住计划', form=form, reservation=reservation)


@bp.route('/delete/<int:reservation_id>', methods=['POST'])
@login_required
def delete(reservation_id):
    """删除入住计划"""
    reservation = Reservation.query.get_or_404(reservation_id)
    
    db.session.delete(reservation)
    db.session.commit()
    
    flash('入住计划已删除', 'success')
    return redirect(url_for('reservations.index'))


@bp.route('/confirm/<int:reservation_id>', methods=['POST'])
@login_required
def confirm(reservation_id):
    """确认入住计划"""
    reservation = Reservation.query.get_or_404(reservation_id)
    
    # 查找可用房间
    available_rooms = Room.query.filter(
        Room.current_occupancy < Room.capacity,
        Room.status != 'maintenance'
    ).all()
    
    # 按需要的床位数筛选
    suitable_rooms = [r for r in available_rooms if r.available_beds >= reservation.beds_needed]
    
    if not suitable_rooms:
        flash('暂无足够的空房间！', 'danger')
        return redirect(url_for('reservations.index'))
    
    # 自动分配第一个合适的房间
    room = suitable_rooms[0]
    room.current_occupancy += reservation.beds_needed
    if room.current_occupancy >= room.capacity:
        room.status = 'full'
    
    # 创建学生记录
    student = Student(
        name=reservation.student_name,
        student_id=reservation.student_id,
        phone=reservation.phone,
        nationality=reservation.nationality,
        gender=reservation.gender,
        room_id=room.id,
        check_in_date=reservation.check_in_date,
        check_out_date=reservation.check_out_date,
        status='active'
    )
    
    db.session.add(student)
    reservation.status = 'confirmed'
    db.session.commit()
    
    flash(f'已确认入住，分配房间: {room.building}-{room.room_number}，学生ID: {student.id}', 'success')
    return redirect(url_for('reservations.index'))


@bp.route('/cancel/<int:reservation_id>', methods=['POST'])
@login_required
def cancel(reservation_id):
    """取消入住计划"""
    reservation = Reservation.query.get_or_404(reservation_id)
    reservation.status = 'cancelled'
    db.session.commit()
    
    flash('入住计划已取消', 'info')
    return redirect(url_for('reservations.index'))


# ==================== 房间预判功能 ====================

@bp.route('/forecast', methods=['GET', 'POST'])
@login_required
def forecast():
    """房间预判 - 预测某天房间是否够用"""
    target_date = None
    beds_needed = 1
    forecast_result = None
    
    if request.method == 'POST':
        try:
            target_date = datetime.strptime(request.form.get('target_date'), '%Y-%m-%d').date()
        except:
            target_date = date.today()
        
        beds_needed = int(request.form.get('beds_needed', 1))
        forecast_result = predict_room_availability(target_date, beds_needed)
    
    return render_template('reservations/forecast.html', title='房间预判',
                         target_date=target_date, beds_needed=beds_needed, forecast_result=forecast_result)


def predict_room_availability(target_date, beds_needed=1):
    """
    预测指定日期的房间可用情况
    
    考虑因素：
    1. 当前已入住的学生
    2. 计划在当天入住的学生
    3. 计划在当天离开的学生
    4. 某天之前入住但还未离开的学生（持续占用）
    """
    total_beds = db.session.query(db.func.sum(Room.capacity)).scalar() or 0
    total_rooms = Room.query.count()
    
    # 计算当天计划入住人数
    checkin_reservations = Reservation.query.filter(
        Reservation.check_in_date == target_date,
        Reservation.status == 'pending'
    ).all()
    checkin_count = sum(r.beds_needed for r in checkin_reservations)
    
    # 计算当天计划离开人数
    checkout_students = Student.query.filter(
        Student.check_out_date == target_date,
        Student.status == 'active'
    ).all()
    checkout_count = len(checkout_students)
    
    # 计算当天及之前的净入住学生数
    # 已入住且未在当天离开的学生
    current_occupied = db.session.query(db.func.sum(Room.current_occupancy)).scalar() or 0
    
    # 计算当天需要净增床位数
    net_beds_needed = checkin_count - checkout_count + beds_needed
    
    # 可用床位数
    available_beds = total_beds - current_occupied + checkout_count
    
    result = {
        'target_date': target_date,
        'beds_needed': beds_needed,
        'total_beds': total_beds,
        'total_rooms': total_rooms,
        'current_occupied': current_occupied,
        'available_beds': available_beds,
        'checkin_count': checkin_count,
        'checkout_count': checkout_count,
        'net_beds_needed': net_beds_needed,
        'is_sufficient': available_beds >= net_beds_needed,
        'shortage': max(0, net_beds_needed - available_beds),
        'checkin_reservations': checkin_reservations,
        'checkout_students': checkout_students
    }
    
    return result


@bp.route('/batch-import', methods=['GET', 'POST'])
@login_required
def batch_import():
    """批量导入入住计划"""
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
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            df = pd.read_excel(filepath)
            df.columns = df.columns.str.strip()
            
            required_cols = ['学生姓名', '计划入住日期']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                flash(f'缺少必要列: {", ".join(missing_cols)}', 'danger')
                return redirect(request.url)
            
            imported = 0
            errors = []
            
            for idx, row in df.iterrows():
                try:
                    student_name = str(row.get('学生姓名', '')).strip()
                    if not student_name:
                        errors.append(f'第{idx+2}行: 学生姓名为空')
                        continue
                    
                    check_in_date = row.get('计划入住日期', '')
                    if isinstance(check_in_date, str):
                        check_in_date = datetime.strptime(check_in_date, '%Y-%m-%d').date()
                    elif hasattr(check_in_date, 'date'):
                        check_in_date = check_in_date.date()
                    else:
                        check_in_date = date.today()
                    
                    check_out_date = row.get('计划离开日期', '')
                    if pd.notna(check_out_date) and check_out_date:
                        if isinstance(check_out_date, str):
                            check_out_date = datetime.strptime(check_out_date, '%Y-%m-%d').date()
                        elif hasattr(check_out_date, 'date'):
                            check_out_date = check_out_date.date()
                        else:
                            check_out_date = None
                    else:
                        check_out_date = None
                    
                    reservation = Reservation(
                        student_name=student_name,
                        student_id=str(row.get('学号', '')).strip() or None,
                        phone=str(row.get('手机号', '')).strip() or None,
                        nationality=str(row.get('国籍', '')).strip() or None,
                        gender=str(row.get('性别', '')).strip() or None,
                        room_type=str(row.get('房间类型', '')).strip() or None,
                        check_in_date=check_in_date,
                        check_out_date=check_out_date,
                        beds_needed=int(row.get('床位数', 1)),
                        notes=str(row.get('备注', '')).strip() or None,
                        status='pending'
                    )
                    
                    if reservation.check_out_date and reservation.check_in_date:
                        reservation.duration_days = (reservation.check_out_date - reservation.check_in_date).days
                    
                    db.session.add(reservation)
                    imported += 1
                    
                except Exception as e:
                    errors.append(f'第{idx+2}行: {str(e)}')
            
            db.session.commit()
            os.remove(filepath)
            
            message = f'成功导入 {imported} 条入住计划'
            if errors:
                message += f'，失败 {len(errors)} 条'
                flash(message, 'warning')
                for err in errors[:10]:
                    flash(err, 'info')
            else:
                flash(message, 'success')
            
            return redirect(url_for('reservations.index'))
            
        except Exception as e:
            flash(f'导入失败: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('reservations/batch_import.html', title='批量导入入住计划')


@bp.route('/export-template')
@login_required
def export_template():
    """导出入住计划导入模板"""
    template = pd.DataFrame({
        '学生姓名': [''],
        '学号': [''],
        '手机号': [''],
        '国籍': [''],
        '性别': ['', '男', '女'],
        '计划入住日期': [date.today().strftime('%Y-%m-%d')],
        '计划离开日期': [(date.today() + timedelta(days=120)).strftime('%Y-%m-%d')],
        '床位数': [1],
        '备注': ['']
    })
    
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'reservation_template.xlsx')
    template.to_excel(filepath, index=False)
    
    from flask import send_file
    return send_file(filepath, as_attachment=True, download_name='reservation_template.xlsx')


@bp.route('/calendar')
@login_required
def calendar():
    """入住计划日历视图"""
    # 获取最近3个月的入住计划
    today = date.today()
    start_date = today - timedelta(days=30)
    end_date = today + timedelta(days=90)
    
    reservations = Reservation.query.filter(
        Reservation.check_in_date >= start_date,
        Reservation.check_in_date <= end_date
    ).order_by(Reservation.check_in_date).all()
    
    # 按日期分组
    events = []
    for r in reservations:
        events.append({
            'id': r.id,
            'title': f'{r.student_name}入住',
            'date': r.check_in_date,
            'beds': r.beds_needed,
            'status': r.status,
            'nationality': r.nationality or ''
        })
        
        if r.check_out_date:
            events.append({
                'id': r.id,
                'title': f'{r.student_name}退房',
                'date': r.check_out_date,
                'beds': -r.beds_needed,
                'status': r.status,
                'nationality': r.nationality or ''
            })
    
    return render_template('reservations/calendar.html', title='入住计划日历',
                         events=events, today=today)


def allowed_file(filename):
    """检查文件扩展名"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']
