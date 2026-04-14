from flask import render_template, Blueprint, redirect, url_for, flash, request, current_app
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Optional, NumberRange
from app import db
from app.models import Room, FeeStandard, Student
from datetime import datetime
from werkzeug.utils import secure_filename
import pandas as pd
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
    
    # 获取所有楼栋
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
    
    # 填充收费标准选择
    fee_standards = FeeStandard.query.filter_by(is_active=True).all()
    form.fee_standard_id.choices = [(0, '未选择')] + [(f.id, f'{f.name} ({f.price}/{f.unit})') for f in fee_standards]
    
    if form.validate_on_submit():
        # 检查房间是否已存在
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
    
    # 填充收费标准选择
    fee_standards = FeeStandard.query.filter_by(is_active=True).all()
    form.fee_standard_id.choices = [(0, '未选择')] + [(f.id, f'{f.name} ({f.price}/{f.unit})') for f in fee_standards]
    
    if form.validate_on_submit():
        # 检查房间是否已存在（排除自己）
        existing = Room.query.filter(
            Room.building == form.building.data,
            Room.room_number == form.room_number.data,
            Room.id != room_id
        ).first()
        
        if existing:
            flash(f'房间 {form.building.data}-{form.room_number.data} 已存在', 'danger')
            return redirect(url_for('rooms.edit', room_id=room_id))
        
        # 记录旧容量
        old_capacity = room.capacity
        
        form.populate_obj(room)
        
        if room.fee_standard_id == 0:
            room.fee_standard_id = None
        
        # 如果容量变更
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
            df.columns = df.columns.str.strip()
            
            # 验证必要列
            required_cols = ['楼号', '房间号', '容量']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                flash(f'缺少必要列: {", ".join(missing_cols)}', 'danger')
                return redirect(request.url)
            
            # 导入房间
            imported = 0
            skipped = 0
            errors = []
            
            for idx, row in df.iterrows():
                try:
                    building = str(row.get('楼号', '')).strip()
                    room_number = str(row.get('房间号', '')).strip()
                    capacity = int(row.get('容量', 2))
                    floor = int(row.get('楼层', 1)) if pd.notna(row.get('楼层')) else None
                    
                    if not building or not room_number:
                        errors.append(f'第{idx+2}行: 楼号或房间号为空')
                        continue
                    
                    # 检查是否已存在
                    existing = Room.query.filter_by(building=building, room_number=room_number).first()
                    if existing:
                        skipped += 1
                        continue
                    
                    room = Room(
                        building=building,
                        room_number=room_number,
                        capacity=capacity,
                        floor=floor,
                        status='available'
                    )
                    
                    # 收费标准
                    fee_name = str(row.get('收费标准', '')).strip()
                    if fee_name:
                        fee_std = FeeStandard.query.filter(
                            (FeeStandard.name == fee_name) |
                            (FeeStandard.name.contains(fee_name))
                        ).first()
                        if fee_std:
                            room.fee_standard_id = fee_std.id
                    
                    db.session.add(room)
                    imported += 1
                    
                except Exception as e:
                    errors.append(f'第{idx+2}行: {str(e)}')
            
            db.session.commit()
            os.remove(filepath)
            
            message = f'成功添加 {imported} 个房间'
            if skipped > 0:
                message += f'，跳过 {skipped} 个已存在的房间'
            if errors:
                message += f'，失败 {len(errors)} 条'
                flash(message, 'warning')
                for err in errors[:10]:
                    flash(err, 'info')
            else:
                flash(message, 'success')
            
            return redirect(url_for('rooms.index'))
            
        except Exception as e:
            flash(f'导入失败: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('rooms/batch_add.html', title='批量添加房间')


@bp.route('/batch-edit', methods=['GET', 'POST'])
@login_required
def batch_edit():
    """批量编辑房间"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update':
            # 批量更新操作
            room_ids = request.form.getlist('room_ids')
            update_field = request.form.get('update_field')
            update_value = request.form.get('update_value')
            
            if not room_ids:
                flash('请选择要更新的房间', 'danger')
                return redirect(url_for('rooms.batch_edit'))
            
            rooms = Room.query.filter(Room.id.in_(room_ids)).all()
            
            for room in rooms:
                if update_field == 'building':
                    room.building = update_value
                elif update_field == 'fee_standard_id':
                    if update_value:
                        room.fee_standard_id = int(update_value)
                elif update_field == 'capacity':
                    new_capacity = int(update_value)
                    if new_capacity < room.current_occupancy:
                        flash(f'房间 {room.building}-{room.room_number} 入住人数大于新容量，跳过', 'warning')
                        continue
                    room.capacity = new_capacity
                    if room.current_occupancy >= room.capacity:
                        room.status = 'full'
                    else:
                        room.status = 'available'
            
            db.session.commit()
            flash(f'已更新 {len(rooms)} 个房间', 'success')
            return redirect(url_for('rooms.index'))
        
        elif action == 'quick':
            # 快速批量设置
            building_prefix = request.form.get('building_prefix', '').strip()
            start_room = request.form.get('start_room', '').strip()
            end_room = request.form.get('end_room', '').strip()
            capacity = request.form.get('quick_capacity', 2, type=int)
            floor = request.form.get('quick_floor', type=int)
            fee_standard_id = request.form.get('quick_fee_standard_id', type=int)
            
            if building_prefix and start_room and end_room:
                try:
                    # 生成房间号范围
                    start_num = int(''.join(filter(str.isdigit, start_room))) or 1
                    end_num = int(''.join(filter(str.isdigit, end_room))) or start_num
                    prefix = ''.join(filter(str.isalpha, start_room))
                    
                    rooms_added = 0
                    for num in range(start_num, end_num + 1):
                        room_number = f'{prefix}{num}'
                        existing = Room.query.filter_by(
                            building=building_prefix, 
                            room_number=room_number
                        ).first()
                        
                        if not existing:
                            room = Room(
                                building=building_prefix,
                                room_number=room_number,
                                capacity=capacity,
                                floor=floor,
                                status='available'
                            )
                            if fee_standard_id:
                                room.fee_standard_id = fee_standard_id
                            db.session.add(room)
                            rooms_added += 1
                    
                    db.session.commit()
                    flash(f'成功创建 {rooms_added} 个房间', 'success')
                    return redirect(url_for('rooms.index'))
                    
                except Exception as e:
                    flash(f'操作失败: {str(e)}', 'danger')
    
    # 获取所有房间（用于选择）
    rooms = Room.query.order_by(Room.building, Room.room_number).all()
    buildings = db.session.query(Room.building).distinct().all()
    buildings = [b[0] for b in buildings]
    
    fee_standards = FeeStandard.query.filter_by(is_active=True).all()
    
    return render_template('rooms/batch_edit.html', title='批量编辑房间',
                         rooms=rooms, buildings=buildings, fee_standards=fee_standards)


@bp.route('/export-template')
@login_required
def export_template():
    """导出房间导入模板"""
    template = pd.DataFrame({
        '楼号': [''],
        '房间号': [''],
        '容量': [2],
        '楼层': [1],
        '收费标准': ['']
    })
    
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'room_import_template.xlsx')
    template.to_excel(filepath, index=False)
    
    from flask import send_file
    return send_file(filepath, as_attachment=True, download_name='room_import_template.xlsx')


@bp.route('/status')
@login_required
def status():
    """房间状态统计"""
    from sqlalchemy import func
    
    # 按楼栋统计
    building_stats = db.session.query(
        Room.building,
        func.count(Room.id).label('total'),
        func.sum(Room.capacity).label('total_capacity'),
        func.sum(Room.current_occupancy).label('total_occupancy'),
        func.sum(db.case((Room.current_occupancy < Room.capacity, 1), else_=0)).label('available')
    ).group_by(Room.building).all()
    
    # 总体统计
    total_rooms = Room.query.count()
    total_capacity = db.session.query(func.sum(Room.capacity)).scalar() or 0
    total_occupancy = db.session.query(func.sum(Room.current_occupancy)).scalar() or 0
    
    return render_template('rooms/status.html', title='房间状态统计',
                         building_stats=building_stats,
                         total_rooms=total_rooms,
                         total_capacity=total_capacity,
                         total_occupancy=total_occupancy)


def allowed_file(filename):
    """检查文件扩展名"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']
