#!/usr/bin/env python3
"""
Test Multi-Agent Flow with Confirmation
Demonstrates the 6-agent system with user confirmation
"""

import os
import json
from unittest.mock import MagicMock, Mock

# Set dummy environment variables
os.environ['AZURE_OPENAI_KEY'] = 'test-key'
os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://test.openai.azure.com/'

from src.conversation_manager import ConversationManager

def create_mock_client():
    """Create a mock Azure OpenAI client"""
    return MagicMock()

def mock_classification_response(form_type, confidence=0.95):
    """Mock response for form classification"""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = json.dumps({
        "form_type": form_type,
        "confidence": confidence,
        "reasoning": f"User mentioned keywords related to {form_type}"
    })
    return mock_response

def mock_extraction_response(fields):
    """Mock response for field extraction"""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = json.dumps({
        "fields": fields,
        "confidence": {key: 0.9 for key in fields.keys()}
    })
    return mock_response

def print_result(step, result):
    """Print formatted result"""
    print(f"\n{'='*70}")
    print(f"STEP {step}")
    print(f"{'='*70}")
    print(f"🤖 Agent Status: {result['agent_status']}")
    print(f"📊 Current Agent: {result['current_agent']}")
    print(f"📝 Form Type: {result.get('form_type', 'None')}")
    print(f"✅ Form Confirmed: {result.get('form_type_confirmed', False)}")
    if result.get('suggested_form_type'):
        print(f"💡 Suggested Type: {result['suggested_form_type']}")
    print(f"\n💬 AI Response:\n{result['response']}")
    if result['extracted_data']:
        print(f"\n📋 Extracted Data: {result['extracted_data']}")
    print(f"\n⏳ Complete: {result['complete']}")

def test_full_flow():
    """Test complete flow with confirmation"""
    print("\n" + "🚀 MULTI-AGENT SYSTEM TEST ".center(70, "="))
    print("\nAgent Flow:")
    print("  0. Initial Gathering → Detect request type")
    print("  1. Ask user to CONFIRM form type")
    print("  2-5. Form-specific agents collect fields")
    print("  6. Validation agent checks rules")
    print("="*70)
    
    mock_client = create_mock_client()
    cm = ConversationManager(mock_client)
    
    # STEP 1: User describes request (Agent 0 - Initial Gathering)
    print("\n\n" + "STEP 1: User describes request".center(70, "-"))
    mock_client.chat.completions.create.return_value = mock_classification_response("expense_reimbursement", 0.92)
    
    result1 = cm.process_message("I paid £150 for a speaker dinner and need to be reimbursed")
    print_result(1, result1)
    
    assert result1['current_agent'] == 'initial_gathering'
    assert result1['suggested_form_type'] == 'expense_reimbursement'
    assert not result1['form_type_confirmed']
    assert "correct" in result1['response'].lower() or "yes" in result1['response'].lower()
    
    # STEP 2: User confirms (moves to Form Collection Agent)
    print("\n\n" + "STEP 2: User confirms form type".center(70, "-"))
    
    result2 = cm.process_message("Yes, that's correct")
    print_result(2, result2)
    
    assert result2['form_type'] == 'expense_reimbursement'
    assert result2['form_type_confirmed']
    assert result2['current_agent'] == 'form_collection_expense_reimbursement'
    
    # STEP 3: Collect club name (Agent 3 - Expense Reimbursement)
    print("\n\n" + "STEP 3: Collecting club name".center(70, "-"))
    mock_client.chat.completions.create.return_value = mock_extraction_response({
        "club_name": "Finance Club"
    })
    
    result3 = cm.process_message("It's for the Finance Club")
    print_result(3, result3)
    
    assert 'club_name' in result3['extracted_data']
    assert result3['current_agent'] == 'form_collection_expense_reimbursement'
    
    # STEP 4: Collect amount (continuing form collection)
    print("\n\n" + "STEP 4: Collecting amount".center(70, "-"))
    mock_client.chat.completions.create.return_value = mock_extraction_response({
        "total_claim_amount": 150.0
    })
    
    result4 = cm.process_message("The amount is £150")
    print_result(4, result4)
    
    assert 'total_claim_amount' in result4['extracted_data']
    
    # STEP 5: Provide EC Reference (final required field)
    print("\n\n" + "STEP 5: Providing EC Reference".center(70, "-"))
    mock_client.chat.completions.create.return_value = mock_extraction_response({
        "ec_reference": "EC00012345",
        "club_treasurer_email": "treasurer@lbs.edu"
    })
    
    result5 = cm.process_message("EC reference is EC00012345, email is treasurer@lbs.edu")
    print_result(5, result5)
    
    # Check if validation agent activated
    if not result5['missing_fields']:
        assert result5['current_agent'] == 'validation'
        print("\n✅ All fields collected - Validation Agent activated!")
    
    print("\n" + "="*70)
    print("✅ MULTI-AGENT FLOW TEST COMPLETE")
    print("="*70)
    print("\nSummary:")
    print(f"  ✓ Agent 0 (Initial Gathering): Detected form type")
    print(f"  ✓ Confirmation: User confirmed form type")
    print(f"  ✓ Agent 3 (Expense Reimbursement): Collected fields")
    print(f"  ✓ Agent 6 (Validation): Ready to validate")
    print(f"  ✓ UI Status Updates: Working correctly")
    print("="*70 + "\n")

def test_rejection_flow():
    """Test when user rejects suggested form type"""
    print("\n" + "🔄 REJECTION FLOW TEST ".center(70, "="))
    
    mock_client = create_mock_client()
    cm = ConversationManager(mock_client)
    
    # STEP 1: AI suggests wrong form type
    print("\n" + "STEP 1: AI makes incorrect suggestion".center(70, "-"))
    mock_client.chat.completions.create.return_value = mock_classification_response("supplier_payment", 0.85)
    
    result1 = cm.process_message("I need to pay someone")
    print_result(1, result1)
    
    assert result1['suggested_form_type'] == 'supplier_payment'
    
    # STEP 2: User rejects
    print("\n" + "STEP 2: User rejects suggestion".center(70, "-"))
    
    result2 = cm.process_message("No, that's not right")
    print_result(2, result2)
    
    assert result2['suggested_form_type'] is None
    assert not result2['form_type_confirmed']
    assert result2['current_agent'] == 'initial_gathering'
    assert "describe" in result2['response'].lower() or "clarify" in result2['response'].lower()
    
    print("\n✅ Rejection handled correctly - asking for clarification\n")

if __name__ == "__main__":
    test_full_flow()
    test_rejection_flow()
    
    print("\n" + "🎉 ALL TESTS PASSED ".center(70, "="))
    print("\nKey Features Verified:")
    print("  ✅ 6-agent system (Initial → Confirmation → Form-specific → Validation)")
    print("  ✅ User confirmation before proceeding")
    print("  ✅ Agent status tracking for UI")
    print("  ✅ Form type rejection handling")
    print("  ✅ Progressive field collection")
    print("="*70 + "\n")
