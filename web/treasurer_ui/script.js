/**
 * Treasurer Dashboard - JavaScript
 * Loads data from local files and manages request approvals
 */

// Global state
let allRequests = [];
let currentRequestId = null;

/**
 * Get amount from request based on form type
 */
function getAmount(request) {
    const type = request.request.type;
    if (type === 'supplier_payment') {
        return request.request.invoice_amount || 0;
    } else if (type === 'expense_reimbursement') {
        return request.request.total_claim_amount || 0;
    } else if (type === 'internal_transfer') {
        return request.request.transfer_amount || 0;
    }
    return request.request.amount || 0;
}

/**
 * Get date from request based on form type
 */
function getDate(request) {
    return request.request.expense_date || request.request.date || 'N/A';
}

/**
 * Get vendor/merchant name from request based on form type
 */
function getVendor(request) {
    const type = request.request.type;
    if (type === 'supplier_payment') {
        return request.request.vendor_name || 'N/A';
    } else if (type === 'expense_reimbursement') {
        return request.request.merchant_name || 'N/A';
    } else if (type === 'internal_transfer') {
        return request.request.recipient_club_name || 'N/A';
    }
    return request.request.vendor || 'N/A';
}

/**
 * Get description from request based on form type
 */
function getDescription(request) {
    const type = request.request.type;
    if (type === 'supplier_payment') {
        return request.request.purpose_of_payment || 'N/A';
    } else if (type === 'expense_reimbursement') {
        return request.request.expense_description || 'N/A';
    } else if (type === 'internal_transfer') {
        return request.request.purpose_of_transfer || 'N/A';
    }
    return request.request.description || 'N/A';
}

/**
 * Get budget/event code from request
 */
function getBudgetLine(request) {
    return request.request.event_code || request.request.budget_line || 'N/A';
}

/**
 * Get receipt/invoice upload from request
 */
function getReceipt(request) {
    const type = request.request.type;
    if (type === 'supplier_payment') {
        return request.request.invoice_upload || null;
    } else if (type === 'expense_reimbursement') {
        return request.request.receipt_upload || null;
    } else if (type === 'internal_transfer') {
        return request.request.file_upload || null;
    }
    return request.request.receipt || null;
}

/**
 * Load all data and populate dashboard
 */
async function loadDashboard() {
    console.log("Loading dashboard...");
    
    try {
        // Fetch data from API
        const response = await fetch('/api/requests');
        const data = await response.json();
        
        allRequests = data;
        
        // Update statistics
        updateStats();
        
        // Populate pending requests
        populatePendingRequests();
        
        // Update activity table
        updateActivityTable();
        
        console.log(`Loaded ${allRequests.length} requests`);
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showError('Failed to load dashboard. Make sure the backend is running.');
    }
}

/**
 * Update dashboard statistics
 */
function updateStats() {
    const pending = allRequests.filter(r => r.metadata.status === 'pending_review').length;
    const today = allRequests.filter(r => {
        const today = new Date().toDateString();
        const reqDate = new Date(r.metadata.created_at).toDateString();
        return reqDate === today;
    }).length;
    
    document.getElementById('pending-count').textContent = pending;
    document.getElementById('today-count').textContent = today;
    document.getElementById('total-count').textContent = allRequests.length;
}

/**
 * Populate pending requests
 */
function populatePendingRequests() {
    const pendingList = document.getElementById('pending-list');
    const pending = allRequests.filter(r => r.metadata.status === 'pending_review');
    
    if (pending.length === 0) {
        pendingList.innerHTML = '<p class="loading">No pending requests</p>';
        return;
    }
    
    pendingList.innerHTML = pending.map(request => {
        const amount = getAmount(request);
        const member = request.member.name || 'Unknown';
        const type = request.request.type || 'Unknown';
        const id = request.metadata.request_id;
        
        return `
            <div class="request-card" onclick="showRequestDetail('${id}')">
                <div class="request-card-info">
                    <h3>
                        ${id}
                        <span class="request-card-status">⏳ Pending</span>
                    </h3>
                    <p>Member: <strong>${member}</strong></p>
                    <p>Type: <strong>${type}</strong></p>
                    <p>Budget: <strong>${request.request.budget_line || 'N/A'}</strong></p>
                </div>
                <div class="request-card-amount">£${amount.toFixed(2)}</div>
            </div>
        `;
    }).join('');
}

/**
 * Show request details in modal
 */
