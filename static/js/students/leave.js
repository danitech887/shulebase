
// Function to get CSRF token (needed for Django AJAX)
function getCookie(name) {
let cookieValue = null;
if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
    const cookie = cookies[i].trim();
    if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
    }
    }
}
return cookieValue;
}
const csrftoken = getCookie('csrftoken');


// AJAX Handler Function (MODIFIED to include term_select)
async function sendApprovalRequest(leaveId, action, url) {
// Get the value from the term selection dropdown inside the modal
const termSelectElement = document.getElementById('term_select');
const selectedTerm = termSelectElement ? termSelectElement.value : '';

const response = await fetch(url, {
    method: 'POST',
    headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrftoken
    },
    body: JSON.stringify({
    'leave_id': leaveId,
    'action': action,
    'term_select': selectedTerm // <-- PASSING THE SELECTED TERM
    })
});

if (!response.ok) {
    const errorText = await response.text();
    // Throw error so it lands in the catch block
    throw new Error(`Server responded with status ${response.status}: ${errorText}`);
}

return response.json();
}

document.addEventListener("DOMContentLoaded", function () {
// 🎯 Leave Approval Action Logic
const approvalModal = document.getElementById('leaveApprovalModal');

if (approvalModal) {
    approvalModal.addEventListener('click', async function (event) {
    let button = event.target.closest('.action-btn');

    if (button) {
        const action = button.getAttribute('data-action');
        const leaveId = button.getAttribute('data-id');
        const url = button.getAttribute('data-url');

        const actionCell = button.closest('.action-buttons-cell');
        const statusCell = actionCell.nextElementSibling;

        if (actionCell && statusCell && url) {

        // 1. Set Status to "Processing" and hide actions immediately
        actionCell.style.display = 'none';
        statusCell.innerHTML = `<span class="badge bg-primary"><i class="bi bi-arrow-clockwise spin me-1"></i>Processing...</span>`;

        try {
            // 2. Send AJAX Request
            const result = await sendApprovalRequest(leaveId, action, url);

            // 3. Update status based on successful response
            if (result.success) {
            const newStatusText = (action === 'Approve' ? 'Approved' : 'Rejected');
            const newStatusClass = (action === 'Approve' ? 'bg-success' : 'bg-danger');
            statusCell.innerHTML = `<span class="badge ${newStatusClass}">${newStatusText}</span>`;
            } else {
            // Handle non-success JSON response from server (e.g., status=400, message: "Invalid term")
            statusCell.innerHTML = `<span class="badge bg-warning text-dark">Failed: ${result.message || 'Error'}</span>`;
            // Re-show action buttons on failure
            actionCell.style.display = 'table-cell';
            }

        } catch (error) {
            console.error("AJAX Error:", error);
            // 4. Handle Network/Server Error
            let displayError = (error.message.includes("403")) ? "CSRF Error" : "Network Error";
            statusCell.innerHTML = `<span class="badge bg-danger">${displayError}</span>`;
            actionCell.style.display = 'table-cell'; // Re-show buttons on error
        }
        }
    }
    });
}

// Custom functions to control your custom overlay dialogs
function showDialog() { document.getElementById("overlay").classList.add("show"); }
function closeDialog() { document.getElementById("overlay").classList.remove("show"); }
function showOptionDialog() { document.getElementById("selectOptions").classList.add("show"); }
function closeOptionDialog() { document.getElementById("selectOptions").classList.remove("show"); }

document.getElementById("modal_grade").addEventListener("change", function () {
    let grade = this.value;
    let streamSelect = document.getElementById("modal_stream");

    // Clear old options
    streamSelect.innerHTML = '<option value="">-- Select Stream --</option>';

    if (grade) {
    // Assuming 'get-streams' is the correct URL for fetching streams
    fetch(`/get-streams/?grade=${grade}`)
        .then(response => response.json())
        .then(data => {
        data.streams.forEach(function (stream) {
            let option = document.createElement("option");
            option.value = stream;
            option.textContent = stream;
            streamSelect.appendChild(option);
        });
        })
        .catch(error => console.error("Error fetching streams:", error));
    }
});

var termSelectForm = document.getElementById('termSelectForm');
var gradeGroupInput = document.getElementById('grade_group');
document.querySelectorAll('[data-bs-target="#selectTermModal"]').forEach(function (btn) {
    btn.addEventListener('click', function () {
    var group = btn.getAttribute('data-grade-group');
    gradeGroupInput.value = group;
    termSelectForm.action = "{% url 'leave_reciepts' %}";
    });
});

// Enhanced loading state management
function setLoadingState(element, isLoading) {
    if (isLoading) {
    element.classList.add('loading-state');
    } else {
    element.classList.remove('loading-state');
    }
}

// Enhanced grade-stream population with better UX
function normalizeGrade(g) { return (g || "").trim(); }

function fillStreamSelect(el, streams, selected) {
    el.innerHTML = '<option value="">All Streams</option>';
    streams.forEach(s => {
    let opt = document.createElement("option");
    opt.value = s;
    opt.text = s;
    if (s === selected) opt.selected = true;
    el.appendChild(opt);
    });
}

function fillGradeSelect(el, grades, selected) {
    el.innerHTML = '<option value="">All Grades</option>';
    grades.forEach(g => {
    let opt = document.createElement("option");
    opt.value = g;
    opt.text = g;
    if (g === selected) opt.selected = true;
    el.appendChild(opt);
    });
}


let gradeSel = document.getElementById("grade");
let streamSel = document.getElementById("stream");
let initGrade = normalizeGrade("{{ request.GET.grade|default_if_none:'' }}");
let initStream = "{{ request.GET.stream|default_if_none:'' }}";

// Set loading state
setLoadingState(gradeSel, true);

// Assuming get_streams provides all grades and streams data
fetch("{% url 'get_streams' %}")
    .then(res => res.json())
    .then(data => {
    let grades = data.grades || Object.keys(data.streams_by_grade || {});
    fillGradeSelect(gradeSel, grades, initGrade);
    setLoadingState(gradeSel, false);

    if (initGrade && data.streams_by_grade && data.streams_by_grade[initGrade]) {
        fillStreamSelect(streamSel, data.streams_by_grade[initGrade], initStream);
    }

    gradeSel.addEventListener("change", function () {
        let g = normalizeGrade(this.value);
        setLoadingState(streamSel, true);

        setTimeout(() => {
        if (data.streams_by_grade && data.streams_by_grade[g]) {
            fillStreamSelect(streamSel, data.streams_by_grade[g], null);
        } else {
            streamSel.innerHTML = '<option value="">All Streams</option>';
        }
        setLoadingState(streamSel, false);
        }, 200);
    });
    })
    .catch(err => {
    console.error("Error loading grades/streams:", err);
    setLoadingState(gradeSel, false);
    gradeSel.innerHTML = '<option value="">Error loading grades</option>';
    });


// Add fade-in animations with staggered timing
const animatedElements = document.querySelectorAll('.action-section, .search-filter-section, .table-section');
animatedElements.forEach((element, index) => {
    element.style.animationDelay = `${index * 0.15}s`;
    element.classList.add('fade-in');
});

// Enhanced form validation
const reasonField = document.getElementById("id_reason");
const otherWrapper = document.getElementById("otherReasonWrapper");

function toggleOtherReason() {
    if (reasonField && otherWrapper) {
    if (reasonField.value === "Other Reason") {
        otherWrapper.style.display = "block";
    } else {
        otherWrapper.style.display = "none";
    }
    }
}

if (reasonField) {
    reasonField.addEventListener("change", toggleOtherReason);
    toggleOtherReason(); // run on load
}

// Auto-focus search input if empty
const searchInput = document.getElementById('search');
if (searchInput && !searchInput.value) {
    setTimeout(() => searchInput.focus(), 800);
}

// Keyboard shortcuts
document.addEventListener('keydown', function (e) {
    // ESC key closes overlay
    if (e.key === 'Escape') {
    const overlay = document.getElementById('overlay');
    const selectOptions = document.getElementById('selectOptions');
    // Close custom overlays
    if (overlay && overlay.classList.contains('show')) {
        closeDialog();
    }
    if (selectOptions && selectOptions.classList.contains('show')) {
        closeOptionDialog();
    }
    }

    // Ctrl+N opens new leave approval (custom overlay)
    if (e.ctrlKey && e.key === 'n') {
    e.preventDefault();
    showDialog();
    }

    // Ctrl+F focuses search
    if (e.ctrlKey && e.key === 'f') {
    e.preventDefault();
    searchInput?.focus();
    }
});
});
