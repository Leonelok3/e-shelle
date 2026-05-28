def format_money(amount, currency="CAD"):
    return f"{amount:,.2f} {currency}".replace(",", " ")

