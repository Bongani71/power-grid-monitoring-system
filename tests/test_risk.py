from main import calculate_risk

def test_calculate_risk():
    assert calculate_risk(100, 100) == "CRITICAL"
    assert calculate_risk(90, 100) == "HIGH"
    assert calculate_risk(75, 100) == "MEDIUM"
    assert calculate_risk(50, 100) == "LOW"

def test_zero_supply():
    # Testing the edge case gracefully handled in code
    assert calculate_risk(100, 0) == "CRITICAL"
