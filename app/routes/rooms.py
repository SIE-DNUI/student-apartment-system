from flask import render_template, Blueprint, redirect, url_for, flash, request, current_app
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Optional, NumberRange
from app.models import db
from app.models import Room, FeeStandard, Student
from datetime import datetime
from werkzeug.utils import secure_filename
from openpyxl import load_workbook
import os

bp = Blueprint('rooms', __name__, url_prefix='/rooms')


class RoomForm(FlaskForm):
    building = StringField('楼号', validators=[DataRequired(message='请输入楼号')])
    room_number = StringField('房间号', validators=[DataRequired(message='请输入房间号')])
    capacity = IntegerField('房间容量', validators=[DataRequired(), NumberRange(min=1, max=10)])
    floor = IntegerField('楼层', validators=[Optional()])
    fee_standard_id = SelectField('收费标准', coerce=int, validators=[Optional()])
    description = StringField('备注', validators=[Optional()])


@bp.route('/')
@login_required
def index():
    """房间列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 30
    
    building_filter = request.args.get('building', '')
    status_filter = request.args.get('status', '')
    
    query = Room.query
    
    if building_filter:
        query = query.filter(Room.building == building_filter)
    
    if status_filter:
        if status_filter == 'available':
            query = query.filter(Room.current_occupancy < Room.capacity)
        elif status_filter == 'full':
            query = query.filter(Room.current_occupancy >= Room.capacity)
    
    pagination = query.order_by(Room.building, Room.room_number).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    rooms = pagination.items
    
    buildings = db.session.query(Room.building).distinct().all()
    buildings = [b[0] for b in buildings]
    
    return render_template('rooms/index.html',
                         title='房间管理',
                         rooms=rooms,
                         pagination=pagination,
                         buildings=buildings,
                         building_filter=building_filter,
                         status_filter=status_filter)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加房间"""
    form = RoomForm()
    
    fee_standards = FeeStandard.query.filter_by(is_active=True).all()
    form.fee_standard_id.choices = [(0, '未选择')] + [(f.id, f'{f.name} ({f.price}/{f.unit})') for f in fee_standards]
    
    if form.validate_on_submit():
        existing = Room.query.filter_by(
            building=form.building.data,
            room_number=form.room_number.data
        ).first()
        
        if existing:
            flash(f'房间 {form.building}-{form.room_number} 已存在', 'danger')
            return redirect(url_for('rooms.add'))
        
        room = Room()
        form.populate_obj(room)
        
        if room.fee_standard_id == 0:
            room.fee_standard_id = None
        
        room.status = 'available'
        db.session.add(room)
        db.session.commit()
        
        flash(f'房间 {room.building}-{room.room_number} 添加成功！', 'success')
        return redirect(url_for('rooms.index'))
    
    return render_template('rooms/add.html', title='添加房间', form=form)


@bp.route('/edit/<int:room_id>', methods=['GET', 'POST'])
@login_required
def edit(room_id):
    """编辑房间"""
    room = Room.query.get_or_404(room_id)
    form = RoomForm(obj=room)
    
    fee_standards = FeeStandard.query.filter_by(is_active=True).all()
    form.fee_standard_id.choices = [(0, '未选择')] + [(f.id, f'{f.name} ({f.price}/{f.unit})') for f in fee_standards]
    
    if form.validate_on_submit():
        existing = Room.query.filter(
            Room.building == form.building.data,
            Room.room_number == form.room_number.data,
            Room.id != room_id
        ).first()
        
        if existing:
            flash(f'房间 {form.building.data}-{form.room_number.data} 已存在', 'danger')
            return redirect(url_for('rooms.edit', room_id=room_id))
        
        old_capacity = room.capacity
        
        form.populate_obj(room)
        
        if room.fee_standard_id == 0:
            room.fee_standard_id = None
        
        if old_capacity != room.capacity:
            room.current_occupancy = min(room.current_occupancy, room.capacity)
            if room.current_occupancy >= room.capacity:
                room.status = 'full'
            else:
                room.status = 'available'
        
        db.session.commit()
        flash(f'房间 {room.building}-{room.room_number} 信息已更新！', 'success')
        return redirect(url_for('rooms.index'))
    
    return render_template('rooms/edit.html', title='编辑房间', form=form, room=room)


