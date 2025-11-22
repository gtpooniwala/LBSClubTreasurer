#!/usr/bin/env python3
"""Test Expense Reimbursement with Infor XM fields"""

import os
os.environ['AZURE_OPENAI_KEY'] = 'test'
os.environ['AZURE_OPENAI_ENDPOINT'] = 'test'

from src.conversation_manager import ConversationManager
from unittest.mock import MagicMock

mock_client = MagicMock()
cm = ConversationManager(mock_client)

print("="*70)
print("EXPENSE REIMBURSEMENT - INFOR XM INTEGRATION TEST")
print("="*70)

# Simulate expense reimbursement
cm.form_type = 'expense_reimbursement'
cm.form_type_confirmed = True
cm.load_form_specific_rules('expense_reimbursement')

print(f"\n✅ Pre-filled fields (hard-coded):")
for key, value in cm.extracted_data.items():
    print(f"   {key}: {value}")

print(f"\n📋 Required fields for expense reimbursement:")
for field in cm.required_fields:
    if field not in cm.extracted_data:
        print(f"   • {field}")

print(f"\n✅ Total required: {len(cm.required_fields)}")
print(f"✅ Pre-filled: {len(cm.extracted_data)}")
print(f"⏳ Still need: {len([f for f in cm.required_fields if f not in cm.extracted_data])}")

# Generate response
cm.missing_fields = [f for f in cm.required_fields if f not in cm.extracted_data]
response = cm._generate_contextual_response()

print(f"\n💬 AI will ask for:")
print("="*70)
print(response)
print("="*70)
