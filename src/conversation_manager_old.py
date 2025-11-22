"""Conversation Manager - Multi-Agent System with Dynamic Rule Loading"""

import json
import logging
from typing import Dict, List, Optional
from src.utils import load_json, get_config_path, generate_request_id

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Multi-agent conversation manager that:
    1. Classifies form type (Agent 1)
    2. Dynamically loads relevant rules (Agent 2)
    3. Extracts form-specific fields (Agent 3)
    4. Validates against rules progressively (Agent 4)
    """
    
    def __init__(self, api_client):
        self.api_client = api_client
        self.reset_conversation()
        self.load_base_rules()
    
    def reset_conversation(self):
        """Start fresh conversation"""
        self.history = []
        self.extracted_data = {}
        self.form_type = None
        self.form_specific_rules = None
        self.form_specific_fields = None
        self.required_fields = []
        self.missing_fields = []
        self.validation_status = {}
        self.confidence_scores = {}
        self.request_id = generate_request_id()
        self.classification_attempted = False
    
    def load_base_rules(self):
        """Load only top-level rules that apply to all forms"""
        try:
            all_rules = load_json(get_config_path("lbs_rules_extracted.json"))
            
            # Extract only base rules that apply to ALL transactions
            self.base_rules = {
                "balance_requirements": all_rules["core_rules"]["balance_requirements"],
                "communication_rules": all_rules["core_rules"]["communication_rules"],
                "processing_times": all_rules["core_rules"]["processing_times"],
                "finance_code_required": True
            }
            
            # Store form type classification criteria (lightweight)
            self.form_classification_criteria = all_rules.get("form_type_classification_criteria", {})
            
            logger.info("Base rules loaded successfully")
        except Exception as e:
            logger.error(f"Error loading base rules: {e}")
            self.base_rules = {}
            self.form_classification_criteria = {}
    
    def load_form_specific_rules(self, form_type: str):
        """Dynamically load rules and fields for the classified form type"""
        try:
            # Load form-specific rules
            all_rules = load_json(get_config_path("lbs_rules_extracted.json"))
            form_rules = all_rules.get("transaction_types", {}).get(form_type, {})
            
            # Load form-specific fields
            all_fields = load_json(get_config_path("form_fields.json"))
            form_key = f"{form_type}_form"
            form_fields = all_fields.get(form_key, {})
            
            self.form_specific_rules = form_rules
            self.form_specific_fields = form_fields
            
            # Extract required fields
            if form_fields and "fields" in form_fields:
                self.required_fields = [
                    field_name for field_name, field_def in form_fields["fields"].items()
                    if field_def.get("required", False)
                ]
            
            logger.info(f"Loaded rules and {len(self.required_fields)} required fields for {form_type}")
            
        except Exception as e:
            logger.error(f"Error loading form-specific rules for {form_type}: {e}")
            self.form_specific_rules = {}
            self.form_specific_fields = {}
            self.required_fields = []
    
    def process_message(self, user_message: str) -> Dict:
        """
        Process a user message using multi-agent approach:
        1. Agent 1: Classify form type (if not done)
        2. Agent 2: Load form-specific rules and fields
        3. Agent 3: Extract data based on form type
        4. Agent 4: Validate against rules
        
        Returns dictionary with response and extracted data
        """
        # Add to history
        self.history.append({
            "role": "user",
            "content": user_message
        })
        
        # AGENT 1: Classify form type if not yet done
        if not self.form_type and not self.classification_attempted:
            classification_result = self._classify_form_type_agent(user_message)
            
            if classification_result and classification_result.get("confidence", 0) > 0.7:
                self.form_type = classification_result["form_type"]
                self.classification_attempted = True
                
                # AGENT 2: Load form-specific rules and fields
                self.load_form_specific_rules(self.form_type)
                
                logger.info(f"✅ Form classified as: {self.form_type}")
        
        # AGENT 3: Extract data (using form-specific context if available)
        extraction_result = self._extract_data_agent(user_message)
        self.extracted_data.update(extraction_result.get("fields", {}))
        self.confidence_scores.update(extraction_result.get("confidence", {}))
        
        # Update missing fields
        self.missing_fields = [
            field for field in self.required_fields
            if field not in self.extracted_data or not self.extracted_data[field]
        ]
        
        # AGENT 4: Progressive validation
        validation_result = self._validate_against_rules_agent()
        self.validation_status = validation_result
        
        # Generate appropriate response
        agent_response = self._generate_contextual_response()
        
        # Add to history
        self.history.append({
            "role": "assistant",
            "content": agent_response
        })
        
        return {
            "response": agent_response,
            "extracted_data": self.extracted_data.copy(),
            "complete": len(self.missing_fields) == 0 and validation_result.get("can_submit", False),
            "form_type": self.form_type,
            "missing_fields": self.missing_fields,
            "validation_status": validation_result,
            "confidence": self._calculate_overall_confidence(),
            "request_id": self.request_id
        }
    
    def _classify_form_type_agent(self, message: str) -> Optional[Dict]:
        """
        AGENT 1: Classify which of the 4 form types this request belongs to
        
        Returns: {"form_type": "supplier_payment|internal_transfer|expense_reimbursement|refund_request", "confidence": 0.95}
        """
        
        system_prompt = """You are a form classification specialist for LBS Club finance requests.

