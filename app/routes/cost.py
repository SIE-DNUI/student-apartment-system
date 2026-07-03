# -*- coding: utf-8 -*-
"""
成本与回款路由模块
提供成本与回款相关功能
"""
from flask import render_template, Blueprint, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from app.models import db, MonthlyRent
from app.utils import cost_calculator
from app.decorators import permission_required

bp = Blueprint('cost', __name__, url_prefix='/cost')


@bp.route('/')
@login_required
def index():
    """成本与回款页面"""
    # 获取统计指标
    summary = cost_calculator.get_summary_data()
    
    # 获取部门统计数据
    dept_stats = cost_calculator.get_all_department_stats()
    
    # 获取当前年份和月份信息
    time_info = cost_calculator.get_current_time_info()
    
    # 获取已录入的房租记录
    monthly_rents = MonthlyRent.query.filter_by(
        year=time_info['current_year']
    ).order_by(MonthlyRent.month).all()
    
    return render_template(
        'cost/index.html',
        title='成本与回款',
        summary=summary,
        dept_stats=dept_stats,
        time_info=time_info,
        monthly_rents=monthly_rents
    )


@bp.route('/rent', methods=['POST'])
@login_required
@permission_required('write')
def save_rent():
    """保存每月房租"""
    year = request.form.get('year', type=int)
    month = request.form.get('month', type=int)
    amount = request.form.get('amount', type=float)
    
    if not all([year, month, amount is not None]):
        flash('请填写完整的房租信息', 'danger')
        return redirect(url_for('cost.index'))
    
    if month < 1 or month > 12:
        flash('月份必须在1-12之间', 'danger')
        return redirect(url_for('cost.index'))
    
    if amount < 0:
        flash('房租金额不能为负数', 'danger')
        return redirect(url_for('cost.index'))
    
    # 查找或创建记录
    rent = MonthlyRent.query.filter_by(year=year, month=month).first()
    
    if rent:
        rent.amount = amount
        flash(f'{year}年{month}月房租已更新为 {amount:.2f}', 'success')
    else:
        rent = MonthlyRent(year=year, month=month, amount=amount)
        db.session.add(rent)
        flash(f'{year}年{month}月房租 {amount:.2f} 已保存', 'success')
    
    db.session.commit()
    return redirect(url_for('cost.index'))


@bp.route('/rent/api/<int:year>/<int:month>', methods=['GET'])
@login_required
def get_rent(year, month):
    """获取指定月份的房租（API）"""
    rent = MonthlyRent.query.filter_by(year=year, month=month).first()
    
    if rent:
        return jsonify({
            'success': True,
            'amount': rent.amount
        })
    else:
        return jsonify({
            'success': False,
            'amount': 0
        })


@bp.route('/rent/list', methods=['GET'])
@login_required
def list_rents():
    """获取今年所有月份的房租列表"""
    time_info = cost_calculator.get_current_time_info()
    year = time_info['current_year']
    
    rents = MonthlyRent.query.filter_by(year=year).order_by(MonthlyRent.month).all()
    
    rent_dict = {}
    for rent in rents:
        rent_dict[rent.month] = rent.amount
    
    return jsonify({
        'success': True,
        'year': year,
        'rents': rent_dict
    })
