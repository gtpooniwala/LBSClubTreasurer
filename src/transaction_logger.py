"""Transaction Logger - Stores and manages transaction data"""

import json
import logging
import os
import csv
from datetime import datetime
from typing import Dict, List
from pathlib import Path
from src.utils import save_json, load_json, get_config_path

logger = logging.getLogger(__name__)


class TransactionLogger:
    """Handles logging of transactions to JSON and CSV"""
    
    def __init__(self, requests_dir: str = "data/requests", csv_path: str = "data/transactions.csv"):
        self.requests_dir = requests_dir
        self.csv_path = csv_path
        self._init_csv()
    
    def _init_csv(self):
        """Initialize CSV file if it doesn't exist"""
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "request_id", "date", "member_name", "type", "amount",
                    "description", "budget_line", "status", "treasurer",
                    "approved_at", "automation_status", "notes"
                ])
            logger.info(f"Initialized CSV at {self.csv_path}")
    
    def create_request(self, member_name: str, form_type: str, data: Dict) -> str:
        """Create a new request and save it"""
        
        request_id = data.get("request_id")
        if not request_id:
            from src.utils import generate_request_id
            request_id = generate_request_id()
        
        # Build full request object
        request_obj = {
            "metadata": {
                "request_id": request_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "status": "pending_review"
            },
            "member": {
                "name": member_name,
                "email": ""  # Could be added later
            },
            "request": {
                "type": form_type,
                **data
            },
            "validation": {},
            "treasurer_action": {},
            "automation": {},
            "audit_trail": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "action": "request_created",
                    "actor": "member"
                }
            ]
        }
        
        # Save to JSON
        json_path = os.path.join(self.requests_dir, f"{request_id}.json")
        Path(self.requests_dir).mkdir(parents=True, exist_ok=True)
        save_json(request_obj, json_path)
        
        # Add to CSV
        self._add_to_csv({
            "request_id": request_id,
            "date": data.get("date", ""),
            "member_name": member_name,
            "type": form_type,
            "amount": data.get("amount", 0),
            "description": data.get("description", ""),
            "budget_line": data.get("budget_line", ""),
            "status": "pending_review",
            "treasurer": "",
            "approved_at": "",
            "automation_status": "pending",
            "notes": ""
        })
        
        logger.info(f"Created request: {request_id}")
        return request_id
    
    def _add_to_csv(self, row_dict: Dict):
        """Add row to CSV"""
        try:
            with open(self.csv_path, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "request_id", "date", "member_name", "type", "amount",
                    "description", "budget_line", "status", "treasurer",
                    "approved_at", "automation_status", "notes"
                ])
                writer.writerow(row_dict)
        except Exception as e:
            logger.error(f"Error adding to CSV: {e}")
    
    def update_request_status(self, request_id: str, status: str, treasurer: str = "", notes: str = ""):
        """Update request status"""
        
        json_path = os.path.join(self.requests_dir, f"{request_id}.json")
        request_obj = load_json(json_path)
        
        if not request_obj:
            logger.error(f"Request not found: {request_id}")
            return False
        
        # Update JSON
        request_obj["metadata"]["status"] = status
        request_obj["metadata"]["updated_at"] = datetime.now().isoformat()
        request_obj["treasurer_action"]["decision"] = status
        request_obj["treasurer_action"]["approved_by"] = treasurer
        request_obj["treasurer_action"]["reviewed_at"] = datetime.now().isoformat()
        
        request_obj["audit_trail"].append({
            "timestamp": datetime.now().isoformat(),
            "action": status,
            "actor": "treasurer",
            "notes": notes
        })
        
        save_json(request_obj, json_path)
        
        # Update CSV
        self._update_csv_row(request_id, status, treasurer, notes)
        
        logger.info(f"Updated request {request_id} to {status}")
        return True
    
    def _update_csv_row(self, request_id: str, status: str, treasurer: str = "", notes: str = ""):
        """Update CSV row"""
        try:
            rows = []
            with open(self.csv_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["request_id"] == request_id:
                        row["status"] = status
                        row["treasurer"] = treasurer
                        row["approved_at"] = datetime.now().isoformat()
                        row["notes"] = notes
                    rows.append(row)
            
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "request_id", "date", "member_name", "type", "amount",
                    "description", "budget_line", "status", "treasurer",
                    "approved_at", "automation_status", "notes"
                ])
                writer.writeheader()
                writer.writerows(rows)
        except Exception as e:
            logger.error(f"Error updating CSV: {e}")
    
    def load_request(self, request_id: str) -> Dict:
        """Load a request from JSON"""
        json_path = os.path.join(self.requests_dir, f"{request_id}.json")
        return load_json(json_path)
    
    def get_all_requests(self) -> List[Dict]:
        """Get all requests"""
        requests = []
        if os.path.exists(self.requests_dir):
            for filename in os.listdir(self.requests_dir):
                if filename.endswith(".json"):
                    request_id = filename.replace(".json", "")
                    request_obj = self.load_request(request_id)
                    if request_obj:
                        requests.append(request_obj)
        return requests
    
    def get_pending_requests(self) -> List[Dict]:
        """Get pending requests"""
        all_requests = self.get_all_requests()
        return [r for r in all_requests if r.get("metadata", {}).get("status") == "pending_review"]
    
    def add_validation_results(self, request_id: str, validation_result: Dict):
        """Add validation results to request"""
        
        json_path = os.path.join(self.requests_dir, f"{request_id}.json")
        request_obj = load_json(json_path)
        
        if not request_obj:
            return False
        
        request_obj["validation"] = validation_result
        request_obj["audit_trail"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "validation_completed",
            "actor": "system",
            "result": "passed" if validation_result.get("passed") else "failed"
        })
        
        save_json(request_obj, json_path)
        return True
    
    def add_automation_results(self, request_id: str, automation_result: Dict):
        """Add automation results to request"""
        
        json_path = os.path.join(self.requests_dir, f"{request_id}.json")
        request_obj = load_json(json_path)
        
        if not request_obj:
            return False
        
        request_obj["automation"] = automation_result
        request_obj["audit_trail"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "automation_executed",
            "actor": "system",
            "status": automation_result.get("status")
        })
        
        save_json(request_obj, json_path)
        
        # Update CSV automation status
        self._update_csv_automation(request_id, automation_result.get("status", "pending"))
        
        return True
    
    def _update_csv_automation(self, request_id: str, status: str):
        """Update automation status in CSV"""
        try:
            rows = []
            with open(self.csv_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["request_id"] == request_id:
                        row["automation_status"] = status
                    rows.append(row)
            
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "request_id", "date", "member_name", "type", "amount",
                    "description", "budget_line", "status", "treasurer",
                    "approved_at", "automation_status", "notes"
                ])
                writer.writeheader()
                writer.writerows(rows)
        except Exception as e:
            logger.error(f"Error updating automation status: {e}")