Classify the user's request into ONE of these 4 form types:

1. **supplier_payment**: External vendor invoices (not yet paid)
   - Keywords: invoice, supplier, vendor, payment due, bill from company
   - User wants to PAY someone (company/vendor) who sent an invoice
   
2. **internal_transfer**: Moving funds between clubs
   - Keywords: transfer, send to another club, joint event, collaboration
   - Moving money between LBS clubs or to SA
   
3. **expense_reimbursement**: Already paid out-of-pocket
   - Keywords: reimburse, paid already, used personal card, need money back, have receipt
   - User ALREADY spent their own money and wants refund
   
4. **refund_request**: Member wants money back (ticket/fee cancellation)
   - Keywords: refund, cancel ticket, membership refund, want money back, paid in error
   - A MEMBER wants their money back (not treasurer reimbursement)

Return ONLY JSON: {"form_type": "expense_reimbursement", "confidence": 0.95, "reasoning": "User said they already paid"}
"""
        
        try:
            response = self.api_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Classify this request: {message}"}
                ],
                temperature=0.0,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"Form classification: {result.get('form_type')} (confidence: {result.get('confidence')})")
            return result
        
        except Exception as e:
            logger.error(f"Form classification error: {e}")
            return None
    
    def _extract_data_agent(self, message: str) -> Dict:
        """
        AGENT 3: Extract data based on form type
        Uses form-specific field definitions if available
        """
        
        # Build dynamic prompt based on form type
        if self.form_specific_fields and "fields" in self.form_specific_fields:
            fields_to_extract = list(self.form_specific_fields["fields"].keys())
            field_descriptions = {
                name: field.get("description", "")
                for name, field in self.form_specific_fields["fields"].items()
            }
        else:
            # Fallback to generic fields
            fields_to_extract = ["amount", "date", "description", "vendor", "currency"]
            field_descriptions = {}
        
        fields_prompt = "\n".join([
            f"- {field}: {field_descriptions.get(field, field.replace('_', ' '))}"
            for field in fields_to_extract
        ])
        
        system_prompt = f"""You are a financial data extraction system for {self.form_type or 'finance'} requests.

Extract these fields from the user's message:
{fields_prompt}