@bp.route('/delete/<int:room_id>', methods=['POST'])
@login_required
def delete(room_id):
    """删除房间"""
    room = Room.query.get_or_404(room_id)
    
    if room.current_occupancy > 0:
        flash(f'房间 {room.building}-{room.room_number} 仍有学生入住，无法删除', 'danger')
        return redirect(url_for('rooms.index'))
    
    db.session.delete(room)
    db.session.commit()
    
    flash(f'房间 {room.building}-{room.room_number} 已删除', 'success')
    return redirect(url_for('rooms.index'))


@bp.route('/detail/<int:room_id>')
@login_required
def detail(room_id):
    """房间详情"""
    room = Room.query.get_or_404(room_id)
    students = Student.query.filter_by(room_id=room_id, status='active').all()
    
    return render_template('rooms/detail.html', title=f'{room.building}-{room.room_number}',
                         room=room, students=students)


@bp.route('/batch-add', methods=['GET', 'POST'])
@login_required
def batch_add():
    """批量添加房间"""
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
            skip_count = 0
            error_count = 0
            
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row[0]:
                    continue
                
                row_data = dict(zip(headers, row))
                
                try:
                    building = str(row_data.get('楼号', '')).strip()
                    room_number = str(row_data.get('房间号', '')).strip()
                    capacity = int(row_data.get('容量', 2))
                    floor = row_data.get('楼层')
                    
                    if not building or not room_number:
                        error_count += 1
                        continue
                    
                    existing = Room.query.filter_by(building=building, room_number=room_number).first()
                    if existing:
                        skip_count += 1
                        continue
                    
                    room = Room(
                        building=building,
                        room_number=room_number,
                        capacity=capacity,
                        floor=floor,
                        status='available'
                    )
                    
                    fee_name = str(row_data.get('收费标准', '')).strip()
                    if fee_name:
                        fee_std = FeeStandard.query.filter(
                            (FeeStandard.name == fee_name) |
                            (FeeStandard.name.contains(fee_name))
                        ).first()
                        if fee_std:
                            room.fee_standard_id = fee_std.id
                    
                    db.session.add(room)
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    continue
            
            db.session.commit()
            flash(f'导入完成！成功: {success_count}, 跳过(已存在): {skip_count}, 失败: {error_count}', 'success')
            return redirect(url_for('rooms.index'))
            
        except Exception as e:
            flash(f'导入失败: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('rooms/batch_add.html', title='批量添加房间')


@bp.route('/batch-edit', methods=['GET', 'POST'])
@login_required
def batch_edit():
    """批量修改房间"""
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
                    building = str(row_data.get('楼号', '')).strip()
                    room_number = str(row_data.get('房间号', '')).strip()
                    
                    room = Room.query.filter_by(building=building, room_number=room_number).first()
                    if not room:
                        error_count += 1
                        continue
                    
                    if row_data.get('新房间号'):
                        room.room_number = str(row_data['新房间号']).strip()
                    if row_data.get('容量'):
                        room.capacity = int(row_data['容量'])
                    if row_data.get('楼层'):
                        room.floor = int(row_data['楼层'])
                    if row_data.get('备注'):
                        room.description = str(row_data['备注'])
                    
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    continue
            
            db.session.commit()
            flash(f'修改完成！成功: {success_count}, 失败: {error_count}', 'success')
            return redirect(url_for('rooms.index'))
            
        except Exception as e:
            flash(f'修改失败: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('rooms/batch_edit.html', title='批量修改房间')


@bp.route('/status')
@login_required
def status():
    """房间状态统计"""
    total_rooms = Room.query.count()
    total_capacity = db.session.query(db.func.sum(Room.capacity)).scalar() or 0
    total_occupancy = db.session.query(db.func.sum(Room.current_occupancy)).scalar() or 0
    
    available_rooms = Room.query.filter(Room.current_occupancy < Room.capacity).count()
    full_rooms = Room.query.filter(Room.current_occupancy >= Room.capacity).count()
    
    buildings = db.session.query(
        Room.building,
        db.func.count(Room.id).label('room_count'),
        db.func.sum(Room.capacity).label('total_capacity'),
        db.func.sum(Room.current_occupancy).label('current_occupancy')
    ).group_by(Room.building).all()
    
    return render_template('rooms/status.html',
                         title='房间状态',
                         total_rooms=total_rooms,
                         total_capacity=total_capacity,
                         total_occupancy=total_occupancy,
                         available_rooms=available_rooms,
                         full_rooms=full_rooms,
                         buildings=buildings)
