from decimal import Decimal

def to_float(value):
    """Convert any numeric value to float."""
    if isinstance(value, Decimal):
        return float(value)
    return float(value)

def calculate_profit_rate(current_value, initial_investment):
    """Calculate profit rate with proper type conversion."""
    current_value = to_float(current_value)
    initial_investment = to_float(initial_investment)
    if initial_investment == 0:
        return 0
    return ((current_value - initial_investment) / initial_investment) * 100

def format_currency(value):
    """Format currency value with proper type conversion."""
    return f"${to_float(value):,.2f}"

def format_percentage(value):
    """Format percentage with proper type conversion."""
    return f"{to_float(value):.2f}%"
