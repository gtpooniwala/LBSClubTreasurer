#!/usr/bin/env python3
"""Test AI Agent Cup event code recognition"""

import os
os.environ['AZURE_OPENAI_KEY'] = 'test'
os.environ['AZURE_OPENAI_ENDPOINT'] = 'test'

from src.conversation_manager import ConversationManager
from unittest.mock import MagicMock

mock_client = MagicMock()
cm = ConversationManager(mock_client)

print("="*70)
print("AI AGENT CUP EVENT CODE TEST")
print("="*70)

# Check if event code loaded
print(f"\n✅ Total event codes loaded: {len(cm.event_codes_df)}")

# Find AI Agent Cup
ai_cup = cm.event_codes_df[cm.event_codes_df['event_name'].str.contains('AI Agent Cup', case=False)]
if not ai_cup.empty:
    print("\n🎯 Found AI Agent Cup event code:")
    ec = ai_cup.iloc[0]
    print(f"   Code: {ec['event_code']}")
    print(f"   Club: {ec['club_name']}")
    print(f"   Event: {ec['event_name']}")
    print(f"   Type: {ec['event_type']}")
    print(f"   VAT: {ec['vat_status']}")
    print(f"   Year: {ec['year_created']}")
else:
    print("\n❌ AI Agent Cup not found!")

# Test auto-suggestion
print("\n" + "="*70)
print("TESTING AUTO-SUGGESTION")
print("="*70)

# Simulate expense for AI Agent Cup with context
cm.conversation_history = []
cm.extracted_data = {
    "club_name": "Data and AI Club",
    "expense_description": "Expenses for AI Agent Cup competition"
}

suggestion = cm._suggest_event_code()
print(f"\nContext: 'Expenses for AI Agent Cup competition'")
if suggestion:
    print(f"   ✅ Auto-suggested: {suggestion['code']}")
    print(f"   Event: {suggestion.get('event_match', 'N/A')}")
    print(f"   Confidence: {suggestion.get('confidence', 'N/A')}")
else:
    print("   ⚠️  No auto-suggestion")

# Test with partial match
cm.extracted_data['expense_description'] = "Competition prize money"
cm.extracted_data.pop('event_name', None)
suggestion = cm._suggest_event_code()
print(f"\nContext: 'Competition prize money' (for Data and AI Club)")
if suggestion:
    print(f"   ✅ Auto-suggested: {suggestion['code']}")
    print(f"   Club match: {suggestion.get('club_match', 'N/A')}")
else:
    print("   ⚠️  No auto-suggestion")

print("\n" + "="*70)
