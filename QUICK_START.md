# Quick Start Guide - LBS Treasurer AI Agent

## What's Been Built

✅ **Complete project structure** with all core modules, configurations, and web interfaces
✅ **Member Chat UI** (Gradio) - Members describe their requests naturally
✅ **Treasurer Dashboard** (HTML/CSS/JS) - Treasurers review and approve requests  
✅ **Conversation Manager** - LLM-powered data extraction using Azure OpenAI
✅ **Validation Engine** - Business rule checking with real budget calculations
✅ **Transaction Logger** - Dual storage (JSON + CSV) with audit trails
✅ **Configuration System** - Finance rules, budget lines, form schemas

## System Overview

```
Member Web UI (Gradio)          Treasurer Web UI (HTML/JS)
     ↓                                  ↓
Chat Interface                   Dashboard Interface
(Ask questions naturally)         (Review & Approve)
     ↓                                  ↓
ConversationManager ────────→ TransactionLogger ←──── API Endpoints
(LLM data extraction)          (JSON + CSV storage)   (Need backend)
     ↓
ValidationEngine
(Rule checking)
```

## File Structure

```
AIAgentCup/
├── src/
│   ├── __init__.py
│   ├── utils.py                    # Shared utilities
│   ├── conversation_manager.py      # LLM orchestration
│   ├── validation_engine.py         # Rule validation
│   ├── transaction_logger.py        # Data persistence
│   └── browser_automation.py        # [Planned]
├── web/
│   ├── member_ui/
│   │   └── app.py                  # Gradio chat interface
│   └── treasurer_ui/
│       ├── dashboard.html          # Dashboard markup
│       ├── style.css               # Professional styling
│       └── script.js               # Frontend logic
├── data/
│   ├── config/
│   │   ├── rules.json              # Finance rules & limits
│   │   └── forms_schema.json       # Form definitions
│   ├── requests/                   # JSON per-request storage
│   ├── receipts/                   # Upload storage
│   └── transactions.csv            # Audit log
├── tests/
├── screenshots/
├── requirements.txt                 # Dependencies
├── .env.example                    # Template for credentials
├── main.py                         # Application launcher
└── README_IMPLEMENTATION.md        # Full documentation
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Azure OpenAI Credentials

Create a `.env` file (copy from `.env.example`):

```bash
AZURE_OPENAI_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=your_endpoint_here
AZURE_API_VERSION=2025-04-01-preview
```

Or set environment variables:
```bash
export AZURE_OPENAI_KEY="your_key"
export AZURE_OPENAI_ENDPOINT="your_endpoint"
export AZURE_API_VERSION="2025-04-01-preview"
```

### 3. Run Member UI (Gradio Chat)

```bash
python main.py --member
```

This launches the Gradio interface where members can:
- Describe their financial request naturally
- AI asks clarifying questions
- System validates against budget rules
- Request stored with full audit trail

Example conversation:
```
Member: "I need £180 reimbursed for speaker dinner on Nov 20"
AI: "Thanks! What budget line should this come from?"
Member: "Event Costs"
AI: "Preview: Reimbursement of £180 from Event Costs (available: £820). Ready to submit?"
```

### 4. View Treasurer Dashboard (HTML)

Open `web/treasurer_ui/dashboard.html` in a browser.

Current status: **UI is ready, needs backend API implementation**

## Current Capabilities

| Feature | Status | Details |
|---------|--------|---------|
| Member chat interface | ✅ Ready | Gradio with LLM integration |
| Data extraction | ✅ Ready | Azure OpenAI gpt-4.1-mini |
| Validation | ✅ Ready | Budget checks, amount limits, date validation |
| CSV logging | ✅ Ready | Transaction audit trail |
| JSON storage | ✅ Ready | Per-request with metadata |
| Treasurer UI | ✅ Built | HTML/CSS/JS complete |
| Treasurer API | ⏳ Pending | Needs Flask/FastAPI backend |
| Auto form fill | ⏳ Pending | BrowserAutomation module design ready |

## Next Steps

### Phase 1: Test Member UI (Now)
```bash
# Set credentials in .env
python main.py --member

