# Data Security Notice

This directory contains sensitive information that should **NOT** be committed to version control.

## Sensitive Files (Already in .gitignore)

### 1. Event Codes (`event_codes.csv`)
- Contains club-specific event codes and descriptions
- May reveal internal organizational structure
- **Use `event_codes.example.csv` as a template**

### 2. Transaction Logs (`transactions.csv`)
- Contains financial transaction records
- Includes member names and amounts
- **Never commit this file**

### 3. Receipts (`receipts/`)
- Contains uploaded receipts and invoices
- May include personal information, bank details, addresses
- **Directory structure is tracked, but files are ignored**

### 4. Requests (`requests/`)
- Contains JSON files with complete request details
- Includes member information and financial data
- **Directory structure is tracked, but files are ignored**

## What IS Committed (Safe to Share)

### Configuration Files
- `config/form_fields.json` - Generic form field definitions
- `config/forms_schema.json` - Form structure
- `config/lbs_rules_extracted.json` - Business rules (non-sensitive)
- `config/rules.json` - Validation rules

### Example Files
- `event_codes.example.csv` - Sample event codes for testing

## Setting Up for Development

1. Copy `event_codes.example.csv` to `event_codes.csv`
2. Add your actual event codes
3. Create empty directories if needed:
   ```bash
   mkdir -p receipts requests
   touch receipts/.gitkeep requests/.gitkeep
   ```

## Security Best Practices

✅ **DO:**
- Use `.env` for API keys and credentials
- Keep sensitive data in ignored directories
- Use example/template files for documentation
- Review git status before committing

❌ **DON'T:**
- Commit `.env` files
- Commit actual transaction data
- Commit uploaded receipts or documents
- Commit files with member personal information

## Questions?

If you're unsure whether something should be committed, assume it's sensitive and exclude it!
