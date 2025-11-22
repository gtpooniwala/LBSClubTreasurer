# Security & Privacy Notice

## ⚠️ Important: Sensitive Data Protection

This repository is configured to **exclude sensitive data** from version control. Before committing, please review what should and should not be shared.

## 🔒 What's Protected (NOT in Git)

### API Keys & Credentials
- `.env` files (Azure OpenAI keys, endpoints)
- Any `*.env` files
- `credentials/` directory
- `secrets/` directory

### Jupyter Notebooks
- `*.ipynb` files may contain:
  - API keys embedded in code cells
  - Hardcoded Azure endpoints
  - Screenshots showing sensitive information
  - Output cells displaying API keys or tokens
- **Safe alternatives**: Template notebooks (`*_template.ipynb`, `*_example.ipynb`) with no real credentials

### Personal & Financial Data
- `data/event_codes.csv` - Contains actual club event codes
- `data/transactions.csv` - Financial transaction records
- `data/receipts/*` - Uploaded receipts and invoices
- `data/requests/*` - Request JSON files with member data
- `screenshots/*.png` - May contain sensitive UI data

### Generated & Cache Files
- `__pycache__/` - Python bytecode
- `.DS_Store` - macOS metadata
- `*.log` - Log files
- Virtual environments (`venv/`, `env/`)

## ✅ What's Safe to Commit

### Source Code
- All `.py` files in `src/`, `web/`, `tests/`
- Configuration files that don't contain secrets
- UI templates (HTML, CSS, JS)

### Documentation
- README files
- Implementation guides
- System design documents

### Configuration Templates
- `data/event_codes.example.csv` - Sample event codes
- `.env.example` - Template for environment variables
- `data/config/*.json` - Generic form definitions and business rules

### Structure Markers
- `.gitkeep` files in empty directories
- Directory structure without sensitive content

## 🛡️ Setup Instructions

### First Time Setup
```bash
# 1. Copy environment template
cp .env.example .env

# 2. Copy event codes template
cp data/event_codes.example.csv data/event_codes.csv

# 3. Edit with your actual credentials/data
nano .env
nano data/event_codes.csv
```

### Before Every Commit
```bash
# Always review what you're about to commit
git status
git diff

# Check that no sensitive files are staged
git diff --cached
```

## 📋 Checklist Before Pushing

- [ ] No `.env` files in commit
- [ ] No Jupyter notebooks (`.ipynb`) with real API keys/endpoints
- [ ] No actual event codes (only example file)
- [ ] No transaction data
- [ ] No uploaded receipts/documents
- [ ] No API keys or credentials in code
- [ ] No member personal information
- [ ] No screenshots showing sensitive UI data

## 🚨 If You Accidentally Commit Sensitive Data

If you accidentally commit sensitive information:

```bash
# If you haven't pushed yet
git reset HEAD~1
git add <files-to-keep>
git commit -m "Your message"

# If you already pushed
# Contact repository admin immediately
# May need to use git filter-branch or BFG Repo-Cleaner
```

## 📞 Questions?

When in doubt about whether to commit a file:
1. Check if it's in `.gitignore`
2. Ask: "Does this contain secrets, personal data, or financial information?"
3. If yes → **DO NOT COMMIT**
4. If unsure → **DO NOT COMMIT** and ask first

---

**Remember:** It's easier to add files later than to remove sensitive data from Git history!
