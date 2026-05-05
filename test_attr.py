try:
    from app.models import Transaction
    print(f"Transaction class: {Transaction}")
    print(f"Transaction.type attribute: {getattr(Transaction, 'type', 'MISSING')}")
except Exception as e:
    print(f"Error: {e}")
