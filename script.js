const API_URL = 'https://script.google.com/macros/s/AKfycbwG462ao0VUGfTOuxNcnYm-BDuNorNLtjFS-b5FY6jo4vzkdFvNv_2CRipYBoYp5_hhvw/exec'; 
const JARVIS_URL = 'http://localhost:5000/chat';

let currentUser = null;
let currentPass = null;

$(document).ready(function() {
    toggleLogoutButton(false);

    // 1. AUTO-LOGIN
    const savedUser = localStorage.getItem('fridgeUser');
    const savedPass = localStorage.getItem('fridgePass');
    const lastView = localStorage.getItem('lastView');
    
    if (savedUser && savedPass) {
        currentUser = savedUser;
        currentPass = savedPass;
        toggleLogoutButton(true);
        
        // FIX 1: Only hide AUTH cards, NOT the About Us card
        $('.auth-card').hide(); 

        // Only switch views if we are on the main dashboard (index.html)
        // We check if the 'inventory-section' exists to know we are on the main page
        if ($('#inventory-section').length > 0) {
            if (lastView === 'jarvis-view') {
                showView('jarvis-view');
            } else {
                showView('inventory-section');
            }
            loadTable();
            loadChatHistory();
        }
    }

    // 3. EVENT BINDINGS
    $('#mobile-search-input').on('keyup', function() {
        if ($.fn.DataTable.isDataTable('#inventory')) $('#inventory').DataTable().search(this.value).draw();
    });

    $('#mobile-sort-select').on('change', function() {
        if ($.fn.DataTable.isDataTable('#inventory')) {
            let val = $(this).val();
            let [col, dir] = val.split('_');
            $('#inventory').DataTable().order([parseInt(col), dir]).draw();
        }
    });

    $('#chat-input').on('keypress', function (e) {
        if(e.which === 13) {
            e.preventDefault(); 
            sendJarvisMessage();
        }
    });
});

// --- CHAT HISTORY PERSISTENCE ---
function saveChatHistory() {
    const history = $('#chat-history').html();
    localStorage.setItem('jarvisChatHistory', history);
}

function loadChatHistory() {
    const history = localStorage.getItem('jarvisChatHistory');
    if (history && $('#chat-history').length > 0) {
        $('#chat-history').html(history);
        $('#chat-history').scrollTop($('#chat-history')[0].scrollHeight);
    }
}

function clearChatHistory() {
    if(confirm("Clear chat history?")) {
        $('#chat-history').html(`
            <div class="chat-msg bot-msg">
                <img src="jarvis-icon.jpg" class="chat-avatar">
                <div class="msg-content">History cleared. How can I help?</div>
            </div>
        `);
        localStorage.removeItem('jarvisChatHistory');
    }
}

// --- JARVIS LOGIC ---
function addChatMsg(text, isUser) {
    let cls = isUser ? 'user-msg' : 'bot-msg';
    let html = `
        <div class="chat-msg ${cls}">
            ${!isUser ? '<img src="jarvis-icon.jpg" class="chat-avatar">' : ''}
            <div class="msg-content">${text}</div>
        </div>
    `;
    $('#chat-history').append(html);
    $('#chat-history').scrollTop($('#chat-history')[0].scrollHeight);
    saveChatHistory();
}

function speakText(text) {
    if ('speechSynthesis' in window) {
        let utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1;
        window.speechSynthesis.speak(utterance);
    }
}

function startDictation() {
    if (window.hasOwnProperty('webkitSpeechRecognition')) {
        let recognition = new webkitSpeechRecognition();
        $('.mic-btn').addClass('active');
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = "en-US";
        recognition.start();

        recognition.onresult = function(e) {
            $('.mic-btn').removeClass('active');
            let text = e.results[0][0].transcript;
            $('#chat-input').val(text);
            sendJarvisMessage();
        };
        recognition.onerror = function(e) { $('.mic-btn').removeClass('active'); };
        recognition.onend = function() { $('.mic-btn').removeClass('active'); };
    } else {
        alert("Voice input not supported. Try Chrome.");
    }
}

function sendJarvisMessage() {
    let text = $('#chat-input').val().trim();
    if(!text) return;

    addChatMsg(text, true);
    $('#chat-input').val('');

    fetch(JARVIS_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
    })
    .then(response => response.json())
    .then(data => {
        let reply = data.response || "I couldn't process that.";
        addChatMsg(reply, false);
        speakText(reply);
        
        if($.fn.DataTable.isDataTable('#inventory')) {
             $('#inventory').DataTable().ajax.reload(null, false);
        }
    })
    .catch(error => {
        console.error("Jarvis Error:", error);
        addChatMsg("Error: Connection failed. Is 'king.py' running?", false);
    });
}

// --- VIEW LOGIC ---
function showView(viewId) {
    if ((viewId === 'jarvis-view' || viewId === 'inventory-section') && !currentUser) {
        alert("Please Log In First!");
        showView('login-view');
        return;
    }

    if (currentUser) {
        localStorage.setItem('lastView', viewId);
    }

    $('#sidebar').removeClass('open');
    $('.overlay').removeClass('active');
    
    // Hide ONLY the specific dashboard views
    $('.card.auth-card, .inventory-wrapper, .jarvis-wrapper').hide();
    
    $('#' + viewId).fadeIn();
    
    $('.message').text('').removeClass('error');
    if(viewId !== 'jarvis-view') $('input').val(''); 

    if (viewId === 'inventory-section') {
        setTimeout(function() {
            if ($.fn.DataTable.isDataTable('#inventory')) {
                $('#inventory').DataTable().columns.adjust().responsive?.recalc();
            }
        }, 200); 
    }
}

