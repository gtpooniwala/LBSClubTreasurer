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
uploaded_documents = []


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


def format_extracted_data(data: dict) -> str:
    """Format extracted data for better readability"""
    if not data:
        return "No data collected yet"
    
    # Skip hardcoded fields that are not user-provided
    skip_fields = {
        "club_name", "treasurer_email", "club_treasurer_email", 
        "location", "payment_type", "charge_allocation_percentage",
        "initiating_club_name", "email", "invoice_type", "currency",
        "invoice_currency", "transfer_amount_currency"
    }
    
    formatted_lines = []
    for key, value in data.items():
        if key in skip_fields:
            continue
        # Format field name nicely
        field_name = key.replace('_', ' ').title()
        formatted_lines.append(f"• {field_name}: {value}")
    
    return "\n".join(formatted_lines) if formatted_lines else "No user data collected yet"


def chat_interface(user_message: str, history: list) -> tuple:
    """
    Process user message and return updated history
    """
    global current_request_data, current_form_type, current_validation, uploaded_documents
    
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
        
        # Update UI displays with formatted data
        extracted_json = format_extracted_data(current_request_data)
        
        # Get agent status for display
        agent_status = result.get("agent_status", "💬 Processing...")
        
        status_msg = f"Current Stage: {agent_status}\n\n"
        status_msg += f"Form Type: {get_form_display_name(current_form_type)}\n"
        
        if result.get("suggested_form_type") and not result.get("form_type_confirmed"):
            status_msg += f"Suggested Type: {get_form_display_name(result['suggested_form_type'])} (awaiting confirmation)\n"
        
        if result.get("form_type_confirmed"):
            status_msg += "Confirmed: ✅\n"
            status_msg += f"Fields Collected: {len(current_request_data)}/{len(result.get('missing_fields', [])) + len(current_request_data)}\n\n"
            
            # Show missing fields in readable format
            if result['missing_fields']:
                status_msg += "Still Need:\n"
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
                status_msg += "✅ All Information Collected\n"
        
        status_msg += f"\nConfidence: {result['confidence']:.0%}"
        
        submit_status = "✅ Ready to Submit" if result["complete"] else agent_status
        
        return history, extracted_json, status_msg, submit_status
    
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        error_response = f"❌ Error: {str(e)}"
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": error_response})
        return history, "{}", "ERROR", "Error occurred"


def _get_amount_from_data(data: dict, form_type: str) -> float:
    """Get amount based on form type"""
    if form_type == "supplier_payment":
        return data.get("invoice_amount", 0)
    elif form_type == "expense_reimbursement":
        return data.get("total_claim_amount", 0)
    elif form_type == "internal_transfer":
        return data.get("transfer_amount", 0)
    elif form_type == "refund_request":
        return data.get("refund_amount", 0)
    return data.get("amount", 0)


def _get_vendor_from_data(data: dict, form_type: str) -> str:
    """Get vendor/payee based on form type"""
    if form_type == "supplier_payment":
        return data.get("vendor_name", "N/A")
    elif form_type == "expense_reimbursement":
        return data.get("merchant_name", "N/A")
    elif form_type == "internal_transfer":
        return data.get("recipient_club_name", "N/A")
    elif form_type == "refund_request":
        return data.get("member_name", "N/A")
    return "N/A"


def _get_description_from_data(data: dict, form_type: str) -> str:
    """Get description based on form type"""
    if form_type == "supplier_payment":
        return data.get("purpose_of_payment", "N/A")
    elif form_type == "expense_reimbursement":
        return data.get("expense_description", "N/A")
    elif form_type == "internal_transfer":
        return data.get("purpose_of_transfer", "N/A")
    elif form_type == "refund_request":
        return data.get("reason_for_refund", "N/A")
    return data.get("description", "N/A")


