"""Conversation Manager - Multi-Agent System with Dynamic Rule Loading"""

import json
import logging
from typing import Dict, Optional
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
        self.extracted_data = {
            "club_name": "Data and AI Club",  # Hard-coded
            "treasurer_email": "abc@123.com",  # Hard-coded
            "club_treasurer_email": "abc@123.com",  # For expense reimbursement
            "location": "London",  # Hard-coded for Infor XM
            "payment_type": "Cash",  # Hard-coded for Infor XM
            "charge_allocation_percentage": 100,  # Hard-coded for Infor XM
            "initiating_club_name": "Data and AI Club",  # Hard-coded for internal transfer
            "email": "abc@123.com",  # Hard-coded for refund request
            "invoice_type": "Final Invoice",  # Hard-coded for vendor payment
            "currency": "GBP",  # Hard-coded for all forms (pounds)
            "invoice_currency": "GBP",  # Hard-coded for vendor payment
            "transfer_amount_currency": "GBP"  # Hard-coded for internal transfer (if needed)
        }
        self.form_type = None
        self.form_type_confirmed = False  # New: Track if user confirmed form type
        self.form_specific_rules = None
        self.form_specific_fields = None
        self.required_fields = []
        self.missing_fields = []
        self.validation_status = {}
        self.confidence_scores = {}
        self.request_id = generate_request_id()
        self.classification_attempted = False
        self.current_agent = "initial_gathering"  # New: Track current agent for UI display
        self.suggested_form_type = None  # New: Store suggestion before confirmation
    
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
            
            # Load event codes for auto-suggestion
            try:
                import pandas as pd
                event_codes_path = get_config_path("../event_codes.csv")
                self.event_codes_df = pd.read_csv(event_codes_path)
                logger.info(f"Loaded {len(self.event_codes_df)} event codes for auto-suggestion")
            except Exception as e:
                logger.warning(f"Could not load event codes: {e}")
                self.event_codes_df = None
            
            logger.info("Base rules loaded successfully")
        except Exception as e:
            logger.error(f"Error loading base rules: {e}")
            self.base_rules = {}
            self.form_classification_criteria = {}
            self.event_codes_df = None
    
    def load_form_specific_rules(self, form_type: str):
        """Dynamically load rules and fields for the classified form type"""
        try:
            # Load form-specific rules
            all_rules = load_json(get_config_path("lbs_rules_extracted.json"))
            form_rules = all_rules.get("transaction_types", {}).get(form_type, {})
            
            # Load form-specific fields (use form_type directly as key)
            all_fields = load_json(get_config_path("form_fields.json"))
            form_fields = all_fields.get(form_type, {})
            
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
        
        Agent Flow:
        1. AGENT 0 (Initial Gathering): Gather initial info and detect request type
        2. Ask user to CONFIRM form type
        3. AGENT 1-4 (Form-Specific): Collect form-specific fields based on confirmed type
           - Agent 1: Supplier Payment
           - Agent 2: Internal Transfer  
           - Agent 3: Expense Reimbursement
           - Agent 4: Refund Request
        5. AGENT 5 (Validation): Flag issues and validate before submission
        
        Returns dictionary with response and extracted data
        """
        # Add to history
        self.history.append({
            "role": "user",
            "content": user_message
        })
        
        # Check if user says they don't have some information
        lacks_info_response = self._check_lacks_information(user_message)
        if lacks_info_response:
            self.history.append({
                "role": "assistant",
                "content": lacks_info_response
            })
            return {
                "response": lacks_info_response,
                "extracted_data": self.extracted_data.copy(),
                "complete": False,
                "form_type": self.form_type,
                "suggested_form_type": self.suggested_form_type,
                "form_type_confirmed": self.form_type_confirmed,
                "missing_fields": self.missing_fields,
                "validation_status": self.validation_status,
                "confidence": self._calculate_overall_confidence(),
                "request_id": self.request_id,
                "current_agent": self.current_agent,
                "agent_status": self._get_agent_status_display()
            }
        
        # Check if user is confirming a suggested form type
        if self.suggested_form_type and not self.form_type_confirmed:
            confirmation = self._check_user_confirmation(user_message)
            if confirmation == "yes":
                # User confirmed the form type
                self.form_type = self.suggested_form_type
                self.form_type_confirmed = True
                self.suggested_form_type = None
                
                # Load form-specific rules and fields
                self.load_form_specific_rules(self.form_type)
                self.current_agent = f"form_collection_{self.form_type}"
                
                # Update missing fields list now that we have required fields
                self.missing_fields = [
                    field for field in self.required_fields
                    if field not in self.extracted_data or not self.extracted_data[field]
                ]
                
                logger.info(f"✅ User confirmed form type: {self.form_type}")
                
                # Generate response to start collecting fields
                agent_response = self._generate_contextual_response()
                
            elif confirmation == "no":
                # User rejected suggestion - try to detect what they actually want
                corrected_type = self._detect_form_type_from_correction(user_message)
                
                if corrected_type:
                    # User explicitly stated the form type (e.g., "it's vendor payment")
                    self.form_type = corrected_type
                    self.form_type_confirmed = True
                    self.suggested_form_type = None
                    self.load_form_specific_rules(self.form_type)
                    self.current_agent = f"form_collection_{self.form_type}"
                    
                    # Update missing fields list
                    self.missing_fields = [
                        field for field in self.required_fields
                        if field not in self.extracted_data or not self.extracted_data[field]
                    ]
                    
                    logger.info(f"✅ User corrected to form type: {self.form_type}")
                    agent_response = self._generate_contextual_response()
                else:
                    # User rejected but didn't specify - ask for clarification
                    self.suggested_form_type = None
                    self.current_agent = "initial_gathering"
                    agent_response = "I understand. Which type of request is this?\n\n" \
                                   "1. **Vendor Payment** - Paying an external company/vendor for an invoice\n" \
                                   "2. **Internal Transfer** - Moving funds between LBS clubs\n" \
                                   "3. **Expense Reimbursement** - Getting reimbursed for money you already spent\n" \
                                   "4. **Member Refund** - Refunding a member for tickets/fees\n\n" \
                                   "You can reply with the number or name."
            else:
                # Unclear response, ask again
                agent_response = f"Just to confirm - is this a **{self._get_form_display_name(self.suggested_form_type)}** request? Please answer 'yes' or 'no'."
        
        # AGENT 0: Initial gathering and form type detection
        elif not self.form_type_confirmed and not self.suggested_form_type:
            self.current_agent = "initial_gathering"
            
            # Try to detect form type from user message
            classification_result = self._classify_form_type_agent(user_message)
            
            if classification_result and classification_result.get("confidence", 0) > 0.7:
                # We have a confident classification - ask user to confirm
                self.suggested_form_type = classification_result["form_type"]
                
                form_display_name = self._get_form_display_name(self.suggested_form_type)
                reasoning = classification_result.get("reasoning", "")
                
                agent_response = f"Based on what you've described, it looks like you need a **{form_display_name}** form.\n\n" \
                               f"Is that correct? (Please reply 'yes' to proceed or 'no' if I misunderstood)"
            else:
                # Not confident enough, ask clarifying questions
                agent_response = "I'd like to help you with your finance request. What type of transaction is this?\n\n" \
                               "Please choose one:\n" \
                               "1. **Vendor Payment** - Paying an external company/vendor for an invoice\n" \
                               "2. **Internal Transfer** - Moving funds between LBS clubs\n" \
                               "3. **Expense Reimbursement** - Getting reimbursed for money you already spent\n" \
                               "4. **Member Refund** - Refunding a member for tickets/fees\n\n" \
                               "You can reply with the number or name."
        
        # AGENT 1-4: Form-specific data collection
        elif self.form_type_confirmed and self.form_type:
            self.current_agent = f"form_collection_{self.form_type}"
            
            # Extract data using form-specific agent
            extraction_result = self._extract_data_agent(user_message)
            self.extracted_data.update(extraction_result.get("fields", {}))
            self.confidence_scores.update(extraction_result.get("confidence", {}))
            
            # Auto-suggest event code if club name is present
            if self.event_codes_df is not None:
                suggested_code = self._suggest_event_code()
                if suggested_code and "event_code" not in self.extracted_data:
                    self.extracted_data["event_code"] = suggested_code["code"]
                    self.confidence_scores["event_code"] = suggested_code["confidence"]
                    logger.info(f"Auto-suggested event code: {suggested_code['code']} (confidence: {suggested_code['confidence']})")
            
            # Update missing fields
            self.missing_fields = [
                field for field in self.required_fields
                if field not in self.extracted_data or not self.extracted_data[field]
            ]
            
            # If all fields collected, move to validation
            if not self.missing_fields:
                self.current_agent = "validation"
            
            # Generate appropriate response
            agent_response = self._generate_contextual_response()
        
        else:
            # Fallback - shouldn't reach here
            agent_response = "I'm not sure I understand. Can you describe what you need help with?"
        
        # AGENT 5: Validation (runs automatically when all fields are collected)
        if not self.missing_fields and self.form_type_confirmed:
            self.current_agent = "validation"
            validation_result = self._validate_against_rules_agent()
            self.validation_status = validation_result
        else:
            validation_result = {"can_submit": False, "warnings": [], "errors": []}
            self.validation_status = validation_result
        
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
            "suggested_form_type": self.suggested_form_type,
            "form_type_confirmed": self.form_type_confirmed,
            "missing_fields": self.missing_fields,
            "validation_status": validation_result,
            "confidence": self._calculate_overall_confidence(),
            "request_id": self.request_id,
            "current_agent": self.current_agent,  # For UI display
            "agent_status": self._get_agent_status_display()  # Human-readable status
        }
    
    def _check_user_confirmation(self, message: str) -> str:
        """
        Check if user is confirming or rejecting the suggested form type
        
        Returns: "yes", "no", or "unclear"
        """
        message_lower = message.lower().strip()
        
        # Check for affirmative responses
        yes_keywords = ["yes", "yeah", "yep", "correct", "right", "that's right", "confirm", "ok", "okay", "sure", "1", "proceed"]
        if any(keyword in message_lower for keyword in yes_keywords):
            return "yes"
        
        # Check for negative responses
        no_keywords = ["no", "nope", "wrong", "incorrect", "not right", "different", "2", "3", "4"]
        if any(keyword in message_lower for keyword in no_keywords):
            return "no"
        
        return "unclear"
    
    def _check_lacks_information(self, message: str) -> Optional[str]:
        """
        Check if user says they don't have some information
        If so, provide treasurer email for them to contact
        
        Returns: Response string if user lacks info, None otherwise
        """
        message_lower = message.lower().strip()
        
        # Keywords indicating user doesn't have information
        lacks_info_keywords = [
            "don't have", "dont have", "do not have",
            "don't know", "dont know", "do not know",
            "not sure", "unsure", "no idea",
            "missing", "don't remember", "can't find",
            "cannot find", "not available", "unavailable",
            "i dont", "i don't", "idk"
        ]
        
        if any(keyword in message_lower for keyword in lacks_info_keywords):
            treasurer_email = self.extracted_data.get("treasurer_email", "abc@123.com")
            return (
                f"No problem! If you don't have this information readily available, "
                f"please reach out to the treasurer at **{treasurer_email}** for assistance.\n\n"
                f"They can help you get the missing details you need to complete your request. "
                f"Feel free to continue when you have the information! 📧"
            )
        
        return None
    
    def _detect_form_type_from_correction(self, message: str) -> Optional[str]:
        """
        Detect form type when user corrects our suggestion
        e.g., "No, it's vendor payment" or "It's expense reimbursement"
        
        Returns: form_type string or None
        """
        message_lower = message.lower().strip()
        
        # Check for explicit form type mentions
        if any(keyword in message_lower for keyword in ["vendor", "supplier", "invoice", "payment to vendor", "paying vendor", "paying supplier"]):
            return "supplier_payment"
        elif any(keyword in message_lower for keyword in ["transfer", "internal", "between clubs", "club to club"]):
            return "internal_transfer"
        elif any(keyword in message_lower for keyword in ["reimbursement", "reimburse", "expense", "spent", "paid out of pocket", "already paid"]):
            return "expense_reimbursement"
        elif any(keyword in message_lower for keyword in ["refund", "member refund", "ticket refund"]):
            return "refund_request"
        
        # Check for numbered responses (1-4)
        if message_lower in ["1", "one", "first"]:
            return "supplier_payment"
        elif message_lower in ["2", "two", "second"]:
            return "internal_transfer"
        elif message_lower in ["3", "three", "third"]:
            return "expense_reimbursement"
        elif message_lower in ["4", "four", "fourth"]:
            return "refund_request"
        
        return None
    
    def _get_form_display_name(self, form_type: str) -> str:
        """Get human-readable form name"""
        form_names = {
            "supplier_payment": "Vendor Payment",
            "internal_transfer": "Internal Transfer",
            "expense_reimbursement": "Expense Reimbursement",
            "refund_request": "Member Refund"
        }
        return form_names.get(form_type, form_type)
    
    def _get_agent_status_display(self) -> str:
        """Get human-readable status for UI display"""
        if self.current_agent == "initial_gathering":
            if self.suggested_form_type:
                return f"🤔 Confirming Request Type: {self._get_form_display_name(self.suggested_form_type)}"
            return "🔍 Understanding Your Request"
        
        elif self.current_agent.startswith("form_collection_"):
            form_name = self._get_form_display_name(self.form_type)
            if self.missing_fields:
                return f"📝 Collecting Details for {form_name} ({len(self.extracted_data)}/{len(self.required_fields)} fields)"
            return f"📝 Collecting Details for {form_name}"
        
        elif self.current_agent == "validation":
            if self.validation_status.get("can_submit"):
                return "✅ Validation Complete - Ready to Submit"
            elif self.validation_status.get("errors"):
                return "⚠️ Validation Issues Found"
            return "🔍 Validating Your Request"
        
        return "💬 Processing..."
    
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
    
    def _suggest_event_code(self) -> Optional[Dict]:
        """
        Suggest event code based on extracted club name and event type
        
        Returns: {"code": "E001", "confidence": 0.85, "club_match": "Finance Club"} or None
        """
        if self.event_codes_df is None or self.event_codes_df.empty:
            return None
        
        club_name = self.extracted_data.get("club_name", "")
        event_name = self.extracted_data.get("event_name", "")
        
        if not club_name:
            return None
        
        # Strategy 1: Try exact club name + event name match
        if event_name:
            exact_matches = self.event_codes_df[
                (self.event_codes_df['club_name'].str.lower() == club_name.lower()) &
                (self.event_codes_df['event_name'].str.lower().str.contains(event_name.lower(), na=False))
            ]
            if not exact_matches.empty:
                best_match = exact_matches.iloc[0]
                return {
                    "code": best_match['event_code'],
                    "confidence": 0.95,
                    "club_match": best_match['club_name'],
                    "event_match": best_match['event_name']
                }
        
        # Strategy 2: Fuzzy match club name
        from difflib import get_close_matches
        all_club_names = self.event_codes_df['club_name'].unique().tolist()
        close_club_matches = get_close_matches(club_name, all_club_names, n=1, cutoff=0.6)
        
        if close_club_matches:
            matched_club = close_club_matches[0]
            club_codes = self.event_codes_df[self.event_codes_df['club_name'] == matched_club]
            
            # Strategy 3: Look for "Operating Costs" or general event for the club
            operating_costs = club_codes[
                club_codes['event_name'].str.lower().str.contains('operating|general|costs', regex=True, na=False)
            ]
            
            if not operating_costs.empty:
                best_match = operating_costs.iloc[0]
                confidence = 0.8 if matched_club == club_name else 0.7
                return {
                    "code": best_match['event_code'],
                    "confidence": confidence,
                    "club_match": matched_club,
                    "event_match": best_match['event_name']
                }
            
            # Strategy 4: Return first code for matched club
            if not club_codes.empty:
                best_match = club_codes.iloc[0]
                confidence = 0.75 if matched_club == club_name else 0.65
                return {
                    "code": best_match['event_code'],
                    "confidence": confidence,
                    "club_match": matched_club,
                    "event_match": best_match['event_name']
                }
        
        return None
    
    def _validate_against_rules_agent(self) -> Dict:
        """
        AGENT 4: Validate current data against form-specific rules
        Returns validation status and warnings
        """
        
        validation = {
            "can_submit": False,
            "warnings": [],
            "errors": [],
            "pre_approval_required": False
        }
        
        if not self.form_type or not self.form_specific_rules:
            return validation
        
        # Check if all required fields are present
        if self.missing_fields:
            validation["errors"].append(f"Missing required fields: {', '.join(self.missing_fields)}")
            return validation
        
        # Form-specific validation rules
        if self.form_type == "supplier_payment":
            amount = self.extracted_data.get("amount", 0)
            if amount > self.form_specific_rules.get("pre_approval_threshold", 8000):
                validation["pre_approval_required"] = True
                validation["warnings"].append(
                    f"⚠️ Supplier invoices over £8,000 require SA Senior Treasurer pre-approval"
                )
        
        elif self.form_type == "expense_reimbursement":
            amount = self.extracted_data.get("amount", 0)
            attendees = self.extracted_data.get("number_of_attendees", 1)
            
            # Check reimbursement limit
            if amount > self.form_specific_rules.get("pre_approval_threshold", 1000):
                validation["pre_approval_required"] = True
                validation["warnings"].append(
                    f"⚠️ Reimbursements over £1,000 require SA Senior Treasurer pre-approval"
                )
            
            # Check social per-head limit
            if self.extracted_data.get("is_social_event", False) and attendees > 0:
                per_head = amount / attendees
                if per_head > 45:
                    validation["errors"].append(
                        f"❌ Social events limited to £45 per head (current: £{per_head:.2f})"
                    )
        
        # Validate event code exists in directory (applies to all forms)
        event_code = self.extracted_data.get("event_code") or self.extracted_data.get("event_finance_code") or self.extracted_data.get("initiating_club_event_code")
        if event_code and self.event_codes_df is not None:
            valid_codes = self.event_codes_df['event_code'].tolist()
            if event_code not in valid_codes:
                validation["errors"].append(
                    f"❌ Invalid event code '{event_code}'. Must use code from Event Code Directory."
                )
                validation["warnings"].append(
                    "💡 Ask your treasurer for the correct event code, or I can suggest one based on your club."
                )
        
        # If no errors, can submit
        if not validation["errors"]:
            validation["can_submit"] = True
        
        return validation
    
    def _get_field_groups(self) -> list:
        """
        Group fields logically for progressive questioning (3-4 fields at a time)
        Returns list of field groups based on form type
        """
        field_groups = {
            "expense_reimbursement": [
                # Group 1: Basic transaction info (what & when)
                ["expense_date", "total_claim_amount", "currency"],
                # Group 2: Where purchased (merchant & event)
                ["merchant_name", "expense_description", "event_code"],
                # Group 3: Supporting documents
                ["receipt_upload"]
            ],
            "supplier_payment": [
                # Group 1: Vendor & invoice basics
                ["vendor_name", "invoice_number", "total_amount"],
                # Group 2: Event & description
                ["event_code", "invoice_description"],
                # Group 3: Supporting documents
                ["invoice_upload"]
            ],
            "internal_transfer": [
                # Group 1: Transfer basics
                ["recipient_club", "transfer_amount", "event_code"],
                # Group 2: Purpose & details
                ["transfer_purpose", "transfer_date"]
            ],
            "refund_request": [
                # Group 1: Member & amount
                ["member_name", "member_email", "refund_amount"],
                # Group 2: Reason & event
                ["refund_reason", "event_code", "original_payment_date"]
            ]
        }
        
        return field_groups.get(self.form_type, [])
    
    def _get_current_field_group(self) -> list:
        """
        Get the next group of fields to ask for based on what's already collected
        """
        field_groups = self._get_field_groups()
        if not field_groups:
            # No grouping defined, return all missing fields
            return self.missing_fields
        
        # Find first group with missing fields
        for group in field_groups:
            group_missing = [f for f in group if f in self.missing_fields]
            if group_missing:
                return group_missing
        
        # All groups complete, return any remaining missing fields
        return self.missing_fields

    def _generate_contextual_response(self) -> str:
        """
        Generate contextual response based on current state
        """
        
        # Case 1: Form type not yet classified
        if not self.form_type:
            return (
                "👋 Hi! I'll help you submit your finance request for the Data and AI Club. "
                "Can you describe what you need? For example:\n"
                "- 'I need to be reimbursed for...'\n"
                "- 'I have an invoice from...'\n"
                "- 'I want to transfer funds to...'\n"
                "- 'A member needs a refund for...'"
            )
        
        # Case 2: Form classified, missing fields - ask in groups of 3-4
        if self.missing_fields:
            # Get current field group to ask for
            current_group = self._get_current_field_group()
            
            # Get field descriptions for current group
            group_field_info = []
            for field in current_group:
                field_def = None
                if self.form_specific_fields and "fields" in self.form_specific_fields:
                    field_def = self.form_specific_fields["fields"].get(field, {})
                
                if field_def and "description" in field_def:
                    group_field_info.append(f"• **{field_def['description']}**")
                else:
                    # Fallback to readable field name
                    readable_name = field.replace('_', ' ').title()
                    group_field_info.append(f"• **{readable_name}**")
            
            # Count non-hard-coded collected fields
            collected_count = len([k for k in self.extracted_data.keys() 
                                  if k not in ["club_name", "treasurer_email", "club_treasurer_email", 
                                              "location", "payment_type", "charge_allocation_percentage"]])
            
            # Add form type context on first question
            if collected_count == 0:
                form_names = {
                    "supplier_payment": "Vendor Payment",
                    "internal_transfer": "Internal Transfer",
                    "expense_reimbursement": "Expense Reimbursement",
                    "refund_request": "Refund Request"
                }
                form_name = form_names.get(self.form_type, self.form_type)
                
                response = f"✅ Great! I'll help you with a **{form_name}** request for the Data and AI Club.\n\n"
                response += "📋 Let's start with the basics:\n\n"
                response += "\n".join(group_field_info)
                response += "\n\n💬 Please provide the information above. You can give multiple details at once if you have them!"
                return response
            else:
                # Subsequent questions - show progress and next group
                total_required = len(self.required_fields)
                total_collected = len([f for f in self.required_fields if f not in self.missing_fields])
                
                response = f"👍 Great progress! ({total_collected}/{total_required} fields collected)\n\n"
                response += "📋 Next, I need:\n\n"
                response += "\n".join(group_field_info)
                response += "\n\n💬 Please provide these details."
                return response
        
        # Case 3: All fields collected, generate summary with validation
        return self._generate_summary_with_validation()
    
    def _generate_field_question(self, field: str) -> str:
        """Generate question for a specific field based on form context"""
        
        # Get field definition if available
        field_def = None
        if self.form_specific_fields and "fields" in self.form_specific_fields:
            field_def = self.form_specific_fields["fields"].get(field, {})
        
        # Use field description if available
        if field_def and "description" in field_def:
            return f"**{field_def['description']}**"
        
        # Fallback generic questions
        questions = {
            "finance_code": "What is the finance/event code for this transaction?",
            "amount": "What is the total amount? (in £)",
            "date": "What is the date? (Format: YYYY-MM-DD, e.g., 2025-11-20)",
            "vendor_name": "What is the vendor/supplier name?",
            "invoice_number": "What is the invoice number?",
            "description": "Can you describe what this is for?",
            "event_description": "What event or activity is this for?",
            "merchant_name": "Where did you make this purchase?",
            "number_of_attendees": "How many people attended?",
            "is_social_event": "Is this a social event? (yes/no)",
            "receipt_attachment": "Please upload the itemized receipt",
            "member_name": "What is the member's name?",
            "refund_reason": "What is the reason for the refund?"
        }
        
        return questions.get(field, f"Can you provide the **{field.replace('_', ' ')}**?")
    
    def _generate_summary_with_validation(self) -> str:
        """Generate summary with validation warnings"""
        
        form_names = {
            "supplier_payment": "Supplier Payment",
            "internal_transfer": "Internal Transfer",
            "expense_reimbursement": "Expense Reimbursement",
            "refund_request": "Refund Request"
        }
        
        summary = f"\n\n## 📋 {form_names.get(self.form_type, 'Request')} Summary\n"
        summary += f"**Request ID:** {self.request_id}\n\n"
        
        # Show extracted data
        summary += "### Details:\n"
        for field, value in self.extracted_data.items():
            display_name = field.replace('_', ' ').title()
            if field == "amount":
                summary += f"- **{display_name}:** £{value}\n"
            elif isinstance(value, bool):
                summary += f"- **{display_name}:** {'Yes' if value else 'No'}\n"
            else:
                summary += f"- **{display_name}:** {value}\n"
        
        # Add validation status
        if self.validation_status.get("pre_approval_required"):
            summary += "\n### ⚠️ Pre-Approval Required\n"
            for warning in self.validation_status.get("warnings", []):
                summary += f"{warning}\n"
        
        if self.validation_status.get("errors"):
            summary += "\n### ❌ Issues to Fix\n"
            for error in self.validation_status.get("errors", []):
                summary += f"{error}\n"
            summary += "\nPlease correct the above issues before submitting."
        elif self.validation_status.get("can_submit"):
            summary += "\n✅ **Ready to submit!** Click the 'Submit for Treasurer Review' button below."
        
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
            "validation_status": self.validation_status,
            "confidence_scores": self.confidence_scores
        }
