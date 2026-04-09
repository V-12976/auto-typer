# tests/test_speed_controller.py
import pytest
from auto_typewriter import SpeedController


def test_fixed_speed_mode():
    """固定速度模式返回常量间隔"""
    controller = SpeedController(mode='fixed', fixed_speed=10)
    interval = controller.get_interval()
    assert interval == 0.1  # 1/10 = 0.1秒


def test_random_speed_mode_within_range():
    """随机速度模式返回在范围内的间隔"""
    controller = SpeedController(mode='random', min_speed=5, max_speed=15)
    for _ in range(100):  # 多次测试确保范围正确
        interval = controller.get_interval()
        assert 0.0667 <= interval <= 0.2  # 1/15≈0.067, 1/5=0.2


def test_fixed_speed_boundary():
    """固定速度边界值测试"""
    controller = SpeedController(mode='fixed', fixed_speed=1)
    assert controller.get_interval() == 1.0

    controller = SpeedController(mode='fixed', fixed_speed=50)
    assert controller.get_interval() == 0.02


def test_default_values():
    """默认参数测试"""
    controller = SpeedController()
    assert controller.mode == 'fixed'
    assert controller.fixed_speed == 10
    assert controller.min_speed == 5
    assert controller.max_speed == 15