def submit_request(history: list, extracted_json: str) -> str:
    """Submit request for treasurer review"""
    global uploaded_documents, current_form_type, current_request_data, current_validation
    
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
            member_name="Gaurav",
            form_type=current_form_type,
            data=current_request_data
        )
        
        # Add validation results
        transaction_logger.add_validation_results(request_id, validation_result)
        
        # Store uploaded documents if any
        if uploaded_documents:
            current_request_data["uploaded_documents"] = [doc["name"] for doc in uploaded_documents]
            # In production: actually save/move files to request folder
        
        # Get form-specific fields for display
        amount = _get_amount_from_data(current_request_data, current_form_type)
        vendor = _get_vendor_from_data(current_request_data, current_form_type)
        description = _get_description_from_data(current_request_data, current_form_type)
        event_code = current_request_data.get('event_code', 'N/A')
        
        # Build detailed summary
        form_names = {
            "supplier_payment": "Vendor Payment",
            "internal_transfer": "Internal Transfer",
            "expense_reimbursement": "Expense Reimbursement",
            "refund_request": "Member Refund"
        }
        form_display_name = form_names.get(current_form_type, current_form_type)
        
        success_msg = (
            f"✅ **Request {request_id} Submitted Successfully!**\n\n"
            f"**Request Type:** {form_display_name}\n\n"
            f"**Key Details:**\n"
            f"- Amount: {format_currency(amount)}\n"
            f"- Vendor/Payee: {vendor}\n"
            f"- Description: {description}\n"
            f"- Event Code: {event_code}\n"
        )
        
        if current_request_data.get("uploaded_documents"):
            success_msg += f"- Documents: {len(current_request_data['uploaded_documents'])} file(s) attached\n"
        
        success_msg += (
            "\n---\n\n"
            "📧 Your request has been sent to **Arijit** (Treasurer) for review.\n"
            "You'll be notified when action is taken.\n\n"
            "✨ You can now start a new request or close this window."
        )
        
        # Reset for next request
        conversation_manager.reset_conversation()
        uploaded_documents = []
        
        return success_msg
    
    except Exception as e:
        logger.error(f"Error submitting request: {e}")
        return f"❌ Error submitting request: {str(e)}"


def reset_form() -> tuple:
    """Reset the form"""
    global current_request_data, current_form_type, current_validation, uploaded_documents
    
    current_request_data = {}
    current_form_type = None
    current_validation = None
    uploaded_documents = []
    
    conversation_manager.reset_conversation() if conversation_manager else None
    
    return (
        [],  # Empty history
        "{}",  # Empty JSON
        "Form reset. Ready to start a new request.",
        "⏳ Ready",
        "No documents uploaded"  # Clear file status
    )


def handle_file_upload(files) -> str:
    """Handle uploaded documents"""
    global uploaded_documents, current_request_data, current_form_type
    
    if not files:
        return "No files uploaded"
    
    uploaded_documents = []
    file_info = []
    
    for file in files:
        # Extract file info
        file_data = {
            "name": os.path.basename(file.name) if hasattr(file, 'name') else "unknown",
            "path": file.name if hasattr(file, 'name') else file,
            "size": os.path.getsize(file.name) if hasattr(file, 'name') and os.path.exists(file.name) else 0
        }
        uploaded_documents.append(file_data)
        file_info.append(f"📎 {file_data['name']} ({file_data['size']} bytes)")
    
    # Automatically populate file fields based on form type
    if uploaded_documents and conversation_manager:
        file_field_mapping = {
            "supplier_payment": "invoice_upload",
            "expense_reimbursement": "receipt_upload",
            "internal_transfer": "file_upload"
        }
        
        # Update the conversation manager's extracted_data directly
        if current_form_type and current_form_type in file_field_mapping:
            field_name = file_field_mapping[current_form_type]
            conversation_manager.extracted_data[field_name] = f"✓ {uploaded_documents[0]['name']}"
            current_request_data[field_name] = f"✓ {uploaded_documents[0]['name']}"
        # If form type not yet determined, try all possible file fields
        else:
            # Mark all possible file upload fields in conversation manager
            conversation_manager.extracted_data["invoice_upload"] = f"✓ {uploaded_documents[0]['name']}"
            conversation_manager.extracted_data["receipt_upload"] = f"✓ {uploaded_documents[0]['name']}"
            conversation_manager.extracted_data["file_upload"] = f"✓ {uploaded_documents[0]['name']}"
            # Also update local state
            current_request_data["invoice_upload"] = f"✓ {uploaded_documents[0]['name']}"
            current_request_data["receipt_upload"] = f"✓ {uploaded_documents[0]['name']}"
            current_request_data["file_upload"] = f"✓ {uploaded_documents[0]['name']}"
    
    return "**Uploaded Documents:**\n" + "\n".join(file_info)


