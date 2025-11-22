"""
Script to populate sample requests for testing
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.transaction_logger import TransactionLogger
from src.validation_engine import ValidationEngine
from datetime import datetime, timedelta

# Initialize
transaction_logger = TransactionLogger()
validation_engine = ValidationEngine()

# Sample Request 1: Supplier Payment
supplier_payment_data = {
    "club_name": "Data and AI Club",
    "treasurer_email": "abc@123.com",
    "event_code": "E031",
    "vendor_name": "Sky Photography Ltd",
    "purpose_of_payment": "Event photography services for AI Summit",
    "invoice_type": "Final Invoice",
    "invoice_number": "INV-2024-1234",
    "invoice_currency": "GBP",
    "invoice_amount": 850.00,
    "vendor_contact_name": "Alex Sky",
    "vendor_email": "alex.sky@skyphotos.com",
    "vendor_address": "123 Regent Street, London, W1B 4TB",
    "bank_account_name": "Sky Photography Ltd",
    "bank_account_number": "12345678",
    "bank_sort_code": "12-34-56",
    "invoice_upload": "✓ invoice_sky_photography.pdf",
    "date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
}

print("Creating Supplier Payment request...")
req1_id = transaction_logger.create_request(
    member_name="Gaurav",
    form_type="supplier_payment",
    data=supplier_payment_data
)
validation1 = validation_engine.validate(supplier_payment_data, "supplier_payment")
transaction_logger.add_validation_results(req1_id, validation1)
print(f"✅ Created: {req1_id}")

# Sample Request 2: Expense Reimbursement
expense_data = {
    "event_code": "E045",
    "expense_date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
    "total_claim_amount": 245.50,
    "currency": "GBP",
    "merchant_name": "Dishoom Restaurant",
    "location": "London",
    "payment_type": "Cash",
    "expense_description": "Speaker dinner for guest lecturer from Google",
    "charge_allocation_percentage": 100,
    "receipt_upload": "✓ receipt_dishoom.pdf",
    "club_treasurer_email": "abc@123.com",
    "date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
}

print("Creating Expense Reimbursement request...")
req2_id = transaction_logger.create_request(
    member_name="Gaurav",
    form_type="expense_reimbursement",
    data=expense_data
)
validation2 = validation_engine.validate(expense_data, "expense_reimbursement")
transaction_logger.add_validation_results(req2_id, validation2)
print(f"✅ Created: {req2_id}")

# Sample Request 3: Internal Transfer
transfer_data = {
    "treasurer_email": "abc@123.com",
    "initiating_club_name": "Data and AI Club",
    "initiating_club_event_code": "E031",
    "recipient_club_name": "Finance Club",
    "recipient_event_code": "E012",
    "currency": "GBP",
    "transfer_amount": 500.00,
    "purpose_of_transfer": "Co-hosting joint AI & Finance career panel - splitting venue costs",
    "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
}

print("Creating Internal Transfer request...")
req3_id = transaction_logger.create_request(
    member_name="Gaurav",
    form_type="internal_transfer",
    data=transfer_data
)
validation3 = validation_engine.validate(transfer_data, "internal_transfer")
transaction_logger.add_validation_results(req3_id, validation3)
print(f"✅ Created: {req3_id}")

# Sample Request 4: Refund Request
refund_data = {
    "club_name": "Data and AI Club",
    "email": "abc@123.com",
    "event_name": "Data Science Workshop - Cancelled Session",
    "event_finance_code": "E031",
    "refund_type": "Multiple",
    "refund_amount": 150.00,
    "member_name": "Sarah Johnson",
    "reason_for_refund": "Workshop cancelled due to speaker illness - refunding 3 members £50 each",
    "date": datetime.now().strftime("%Y-%m-%d")
}

print("Creating Refund Request...")
req4_id = transaction_logger.create_request(
    member_name="Gaurav",
    form_type="refund_request",
    data=refund_data
)
validation4 = validation_engine.validate(refund_data, "refund_request")
transaction_logger.add_validation_results(req4_id, validation4)
print(f"✅ Created: {req4_id}")

# Approve one of them to test the time saved metric
print("\nApproving one request to test time saved metric...")
transaction_logger.update_request_status(req1_id, "approved", "Arijit", "Approved - all documentation in order")
print(f"✅ Approved: {req1_id}")

print("\n" + "="*60)
print("✅ Sample requests created successfully!")
print("="*60)
print(f"\n📊 Summary:")
print(f"  - Supplier Payment: {req1_id} (APPROVED)")
print(f"  - Expense Reimbursement: {req2_id} (PENDING)")
print(f"  - Internal Transfer: {req3_id} (PENDING)")
print(f"  - Refund Request: {req4_id} (PENDING)")
print(f"\nTime saved: 2 hours (1 approved request × 2h)")
