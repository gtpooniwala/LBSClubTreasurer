"""Member UI - Gradio Chat Interface"""

import gradio as gr
import logging
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import ConversationManager, ValidationEngine, TransactionLogger, get_api_client, ensure_data_dirs
from src.utils import format_currency

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize components
ensure_data_dirs()

api_client = get_api_client()
if not api_client:
    logger.error("Failed to initialize API client. Check your credentials.")
    api_client = None

conversation_manager = ConversationManager(api_client) if api_client else None
validation_engine = ValidationEngine()
transaction_logger = TransactionLogger()

# Global state
current_request_data = {}
current_form_type = None
current_validation = None


def get_form_display_name(form_type: str) -> str:
    """Get human-readable form name"""
    if not form_type:
        return "Not confirmed yet"
    form_names = {
        "supplier_payment": "Vendor Payment",
        "internal_transfer": "Internal Transfer",
        "expense_reimbursement": "Expense Reimbursement",
        "refund_request": "Member Refund"
    }
    return form_names.get(form_type, form_type)


def chat_interface(user_message: str, history: list) -> tuple:
    """
    Process user message and return updated history
    """
    global current_request_data, current_form_type, current_validation
    
    if not conversation_manager:
        error_msg = "❌ System Error: API client not initialized. Check your Azure OpenAI credentials."
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": error_msg})
        return history, "ERROR", "", "System unavailable"
    
    try:
        # Process message
        result = conversation_manager.process_message(user_message)
        
        # Update state
        current_request_data = result["extracted_data"]
        current_form_type = result["form_type"]
        
        # Build response
        response = result["response"]
        
        # Add validation info if complete
        if result["complete"] and current_form_type:
            validation_result = validation_engine.validate(
                current_request_data,
                current_form_type
            )
            current_validation = validation_result
            
            response += "\n\n" + validation_engine.get_validation_summary(validation_result)
        
        # Add to history with role/content format
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": response})
        
        # Update UI displays
        extracted_json = str(current_request_data)
        
        # Get agent status for display
        agent_status = result.get("agent_status", "💬 Processing...")
        
        status_msg = f"**Current Stage:** {agent_status}\n\n"
        status_msg += f"**Form Type:** {get_form_display_name(current_form_type)}\n"
        
        if result.get("suggested_form_type") and not result.get("form_type_confirmed"):
            status_msg += f"**Suggested Type:** {get_form_display_name(result['suggested_form_type'])} (awaiting confirmation)\n"
        
        if result.get("form_type_confirmed"):
            status_msg += "**Confirmed:** ✅\n"
            status_msg += f"**Fields Collected:** {len(current_request_data)}/{len(result.get('missing_fields', [])) + len(current_request_data)}\n\n"
            
            # Show missing fields in readable format
            if result['missing_fields']:
                status_msg += "**📋 Still Need:**\n"
                # Get field descriptions if available
                if conversation_manager and conversation_manager.form_specific_fields:
                    for field in result['missing_fields']:
                        field_def = conversation_manager.form_specific_fields.get("fields", {}).get(field, {})
                        if field_def and "description" in field_def:
                            status_msg += f"  • {field_def['description']}\n"
                        else:
                            status_msg += f"  • {field.replace('_', ' ').title()}\n"
                else:
                    for field in result['missing_fields']:
                        status_msg += f"  • {field.replace('_', ' ').title()}\n"
            else:
                status_msg += "**✅ All Information Collected**\n"
        
        status_msg += f"\n**Confidence:** {result['confidence']:.0%}"
        
        submit_status = "✅ Ready to Submit" if result["complete"] else agent_status
        
        return history, extracted_json, status_msg, submit_status
    
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        error_response = f"❌ Error: {str(e)}"
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": error_response})
        return history, "{}", "ERROR", "Error occurred"


