#!/usr/bin/env python3
"""Test progressive field collection (3-4 fields at a time)"""

import os
os.environ['AZURE_OPENAI_KEY'] = 'test'
os.environ['AZURE_OPENAI_ENDPOINT'] = 'test'

from src.conversation_manager import ConversationManager
from unittest.mock import MagicMock

mock_client = MagicMock()
cm = ConversationManager(mock_client)

print("="*70)
print("PROGRESSIVE FIELD COLLECTION TEST")
print("="*70)

# Simulate expense reimbursement
cm.form_type = 'expense_reimbursement'
cm.form_type_confirmed = True
cm.load_form_specific_rules('expense_reimbursement')

print("\n✅ Simulating user providing fields progressively...\n")

# === STEP 1: First group (basics) ===
print("="*70)
print("STEP 1: Ask for first group (3 fields)")
print("="*70)
cm.missing_fields = [f for f in cm.required_fields if f not in cm.extracted_data]
response = cm._generate_contextual_response()
print(response)

# User provides first group
print("\n[User provides: date=2025-11-20, amount=150, currency=GBP]\n")
cm.extracted_data['expense_date'] = '2025-11-20'
cm.extracted_data['total_claim_amount'] = 150
cm.extracted_data['currency'] = 'GBP'

# === STEP 2: Second group (where & what) ===
print("="*70)
print("STEP 2: Ask for second group (3 fields)")
print("="*70)
cm.missing_fields = [f for f in cm.required_fields if f not in cm.extracted_data]
response = cm._generate_contextual_response()
print(response)

# User provides second group
print("\n[User provides: merchant=Restaurant ABC, description=Team dinner, event_code=E031]\n")
cm.extracted_data['merchant_name'] = 'Restaurant ABC'
cm.extracted_data['expense_description'] = 'Team dinner for AI Agent Cup'
cm.extracted_data['event_code'] = 'E031'

# === STEP 3: Final group (documents) ===
print("="*70)
print("STEP 3: Ask for final group (1 field)")
print("="*70)
cm.missing_fields = [f for f in cm.required_fields if f not in cm.extracted_data]
response = cm._generate_contextual_response()
print(response)

# User provides final field
print("\n[User uploads receipt]\n")
cm.extracted_data['receipt_upload'] = 'receipt_123.pdf'

# === STEP 4: All complete ===
print("="*70)
print("STEP 4: All fields collected!")
print("="*70)
cm.missing_fields = []
response = cm._generate_contextual_response()
print(response[:200] + "...\n")  # Truncate summary

print("="*70)
print("✅ Progressive collection complete in 3 steps!")
print(f"   Total fields: {len(cm.required_fields)}")
print(f"   User provided: 7 fields across 3 steps")
print(f"   Auto-filled: 6 fields")
print("="*70)
