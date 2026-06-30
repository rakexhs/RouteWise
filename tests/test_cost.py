from app.gateway.cost import cost_from_table, estimate_cost
from app.providers.mock_provider import MockLargeProvider, MockSmallProvider


def test_mock_small_cost():
    provider = MockSmallProvider()
    cost = estimate_cost(provider, 1000, 500)
    assert cost > 0
    assert cost < 0.01


def test_mock_large_cost_higher():
    small = MockSmallProvider()
    large = MockLargeProvider()
    small_cost = estimate_cost(small, 1000, 1000)
    large_cost = estimate_cost(large, 1000, 1000)
    assert large_cost > small_cost


def test_cost_from_table():
    cost = cost_from_table("openai", 1000, 1000)
    assert cost > 0