def submit_request(history: list, extracted_json: str) -> str:
    """Submit request for treasurer review"""
    
    if not current_form_type or not current_request_data:
        return "❌ Cannot submit: No valid request data"
    
    # Validate one more time
    validation_result = validation_engine.validate(
        current_request_data,
        current_form_type
    )
    
    if not validation_result["passed"]:
        violations_text = "\n".join([v["message"] for v in validation_result["violations"]])
        return f"❌ Cannot submit - validation errors:\n{violations_text}"
    
    try:
        # Create request in transaction logger
        request_id = transaction_logger.create_request(
            member_name="Demo User",  # In production: from authentication
            form_type=current_form_type,
            data=current_request_data
        )
        
        # Add validation results
        transaction_logger.add_validation_results(request_id, validation_result)
        
        # Reset for next request
        conversation_manager.reset_conversation()
        
        success_msg = (
            f"✅ **Request {request_id} submitted successfully!**\n\n"
            f"**Summary:**\n"
            f"- Type: {current_form_type}\n"
            f"- Amount: {format_currency(current_request_data.get('amount', 0))}\n"
            f"- Budget: {current_request_data.get('budget_line', 'N/A')}\n\n"
            f"Your request has been sent to the treasurer for review. "
            f"You'll be notified when they take action."
        )
        
        return success_msg
    
    except Exception as e:
        logger.error(f"Error submitting request: {e}")
        return f"❌ Error submitting request: {str(e)}"


def reset_form() -> tuple:
    """Reset the form"""
    global current_request_data, current_form_type, current_validation
    
    current_request_data = {}
    current_form_type = None
    current_validation = None
    
    conversation_manager.reset_conversation() if conversation_manager else None
    
    return (
        [],  # Empty history
        "{}",  # Empty JSON
        "Form reset. Ready to start a new request.",
        "⏳ Ready"
    )


# Build Gradio interface
def create_interface():
    """Create the Gradio interface"""
    
    with gr.Blocks(title="LBS Finance Assistant") as app:
        gr.Markdown("# 💰 LBS Club Finance Assistant")
        gr.Markdown(
            "Welcome! I'll help you submit reimbursements and finance requests. "
            "Just describe what you need in natural language."
        )
        
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### 💬 Chat Interface")
                
                chatbot = gr.Chatbot(
                    label="Conversation with AI Assistant",
                    height=500,
                    show_label=True
                )
                
                msg_input = gr.Textbox(
                    label="Your message",
                    placeholder="e.g., 'I need £180 reimbursed for speaker dinner on Nov 20'",
                    lines=2,
                    interactive=True
                )
                
                with gr.Row():
                    submit_chat = gr.Button("Send", scale=1, variant="primary")
                    reset_btn = gr.Button("New Request", scale=1)
            
            with gr.Column(scale=1):
                gr.Markdown("### 📋 Request Details")
                
                extracted_display = gr.Textbox(
                    label="Extracted Data",
                    value="{}",
                    interactive=False,
                    lines=10
                )
                
                status_display = gr.Textbox(
                    label="Status",
                    value="Ready to start",
                    interactive=False,
                    lines=5
                )
                
                submit_status = gr.Textbox(
                    label="Submission Status",
                    value="⏳ Waiting",
                    interactive=False
                )
                
                gr.Markdown("### ✅ Submit for Approval")
                
                submit_btn = gr.Button(
                    "Submit for Treasurer Review",
                    scale=1,
                    variant="primary",
                    size="lg"
                )
                
                submit_result = gr.Textbox(
                    label="Result",
                    value="",
                    interactive=False,
                    lines=4
                )
        
        # Event handlers
        def on_send(message, history):
            return chat_interface(message, history)
        
        msg_input.submit(
            on_send,
            [msg_input, chatbot],
            [chatbot, extracted_display, status_display, submit_status]
        ).then(
            lambda: gr.Textbox(value=""),
            [],
            msg_input
        )
        
        submit_chat.click(
            on_send,
            [msg_input, chatbot],
            [chatbot, extracted_display, status_display, submit_status]
        ).then(
            lambda: gr.Textbox(value=""),
            [],
            msg_input
        )
        
        reset_btn.click(
            reset_form,
            [],
            [chatbot, extracted_display, status_display, submit_status]
        )
        
        submit_btn.click(
            submit_request,
            [chatbot, extracted_display],
            submit_result
        )
    
    return app


if __name__ == "__main__":
    app = create_interface()
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True
    )