Rules:
- Extract ONLY fields explicitly mentioned or strongly implied
- Use format: dates as YYYY-MM-DD, amounts as numbers (no currency symbols)
- If unsure, omit the field (don't guess)
- Currency defaults to "GBP" if not specified

Return ONLY valid JSON:
{{
    "fields": {{"amount": 180.0, "vendor": "Restaurant ABC", ...}},
    "confidence": {{"amount": 0.95, "vendor": 0.87, ...}}
}}

For missing/unclear fields, omit from "fields" object."""
        
        try:
            response = self.api_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.2,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"Extracted fields: {list(result.get('fields', {}).keys())}")
            return result
        
        except Exception as e:
            logger.error(f"Data extraction error: {e}")
            return {"fields": {}, "confidence": {}}
        """Call LLM to extract structured data from natural language"""
        
        system_prompt = """You are a financial data extraction system. Extract the following fields from user messages:
        - amount (number, in GBP)
        - currency (default GBP)
        - date (YYYY-MM-DD format)
        - description (what the expense/request is for)
        - vendor (who they paid or company name)
        - budget_line (which budget category)
        - justification (why, if budget-related)
        - event_name (if event-related)
        - attendees (number, if event-related)
        
        Return ONLY valid JSON with this structure:
        {
            "fields": {
                "amount": 180.0,
                "vendor": "Restaurant ABC",
                "date": "2025-11-20",
                ...
            },
            "confidence": {
                "amount": 0.95,
                "vendor": 0.87,
                ...
            }
        }
        
        For fields you cannot extract, omit them from "fields" object.
        If confidence is low, set to low value (0.1-0.5)."""
        
        try:
            response = self.api_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.2,
                max_tokens=400,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"Extracted data: {result['fields'].keys()}")
            return result
        
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return {"fields": {}, "confidence": {}}
    
    def _classify_form_type(self) -> Optional[str]:
        """Determine which form type this request is for"""
        
        if not self.extracted_data:
            return None
        
        system_prompt = """Classify this financial request into ONE of these types:
        - reimbursement: "I spent money and need it back"
        - budget_approval: "I want to adjust/approve a budget"
        - transfer: "Move money between accounts/clubs"
        - event: "Approve or book an event"
        
        Look for keywords like:
        - reimbursement: reimburse, refund, money back, paid for
        - budget: budget, allocation, funds, approval
        - transfer: transfer, move, send, from...to
        - event: event, booking, conference, meeting
        
        Return ONLY JSON: {"form_type": "reimbursement", "confidence": 0.95}"""
        
        data_summary = json.dumps(self.extracted_data, indent=2)
        
        try:
            response = self.api_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Data: {data_summary}"}
                ],
                temperature=0.0,
                max_tokens=100,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            form_type = result.get("form_type")
            logger.info(f"Classified form type: {form_type}")
            return form_type
        
        except Exception as e:
            logger.error(f"Form classification error: {e}")
            return None
    
    def _generate_question(self, missing_field: str) -> str:
        """Ask for a specific missing field"""
        
        questions = {
            "amount": "How much was/is the expense? (Please provide in £)",
            "date": "What is the date? (Format: YYYY-MM-DD, e.g., 2025-11-20)",
            "vendor": "Who did you pay or what company was this for?",
            "description": "Can you briefly describe what this was for?",
            "budget_line": "Which budget category does this belong to? (Event Costs, Supplies, Travel, or Speaker Fees)",
            "justification": "Can you explain why this budget adjustment is needed?",
            "event_name": "What is the name of the event?",
            "attendees": "How many people are expected to attend?",
            "from_account": "Which account should this transfer come from?",
            "to_account": "Which account should this go to?"
        }
        
        question = questions.get(missing_field, f"Can you provide the {missing_field}?")
        return f"**{question}**"
    
    def _generate_summary(self) -> str:
        """Generate a summary when all data is collected"""
        
        summary = "\n\n## 📋 Request Summary\n"
        summary += f"**Type:** {self.form_type}\n"
        summary += f"**Request ID:** {self.request_id}\n\n"
        summary += "### Details:\n"
        
        if "amount" in self.extracted_data:
            summary += f"- **Amount:** £{self.extracted_data['amount']}\n"
        if "date" in self.extracted_data:
            summary += f"- **Date:** {self.extracted_data['date']}\n"
        if "vendor" in self.extracted_data:
            summary += f"- **Vendor:** {self.extracted_data['vendor']}\n"
        if "description" in self.extracted_data:
            summary += f"- **Description:** {self.extracted_data['description']}\n"
        if "budget_line" in self.extracted_data:
            summary += f"- **Budget Line:** {self.extracted_data['budget_line']}\n"
        if "event_name" in self.extracted_data:
            summary += f"- **Event:** {self.extracted_data['event_name']}\n"
        
        summary += "\n**Does this look correct?** Reply 'yes' to proceed or 'no' to edit"
        
        return summary
    
    def _calculate_overall_confidence(self) -> float:
        """Average confidence across extracted fields"""
        
        if not self.confidence_scores:
            return 0.0
        
        return min(1.0, sum(self.confidence_scores.values()) / len(self.confidence_scores))
    
    def get_conversation_state(self) -> Dict:
        """Get current state for saving/debugging"""
        return {
            "request_id": self.request_id,
            "history": self.history,
            "extracted_data": self.extracted_data,
            "form_type": self.form_type,
            "missing_fields": self.missing_fields,
            "confidence_scores": self.confidence_scores
        }