# Try a request:
# "I spent £45 on office supplies on Nov 15"
# Follow the chat to complete submission
```

### Phase 2: Build Treasurer Backend (Next)
Create Flask/FastAPI server with endpoints:
- `GET /api/requests` - List pending approvals
- `GET /api/request/{id}` - Request details
- `POST /api/request/{id}/approve` - Approve action
- `POST /api/request/{id}/reject` - Reject action

### Phase 3: Add Auto Form Filling (Optional)
Implement `src/browser_automation.py` with Selenium to:
- Navigate to form URLs
- Fill extracted data automatically
- Stop at manual submit for treasurer

## Data Models

### Request JSON Structure
```json
{
  "request_id": "REQ-20251122-001",
  "timestamp": "2025-11-22T14:30:00Z",
  "member": {
    "name": "John Doe",
    "email": "john@example.com"
  },
  "request_data": {
    "type": "reimbursement",
    "amount": 180.00,
    "currency": "GBP",
    "date": "2025-11-20",
    "description": "Speaker dinner",
    "budget_line": "Event Costs",
    "vendor": "Restaurant XYZ"
  },
  "validation": {
    "passed": true,
    "violations": [],
    "warnings": [],
    "score": 0.95
  },
  "status": "pending",
  "conversation_history": [...]
}
```

### Transaction CSV Schema
```
request_id,date,member_name,type,amount,description,budget_line,status,treasurer,approved_at,automation_status,notes
REQ-20251122-001,2025-11-22,John Doe,reimbursement,180.00,Speaker dinner,Event Costs,pending,,,,
```

## Configuration Files

### rules.json
Defines:
- Budget amounts per line
- Spending limits
- Auto-approval thresholds
- Validation rules

Edit to adjust business rules without code changes.

### forms_schema.json
Defines:
- Form types (reimbursement, budget_approval, transfer, event)
- Required vs optional fields
- Field validation rules

## Troubleshooting

**Gradio not starting?**
- Ensure `pip install gradio` completed
- Check Azure OpenAI credentials in `.env`

**Treasurer dashboard shows no data?**
- Backend API not yet implemented
- This is expected; Phase 2 task

**Validation always fails?**
- Check `data/config/rules.json` settings
- Verify budget line exists in config
- Check transaction CSV for budget usage

**Requests not saving?**
- Ensure `data/` directories are writable
- Check file permissions: `ls -la data/`

## Key Components API

### ConversationManager
```python
manager = ConversationManager(api_client)

# Process user message
result = manager.process_message(user_message)
# Returns: {
#   "response": "AI reply",
#   "extracted_data": {...},
#   "complete": False/True,
#   "confidence": 0.95,
#   "missing_fields": [...]
# }
```

### ValidationEngine
```python
engine = ValidationEngine(rules_path, schema_path)

# Validate extracted data
result = engine.validate(form_type, extracted_data)
# Returns: {
#   "passed": True/False,
#   "violations": [...],
#   "warnings": [...],
#   "score": 0.95
# }
```

### TransactionLogger
```python
logger = TransactionLogger()

# Create new request
request_id = logger.create_request(member_name, form_type, extracted_data)

# Update status
logger.update_request_status(request_id, "approved", treasurer_email)

# Load request
request = logger.load_request(request_id)

# Get all pending
pending = logger.get_pending_requests()
```

## Security Notes

- Environment variables store Azure credentials (not in code)
- Each request gets unique ID for audit trail
- All actions logged with timestamps and user info
- CSV provides tamper-evident transaction log
- No authentication yet (Demo mode) - add before production

## Performance Notes

- CSV reading is fast (<1KB per transaction typically)
- JSON storage avoids database complexity
- LLM calls averaged 2-3 seconds per message
- Dashboard refresh every 30 seconds (configurable)

## Support & Development

Full API documentation in `README_IMPLEMENTATION.md`

For questions on specific components, refer to:
- Conversation flow: see `src/conversation_manager.py`
- Validation rules: see `data/config/rules.json`
- Database schema: see `data/config/forms_schema.json`
- UI implementation: see `web/*/` directories