def handle_file_upload_with_data(files) -> tuple:
    """Handle file upload and return both status and updated data"""
    global current_request_data, current_form_type
    
    file_status = handle_file_upload(files)
    extracted_json = str(current_request_data)
    
    # Create a message about the uploaded files to inform the chatbot
    if uploaded_documents:
        file_names = [doc["name"] for doc in uploaded_documents]
        # Make the message explicit about what field is being filled
        if current_form_type == "supplier_payment":
            upload_message = f"Here is the invoice PDF: {', '.join(file_names)}"
        elif current_form_type == "expense_reimbursement":
            upload_message = f"Here is the receipt: {', '.join(file_names)}"
        elif current_form_type == "internal_transfer":
            upload_message = f"Here is the supporting document: {', '.join(file_names)}"
        else:
            upload_message = f"I've uploaded the required document(s): {', '.join(file_names)}"
    else:
        upload_message = ""
    
    return file_status, extracted_json, upload_message


# Build Gradio interface
def create_interface():
    """Create the Gradio interface"""
    
    # Reset conversation state on interface load
    global current_request_data, current_form_type, current_validation, uploaded_documents
    current_request_data = {}
    current_form_type = None
    current_validation = None
    uploaded_documents = []
    if conversation_manager:
        conversation_manager.reset_conversation()
    
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
                    interactive=True,
                    autofocus=True,
                    elem_classes="message-input"
                )
                
                with gr.Row():
                    submit_chat = gr.Button("Send", scale=1, variant="primary")
                    file_upload = gr.UploadButton(
                        "📎 Upload Documents",
                        file_count="multiple",
                        file_types=[".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".xlsx", ".csv"],
                        scale=1
                    )
                
                gr.Markdown("---")
                
                gr.Markdown("### 📤 Submit Your Request")
                
                submit_btn = gr.Button(
                    "✅ Submit for Treasurer Review",
                    scale=1,
                    variant="primary",
                    size="lg"
                )
                
                submit_result = gr.Textbox(
                    label="Submission Status",
                    value="",
                    interactive=False,
                    lines=12,
                    show_label=True,
                    visible=True
                )
            
            with gr.Column(scale=1):
                gr.Markdown("### 📋 Request Summary")
                
                extracted_display = gr.Textbox(
                    label="Collected Information",
                    value="No data collected yet",
                    interactive=False,
                    lines=12
                )
                
                status_display = gr.Textbox(
                    label="Progress",
                    value="Ready to start",
                    interactive=False,
                    lines=8
                )
                
                file_status = gr.Textbox(
                    label="Documents",
                    value="No documents uploaded",
                    interactive=False,
                    lines=3
                )
                
                submit_status = gr.Textbox(
                    label="Ready to Submit?",
                    value="⏳ Waiting",
                    interactive=False
                )
        
        # Event handlers
        def on_send(message, history):
            return chat_interface(message, history)
        
        # Helper to clear and refocus input
        def clear_input():
            return gr.Textbox(value="", interactive=True)
        
        # Enter key or click Send button
        msg_input.submit(
            on_send,
            [msg_input, chatbot],
            [chatbot, extracted_display, status_display, submit_status]
        ).then(
            clear_input,
            [],
            msg_input
        )
        
        submit_chat.click(
            on_send,
            [msg_input, chatbot],
            [chatbot, extracted_display, status_display, submit_status]
        ).then(
            clear_input,
            [],
            msg_input
        )
        
        # File upload handler - processes upload and triggers chatbot
        def handle_upload_and_chat(files, history):
            # First handle the file upload
            file_status, extracted_json, upload_message = handle_file_upload_with_data(files)
            
            # If files were uploaded, process through chatbot
            if upload_message:
                updated_history, updated_json, updated_status, updated_submit = chat_interface(upload_message, history)
                return updated_history, updated_json, updated_status, updated_submit, file_status
            else:
                return history, extracted_json, "Ready to start", "⏳ Waiting", file_status
        
        file_upload.upload(
            handle_upload_and_chat,
            [file_upload, chatbot],
            [chatbot, extracted_display, status_display, submit_status, file_status]
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