function showRequestDetail(requestId) {
    currentRequestId = requestId;
    
    const request = allRequests.find(r => r.metadata.request_id === requestId);
    if (!request) {
        showError('Request not found');
        return;
    }
    
    const modal = document.getElementById('detail-modal');
    const modalBody = document.getElementById('modal-body');
    
    const validationStatus = request.validation.passed ? '✅ Passed' : '❌ Failed';
    const violations = request.validation.violations || [];
    const violationHtml = violations.length > 0 
        ? `<strong>Issues:</strong><ul>${violations.map(v => `<li>${v.message}</li>`).join('')}</ul>`
        : '';
    
    const receiptFile = getReceipt(request);
    const receiptLink = receiptFile
        ? `<a href="/receipts/${receiptFile}" target="_blank">📎 ${receiptFile}</a>`
        : 'No receipt';
    
    modalBody.innerHTML = `
        <h2>${requestId}</h2>
        
        <h3>📋 Request Details</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Member:</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">${request.member.name}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Type:</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">${request.request.type}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Amount:</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>£${getAmount(request).toFixed(2)}</strong></td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Date:</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">${getDate(request)}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Vendor/Merchant:</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">${getVendor(request)}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Description:</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">${getDescription(request)}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Event Code:</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">${getBudgetLine(request)}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Receipt/Invoice:</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">${receiptLink}</td>
            </tr>
        </table>
        
        <h3 style="margin-top: 20px;">✅ Validation Results</h3>
        <p><strong>Status:</strong> ${validationStatus}</p>
        <p><strong>Score:</strong> ${((request.validation.score || 0) * 100).toFixed(0)}%</p>
        ${violationHtml}
    `;
    
    modal.style.display = 'block';
}

/**
 * Close modal
 */
function closeModal() {
    document.getElementById('detail-modal').style.display = 'none';
}

/**
 * Approve request
 */
function approveRequest() {
    if (!currentRequestId) return;
    
    fetch(`/api/request/${currentRequestId}/approve`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            treasurer: 'Treasurer Name',
            notes: 'Approved'
        })
    })
    .then(r => r.json())
    .then(data => {
        alert('✅ Request approved!');
        closeModal();
        loadDashboard();
    })
    .catch(e => showError(`Error approving request: ${e}`));
}

/**
 * Hold request
 */
function holdRequest() {
    if (!currentRequestId) return;
    
    const reason = prompt('Enter reason for holding:');
    if (!reason) return;
    
    fetch(`/api/request/${currentRequestId}/hold`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            treasurer: 'Treasurer Name',
            notes: reason
        })
    })
    .then(r => r.json())
    .then(data => {
        alert('⏸️ Request put on hold');
        closeModal();
        loadDashboard();
    })
    .catch(e => showError(`Error holding request: ${e}`));
}

/**
 * Reject request
 */
function rejectRequest() {
    if (!currentRequestId) return;
    
    const reason = prompt('Enter reason for rejection:');
    if (!reason) return;
    
    fetch(`/api/request/${currentRequestId}/reject`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            treasurer: 'Treasurer Name',
            notes: reason
        })
    })
    .then(r => r.json())
    .then(data => {
        alert('❌ Request rejected');
        closeModal();
        loadDashboard();
    })
    .catch(e => showError(`Error rejecting request: ${e}`));
}

/**
 * Update budget overview
 */
function updateBudgetOverview() {
    // Removed - budget section no longer displayed
}

/**
 * Update activity table
 */
function updateActivityTable() {
    const tbody = document.getElementById('activity-tbody');
    
    if (allRequests.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="loading">No transactions yet</td></tr>';
        return;
    }
    
    tbody.innerHTML = allRequests.slice(0, 10).map(request => {
        const status = request.metadata.status;
        let statusClass = 'status-pending';
        if (status === 'approved') statusClass = 'status-approved';
        else if (status === 'rejected') statusClass = 'status-rejected';
        
        return `
            <tr>
                <td>${request.metadata.request_id}</td>
                <td>${request.request.date || 'N/A'}</td>
                <td>${request.member.name}</td>
                <td>${request.request.type}</td>
                <td>£${getAmount(request).toFixed(2)}</td>
                <td><span class="status-badge ${statusClass}">${status}</span></td>
            </tr>
        `;
    }).join('');
}

/**
 * Export to CSV
 */
function exportCSV() {
    // Removed - export section no longer displayed
}

/**
 * Export to JSON
 */
function exportJSON() {
    // Removed - export section no longer displayed
}

/**
 * Download file utility
 */
function downloadFile(content, filename, type) {
    const element = document.createElement('a');
    element.setAttribute('href', `data:${type};charset=utf-8,` + encodeURIComponent(content));
    element.setAttribute('download', filename);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}

/**
 * Show error message
 */
function showError(message) {
    alert(`❌ Error: ${message}`);
}

/**
 * Close modal when clicking outside
 */
window.onclick = function(event) {
    const modal = document.getElementById('detail-modal');
    if (event.target == modal) {
        modal.style.display = 'none';
    }
};

// Load dashboard on page load
document.addEventListener('DOMContentLoaded', loadDashboard);

// Refresh every 30 seconds
setInterval(loadDashboard, 30000);
