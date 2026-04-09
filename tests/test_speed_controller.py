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


def test_zero_fixed_speed_raises_value_error():
    """固定速度为0时抛出ValueError"""
    with pytest.raises(ValueError, match="Speed must be positive"):
        SpeedController(mode='fixed', fixed_speed=0)


def test_negative_fixed_speed_raises_value_error():
    """固定速度为负数时抛出ValueError"""
    with pytest.raises(ValueError, match="Speed must be positive"):
        SpeedController(mode='fixed', fixed_speed=-10)


def test_zero_min_speed_raises_value_error():
    """最小速度为0时抛出ValueError"""
    with pytest.raises(ValueError, match="Speed must be positive"):
        SpeedController(mode='random', min_speed=0, max_speed=10)


def test_zero_max_speed_raises_value_error():
    """最大速度为0时抛出ValueError"""
    with pytest.raises(ValueError, match="Speed must be positive"):
        SpeedController(mode='random', min_speed=5, max_speed=0)


def test_min_speed_greater_than_max_speed_raises_value_error():
    """最小速度大于最大速度时抛出ValueError"""
    with pytest.raises(ValueError, match="min_speed must not exceed max_speed"):
        SpeedController(mode='random', min_speed=20, max_speed=10)


def test_invalid_mode_raises_value_error():
    """无效模式时抛出ValueError"""
    controller = SpeedController(mode='invalid_mode')
    with pytest.raises(ValueError, match="Invalid mode: invalid_mode"):
        controller.get_interval()


def test_typo_mode_raises_value_error():
    """模式拼写错误时抛出ValueError（如'randm'而非'random'）"""
    controller = SpeedController(mode='randm')
    with pytest.raises(ValueError, match="Invalid mode: randm"):
        controller.get_interval()