function toggleMenu() {
    $('#sidebar').toggleClass('open');
    $('.overlay').toggleClass('active');
}

function toggleLogoutButton(show) {
    if (show) $('#logout-section').show(); else $('#logout-section').hide();
}

function handleAuth(action) {
    let payload = { action: action };
    let msgBox, btn;

    if (action === 'login') {
        payload.username = $('#login-user').val();
        payload.password = $('#login-pass').val();
        msgBox = $('#login-msg'); btn = $('#btn-login');
    } else if (action === 'signup') {
        payload.username = $('#signup-user').val();
        payload.password = $('#signup-pass').val();
        msgBox = $('#signup-msg'); btn = $('#btn-signup');
    } else if (action === 'change_password') {
        payload.username = $('#cp-user').val();
        payload.old_password = $('#cp-old').val();
        payload.new_password = $('#cp-new').val();
        msgBox = $('#cp-msg'); btn = $('#btn-cp');
    }

    msgBox.removeClass('error').text('');
    btn.prop('disabled', true).find('.btn-text').hide().end().find('.spinner').show();

    $.ajax({
        url: API_URL,
        method: "POST",
        data: JSON.stringify(payload),
        contentType: "text/plain", 
        success: function(response) {
            btn.prop('disabled', false).find('.btn-text').show().end().find('.spinner').hide();
            
            let res;
            try {
                res = (typeof response === "object") ? response : JSON.parse(response);
            } catch (e) {
                msgBox.addClass('error').text("Invalid server response.");
                return;
            }

            if (res.status === 'success') {
                if (action === 'login' || action === 'signup') {
                    currentUser = payload.username;
                    currentPass = payload.password;
                    
                    localStorage.setItem('fridgeUser', currentUser);
                    localStorage.setItem('fridgePass', currentPass);
                    localStorage.setItem('lastView', 'inventory-section');

                    $('.auth-card').hide(); // Only hide login/signup cards
                    $('#inventory-section').fadeIn();
                    toggleLogoutButton(true);
                    loadTable();
                } else if (action === 'change_password') {
                    alert("Password updated. Please login again."); 
                    logout();
                }
            } else {
                msgBox.addClass('error').text(res.message);
            }
        },
        error: function() {
            btn.prop('disabled', false).find('.btn-text').show().end().find('.spinner').hide();
            msgBox.addClass('error').text("Connection failed. Please check internet.");
        }
    });
}

function loadTable() {
    // FIX 2: Check if table exists before trying to load it (prevents errors on About Us page)
    if ($('#inventory').length === 0) return;

    if ($.fn.DataTable.isDataTable('#inventory')) {
        $('#inventory').DataTable().ajax.reload(null, false);
        return;
    } 

    $('#inventory').DataTable({
        processing: true,
        pageLength: 10,
        lengthChange: false, 
        language: { search: "", searchPlaceholder: "Search items..." },
        
        createdRow: function (row, data, dataIndex) {
            const labels = ['Item', 'Qty', 'Unit', 'Category', 'Expiry', 'Status', 'Days Left'];
            $('td', row).each(function(i) {
                $(this).attr('data-label', labels[i]);
            });
        },
        
        ajax: function (data, callback, settings) {
            $.ajax({
                url: API_URL,
                method: 'POST',
                contentType: "text/plain", 
                data: JSON.stringify({
                    action: "get_inventory",
                    username: currentUser,
                    password: currentPass
                }),
                success: function (response) {
                    let json;
                    try { json = (typeof response === "object") ? response : JSON.parse(response); } catch(e) { json = { data: [] }; }
                    if (json.error) console.error("Table Sync Error:", json.error);
                    else callback({ data: json.data || [] });
                },
                error: function() {
                    console.error("Failed to load inventory from cloud.");
                    callback({ data: [] });
                }
            });
        },
        columns: [
            { 
                data: 'item_name', 
                defaultContent: "-",
                render: function (data) {
                    if (!data || data === "-") return "-";
                    let text = String(data); 
                    return `<strong>${text.charAt(0).toUpperCase() + text.slice(1)}</strong>`;
                }
            },
            { data: 'qty', defaultContent: "0" },
            { data: 'unit', defaultContent: "-" },
            { data: 'category', defaultContent: "-" },
            { 
                data: 'expiry', 
                defaultContent: "-",
                render: function (data) {
                    if (!data || data === "N/A" || data === "-") return "N/A";
                    return moment(data).format('YYYY-MM-DD');
                }
            },
            { 
                data: 'status', 
                defaultContent: "N/A",
                render: function(data) {
                    let color = '#333';
                    if(data === 'Expired') color = '#e74c3c';
                    else if(data === 'Good') color = '#27ae60';
                    else if(data === 'Expiring Soon') color = '#f39c12';
                    return `<span style="color:${color}; font-weight:600;">${data}</span>`;
                }
            },
            { data: 'days_left', defaultContent: "N/A" } 
        ]
    });
}

function prepareChangePass() {
    if(currentUser) $('#cp-user').val(currentUser);
    showView('change-pass-view');
}

function logout() {
    currentUser = null; currentPass = null;
    localStorage.clear(); 
    toggleLogoutButton(false);
    location.reload(); 
}