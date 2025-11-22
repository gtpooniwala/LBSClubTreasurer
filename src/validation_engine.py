"""Validation Engine - Checks extracted data against finance rules"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict
from src.utils import load_json, get_config_path

logger = logging.getLogger(__name__)


class ValidationEngine:
    """Validates extracted data against finance rules"""
    
    def __init__(self):
        self.rules = load_json(get_config_path("rules.json"))
        self.schemas = load_json(get_config_path("forms_schema.json"))
    
    def validate(self, data: Dict, form_type: str) -> Dict:
        """
        Validate data against all applicable rules
        
        Returns validation result with violations and score
        """
        
        violations = []
        warnings = []
        
        # Amount checks
        if "amount" in data and form_type in self.schemas:
            amount_violations = self._check_amount(
                data["amount"],
                form_type
            )
            violations.extend(amount_violations)
        
        # Budget checks
        if "budget_line" in data:
            budget_result = self._check_budget(
                data["budget_line"],
                data.get("amount", 0)
            )
            violations.extend(budget_result["violations"])
            warnings.extend(budget_result["warnings"])
        
        # Receipt checks
        if "amount" in data and data["amount"] > 50:
            if "receipt" not in data or not data["receipt"]:
                violations.append({
                    "rule": "receipt_required",
                    "severity": "error",
                    "message": f"Receipt required for amounts over £50 (you have £{data['amount']})"
                })
        
        # Date checks
        if "date" in data:
            date_violations = self._check_date(data["date"])
            violations.extend(date_violations)
        
        # Completeness check
        if form_type in self.schemas:
            required_fields = self.schemas[form_type].get("required_fields", [])
            missing = [f for f in required_fields if f not in data or not data[f]]
            if missing:
                violations.append({
                    "rule": "incomplete_data",
                    "severity": "error",
                    "message": f"Missing required fields: {', '.join(missing)}"
                })
        
        # Calculate score
        error_count = len([v for v in violations if v["severity"] == "error"])
        warning_count = len(warnings)
        total_checks = 8
        score = max(0, (total_checks - error_count - warning_count * 0.5) / total_checks)
        
        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "score": min(1.0, score),
            "total_checks": len(violations) + len(warnings)
        }
    
    def _check_amount(self, amount: float, form_type: str) -> list:
        """Check amount validity and limits"""
        violations = []
        
        limits = self.rules.get("amount_limits", {})
        
        # Basic validation
        if amount <= 0:
            violations.append({
                "rule": "invalid_amount",
                "severity": "error",
                "message": "Amount must be greater than £0"
            })
            return violations
        
        # Type-specific limits
        if form_type == "reimbursement":
            max_single = limits.get("reimbursement_max_single", 500)
            if amount > max_single:
                violations.append({
                    "rule": "amount_single_limit",
                    "severity": "error",
                    "message": f"Reimbursement amount exceeds maximum of £{max_single}"
                })
        
        return violations
    
    def _check_budget(self, budget_line: str, amount: float) -> Dict:
        """Check budget availability"""
        violations = []
        warnings = []
        
        budgets = self.rules.get("budget_lines", {})
        
        if budget_line not in budgets:
            violations.append({
                "rule": "invalid_budget_line",
                "severity": "error",
                "message": f"Unknown budget line: {budget_line}"
            })
            return {"violations": violations, "warnings": warnings}
        
        # Calculate spent amount from transactions
        spent = self._calculate_spent(budget_line)
        total = budgets[budget_line].get("total", 0)
        available = total - spent
        
        if amount > available:
            violations.append({
                "rule": "budget_insufficient",
                "severity": "error",
                "message": f"Insufficient budget. Available: £{available:.2f}, Requested: £{amount:.2f}"
            })
        elif amount > available * 0.75:
            warnings.append({
                "rule": "budget_high_usage",
                "severity": "warning",
                "message": f"This request uses {(amount/total)*100:.0f}% of total budget"
            })
        
        return {"violations": violations, "warnings": warnings}
    
    def _check_date(self, date_str: str) -> list:
        """Check date validity and recency"""
        violations = []
        
        # Try to parse date
        formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
        request_date = None
        
        for fmt in formats:
            try:
                request_date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue
        
        if not request_date:
            violations.append({
                "rule": "invalid_date",
                "severity": "error",
                "message": f"Invalid date format. Use YYYY-MM-DD (e.g., 2025-11-20)"
            })
            return violations
        
        today = datetime.now()
        days_old = (today - request_date).days
        
        if days_old > 30:
            violations.append({
                "rule": "date_too_old",
                "severity": "error",
                "message": f"Reimbursement requests must be within 30 days (this is {days_old} days old)"
            })
        
        if request_date > today:
            violations.append({
                "rule": "date_future",
                "severity": "error",
                "message": "Date cannot be in the future"
            })
        
        return violations
    
    def _calculate_spent(self, budget_line: str) -> float:
        """Calculate total spent in a budget line from CSV"""
        spent = 0.0
        
        csv_path = "data/transactions.csv"
        if os.path.exists(csv_path):
            try:
                with open(csv_path, 'r') as f:
                    lines = f.readlines()
                    # Skip header
                    for line in lines[1:]:
                        try:
                            parts = line.strip().split(',')
                            if len(parts) > 3 and parts[6].strip() == budget_line:  # budget_line column
                                if parts[5].strip() in ["completed", "approved"]:  # status column
                                    spent += float(parts[4])  # amount column
                        except (ValueError, IndexError):
                            continue
            except Exception as e:
                logger.error(f"Error calculating spent: {e}")
        
        return spent
    
    def get_validation_summary(self, validation_result: Dict) -> str:
        """Get human-readable validation summary"""
        
        summary = ""
        
        if validation_result["passed"]:
            summary = "✅ **All validations passed!**\n"
        else:
            summary = "⚠️ **Validation Issues Found:**\n"
            for v in validation_result["violations"]:
                if v["severity"] == "error":
                    summary += f"- ❌ {v['message']}\n"
        
        for w in validation_result["warnings"]:
            summary += f"- ⚠️ {w['message']}\n"
        
        return summary
