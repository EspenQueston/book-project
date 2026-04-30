/**
 * AI Chatbot Widget
 * Self-contained widget — injects itself when DOM is ready.
 * Config loaded from /manager/chatbot/config/
 */
(function () {
    'use strict';

    var SEND_URL = '/manager/chatbot/send/';
    var STREAM_URL = '/manager/chatbot/stream/';
    var CONFIG_URL = '/manager/chatbot/config/';
    var HISTORY_URL = '/manager/chatbot/history/';
    var CONTACT_URL = '/manager/chatbot/contact/';
    var CONTACT_REPLIES_URL = '/manager/chatbot/contact/replies/';

    var widgetConfig = null;
    var messages = [];
    var isOpen = false;
    var isTyping = false;
    var csMode = false;  // customer service mode
    var csReplyPollTimer = null;
    var csLastSeen = '';

    // ---- CSS ----
    var css = `
    #ai-chat-toggle {
        position: fixed;
        bottom: 88px;
        right: 24px;
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: #fff;
        border: none;
        cursor: grab;
        box-shadow: 0 6px 25px rgba(102,126,234,0.5);
        font-size: 1.4rem;
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9900;
        transition: all 0.3s ease;
        animation: chatPulse 2s ease-in-out infinite;
        touch-action: none;
        user-select: none;
        -webkit-user-select: none;
    }
    #ai-chat-toggle:active { cursor: grabbing; }
    #ai-chat-toggle:hover {
        transform: scale(1.1);
        box-shadow: 0 10px 35px rgba(102,126,234,0.65);
        animation: none;
    }
    #ai-chat-badge {
        position: absolute;
        top: -4px;
        right: -4px;
        width: 20px;
        height: 20px;
        background: #ef4444;
        border-radius: 50%;
        font-size: 0.65rem;
        font-weight: 700;
        color: #fff;
        display: none;
        align-items: center;
        justify-content: center;
        border: 2px solid #fff;
    }
    @keyframes chatPulse {
        0%, 100% { box-shadow: 0 6px 25px rgba(102,126,234,0.5); }
        50%       { box-shadow: 0 6px 40px rgba(102,126,234,0.8); }
    }
    #ai-chat-window {
        position: fixed;
        bottom: 160px;
        right: 24px;
        width: 380px;
        max-height: 580px;
        background: #fff;
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.18);
        z-index: 9901;
        display: none;
        flex-direction: column;
        overflow: hidden;
        animation: chatSlideIn 0.3s ease;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    #ai-chat-window.open {
        display: flex;
    }
    @keyframes chatSlideIn {
        from { opacity: 0; transform: translateY(20px) scale(0.95); }
        to   { opacity: 1; transform: translateY(0) scale(1); }
    }
    #ai-chat-header {
        background: linear-gradient(135deg, #667eea, #764ba2);
        padding: 16px 20px;
        color: #fff;
        display: flex;
        align-items: center;
        gap: 12px;
        flex-shrink: 0;
    }
    .ai-chat-avatar {
        width: 40px;
        height: 40px;
        background: rgba(255,255,255,0.2);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        flex-shrink: 0;
    }
    .ai-chat-header-info { flex: 1; min-width: 0; }
    .ai-chat-header-title { font-weight: 700; font-size: 0.95rem; }
    .ai-chat-header-sub { font-size: 0.75rem; opacity: 0.85; }
    .ai-chat-status {
        width: 8px; height: 8px;
        background: #10b981;
        border-radius: 50%;
        display: inline-block;
        margin-right: 4px;
        animation: blink 2s ease-in-out infinite;
    }
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.4} }
    #ai-chat-close {
        background: none;
        border: none;
        color: rgba(255,255,255,0.8);
        font-size: 1.1rem;
        cursor: pointer;
        padding: 4px 8px;
        border-radius: 6px;
        transition: background 0.2s;
        flex-shrink: 0;
    }
    #ai-chat-close:hover { background: rgba(255,255,255,0.15); color: #fff; }
    #ai-chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        scroll-behavior: smooth;
    }
    #ai-chat-messages::-webkit-scrollbar { width: 4px; }
    #ai-chat-messages::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 4px; }
    .chat-msg {
        max-width: 80%;
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    .chat-msg.user { align-self: flex-end; align-items: flex-end; }
    .chat-msg.assistant { align-self: flex-start; align-items: flex-start; }
    .chat-bubble {
        padding: 10px 14px;
        border-radius: 16px;
        font-size: 0.88rem;
        line-height: 1.55;
        word-break: break-word;
        white-space: pre-wrap;
    }
    .chat-msg.user .chat-bubble {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: #fff;
        border-bottom-right-radius: 4px;
    }
    .chat-msg.assistant .chat-bubble {
        background: #f1f5f9;
        color: #1e293b;
        border-bottom-left-radius: 4px;
        border: 1px solid #e2e8f0;
        white-space: normal;
    }
    .chat-msg.assistant .chat-bubble strong { color: #4338ca; }
    .chat-msg.assistant .chat-bubble em { color: #6b7280; }
    .chat-msg.assistant .chat-bubble code {
        background: #e0e7ff; color: #3730a3; padding: 1px 5px; border-radius: 4px;
        font-size: 0.82em; font-family: 'Courier New', monospace;
    }
    .chat-msg.assistant .chat-bubble pre {
        background: #1e293b; color: #e2e8f0; padding: 10px 14px; border-radius: 8px;
        font-size: 0.8em; font-family: 'Courier New', monospace; overflow-x: auto;
        margin: 8px 0; line-height: 1.5; white-space: pre-wrap; word-break: break-word;
    }
    .chat-msg.assistant .chat-bubble pre code {
        background: none; color: inherit; padding: 0; font-size: inherit;
    }
    .chat-msg.assistant .chat-bubble h3, .chat-msg.assistant .chat-bubble h4 {
        font-size: 0.95em; font-weight: 700; color: #1e293b; margin: 10px 0 4px;
        padding-bottom: 3px; border-bottom: 1px solid #e2e8f0;
    }
    .chat-msg.assistant .chat-bubble h4 { font-size: 0.9em; border-bottom: none; }
    .chat-msg.assistant .chat-bubble ul, .chat-msg.assistant .chat-bubble ol {
        margin: 6px 0; padding-left: 18px;
    }
    .chat-msg.assistant .chat-bubble li { margin-bottom: 3px; }
    .chat-msg.assistant .chat-bubble hr {
        border: none; border-top: 1px solid #e2e8f0; margin: 8px 0;
    }
    .chat-msg.assistant .chat-bubble a {
        color: #667eea; text-decoration: underline;
    }
    .chat-msg.assistant .chat-bubble blockquote {
        border-left: 3px solid #667eea; padding: 4px 10px; margin: 6px 0;
        color: #6b7280; background: rgba(102,126,234,0.05); border-radius: 0 6px 6px 0;
    }
    .chat-msg.assistant .chat-bubble table {
        border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 0.85em;
    }
    .chat-msg.assistant .chat-bubble table th,
    .chat-msg.assistant .chat-bubble table td {
        border: 1px solid #e2e8f0; padding: 4px 8px; text-align: left;
    }
    .chat-msg.assistant .chat-bubble table th {
        background: #f1f5f9; font-weight: 600;
    }
    .chat-time { font-size: 0.7rem; color: #94a3b8; margin-top: 2px; padding: 0 4px; }
    .typing-dots {
        display: inline-flex;
        gap: 4px;
        align-items: center;
        height: 20px;
    }
    .typing-dots span {
        width: 7px; height: 7px;
        background: #94a3b8;
        border-radius: 50%;
        animation: typingBounce 1.4s ease-in-out infinite;
    }
    .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
    .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes typingBounce {
        0%,80%,100% { transform: translateY(0); background: #94a3b8; }
        40%          { transform: translateY(-8px); background: #667eea; }
    }
    #ai-chat-input-area {
        padding: 12px 16px;
        border-top: 1px solid #e5e7eb;
        display: flex;
        gap: 8px;
        align-items: flex-end;
        background: #fafafa;
        flex-shrink: 0;
    }
    #ai-chat-input {
        flex: 1;
        border: 1.5px solid #e5e7eb;
        border-radius: 12px;
        padding: 9px 14px;
        font-size: 0.88rem;
        outline: none;
        resize: none;
        max-height: 100px;
        min-height: 38px;
        font-family: inherit;
        line-height: 1.4;
        transition: border-color 0.2s;
        background: #fff;
    }
    #ai-chat-input:focus { border-color: #667eea; }
    #ai-chat-send {
        width: 38px; height: 38px;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: #fff;
        border: none;
        border-radius: 50%;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.9rem;
        transition: all 0.2s;
        flex-shrink: 0;
    }
    #ai-chat-send:hover { transform: scale(1.1); box-shadow: 0 4px 12px rgba(102,126,234,0.4); }
    #ai-chat-send:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
    .chat-quick-btns {
        padding: 0 16px 10px;
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        flex-shrink: 0;
    }
    .chat-quick-btn {
        background: #f1f5f9;
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.78rem;
        cursor: pointer;
        color: #475569;
        transition: all 0.2s;
    }
    .chat-quick-btn:hover {
        background: #e0e7ff;
        border-color: #667eea;
        color: #667eea;
    }
    .chat-cs-btn {
        background: linear-gradient(135deg, #10b981, #059669);
        color: #fff;
        border: none;
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 0.8rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .chat-cs-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(16,185,129,0.4);
    }
    .chat-cs-btn.active {
        background: linear-gradient(135deg, #ef4444, #dc2626);
    }
    .chat-mode-bar {
        padding: 6px 16px;
        background: #ecfdf5;
        border-bottom: 1px solid #d1fae5;
        display: none;
        align-items: center;
        justify-content: space-between;
        font-size: 0.78rem;
        color: #059669;
        font-weight: 600;
        flex-shrink: 0;
    }
    .chat-mode-bar.show { display: flex; }
    .cs-name-input {
        border: 1.5px solid #e5e7eb;
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 0.82rem;
        outline: none;
        width: 100%;
        margin-bottom: 6px;
        font-family: inherit;
    }
    .cs-name-input:focus { border-color: #10b981; }
    @media (max-width: 480px) {
        #ai-chat-window { width: calc(100vw - 32px); right: 16px; bottom: 90px; }
        #ai-chat-toggle { right: 16px; bottom: 24px; }
    }
    `;

    // ---- Quick prompts ----
    var quickPrompts = [
        { zh: '📚 有哪些热门图书推荐？',   en: '📚 Any popular book recommendations?' },
        { zh: '🔍 如何查询我的订单？',      en: '🔍 How to track my order?' },
        { zh: '✍️ 平台有哪些知名作者？',    en: '✍️ What famous authors are available?' },
        { zh: '💰 图书价格范围是多少？',     en: '💰 What are the price ranges?' },
        { zh: '📊 平台有多少本图书？',       en: '📊 How many books on the platform?' },
    ];

    function getLang() {
        return localStorage.getItem('adminLang') || localStorage.getItem('publicLang') || 'zh';
    }

    function tr(zh, en) {
        return getLang() === 'en' ? en : zh;
    }

    function getCsrf() {
        var m = document.cookie.match('(^|;)\\s*csrftoken=([^;]*)');
        return m ? decodeURIComponent(m[2]) : '';
    }

    function now() {
        return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    }

    function injectCSS(cssText) {
        var s = document.createElement('style');
        s.textContent = cssText;
        document.head.appendChild(s);
    }

    function makeDraggable(el) {
        var isDragging = false, wasDragged = false;
        var startX, startY, origX, origY;
        var DRAG_THRESHOLD = 6;

        function onStart(e) {
            var ev = e.touches ? e.touches[0] : e;
            startX = ev.clientX;
            startY = ev.clientY;
            var rect = el.getBoundingClientRect();
            origX = rect.left;
            origY = rect.top;
            isDragging = true;
            wasDragged = false;
            el.style.transition = 'none';
            el.style.animation = 'none';
        }
        function onMove(e) {
            if (!isDragging) return;
            var ev = e.touches ? e.touches[0] : e;
            var dx = ev.clientX - startX;
            var dy = ev.clientY - startY;
            if (!wasDragged && Math.abs(dx) < DRAG_THRESHOLD && Math.abs(dy) < DRAG_THRESHOLD) return;
            wasDragged = true;
            e.preventDefault();
            var newX = Math.max(0, Math.min(window.innerWidth - el.offsetWidth, origX + dx));
            var newY = Math.max(0, Math.min(window.innerHeight - el.offsetHeight, origY + dy));
            el.style.left = newX + 'px';
            el.style.top = newY + 'px';
            el.style.right = 'auto';
            el.style.bottom = 'auto';
        }
        function onEnd() {
            isDragging = false;
            el.style.transition = 'all 0.3s ease';
            if (wasDragged) {
                var rect = el.getBoundingClientRect();
                var midX = rect.left + rect.width / 2;
                if (midX < window.innerWidth / 2) {
                    el.style.left = '16px';
                    el.style.right = 'auto';
                } else {
                    el.style.left = 'auto';
                    el.style.right = '24px';
                }
            }
        }

        el.addEventListener('mousedown', onStart);
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onEnd);
        el.addEventListener('touchstart', onStart, {passive: false});
        document.addEventListener('touchmove', onMove, {passive: false});
        document.addEventListener('touchend', onEnd);

        el._wasDragged = function() { return wasDragged; };
    }

    function buildWidget(cfg) {
        // Toggle button
        var toggle = document.createElement('button');
        toggle.id = 'ai-chat-toggle';
        toggle.title = tr('AI 助手', 'AI Assistant');
        toggle.innerHTML = '<i class="fas fa-robot"></i><span id="ai-chat-badge"></span>';
        toggle.onclick = function () {
            if (toggle._wasDragged && toggle._wasDragged()) return;
            toggleChat();
        };
        document.body.appendChild(toggle);
        makeDraggable(toggle);

        // Window
        var win = document.createElement('div');
        win.id = 'ai-chat-window';
        win.innerHTML = `
        <div id="ai-chat-header">
            <div class="ai-chat-avatar"><i class="fas fa-robot"></i></div>
            <div class="ai-chat-header-info">
                <div class="ai-chat-header-title">${escHtml(cfg.widget_title || 'AI 助手')}</div>
                <div class="ai-chat-header-sub">
                    <span class="ai-chat-status"></span>${escHtml(cfg.widget_subtitle || '在线')}
                </div>
            </div>
            <button class="chat-cs-btn" id="ai-cs-toggle" title="${tr('联系客服', 'Contact Support')}" onclick="window._aiChatCSToggle()">
                <i class="fas fa-headset"></i> ${tr('客服', 'Support')}
            </button>
            <button id="ai-chat-close" title="关闭"><i class="fas fa-times"></i></button>
        </div>
        <div class="chat-mode-bar" id="ai-cs-mode-bar">
            <span><i class="fas fa-headset me-1"></i>${tr('客服模式 — 消息将发送给人工客服', 'Support Mode — Messages go to human support')}</span>
            <button onclick="window._aiChatCSToggle()" style="background:none;border:none;color:#059669;cursor:pointer;font-weight:700;">✕</button>
        </div>
        <div id="ai-chat-messages"></div>
        <div class="chat-quick-btns" id="chatQuickBtns"></div>
        <div id="ai-cs-info" style="display:none;padding:4px 16px;">
            <input type="text" class="cs-name-input" id="ai-cs-name" placeholder="${tr('您的姓名（可选）', 'Your name (optional)')}">
            <input type="email" class="cs-name-input" id="ai-cs-email" placeholder="${tr('您的邮箱（可选）', 'Your email (optional)')}">
        </div>
        <div id="ai-chat-input-area">
            <textarea id="ai-chat-input" rows="1"
                placeholder="${tr('输入消息...', 'Type a message...')}"></textarea>
            <button id="ai-chat-send" title="${tr('发送', 'Send')}">
                <i class="fas fa-paper-plane"></i>
            </button>
        </div>`;
        document.body.appendChild(win);

        // Wire events
        document.getElementById('ai-chat-close').onclick = function () { closeChat(); };
        document.getElementById('ai-chat-send').onclick = function () { sendMessage(); };
        var inputEl = document.getElementById('ai-chat-input');
        inputEl.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
        });
        inputEl.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 100) + 'px';
        });

        // Quick prompts
        var qb = document.getElementById('chatQuickBtns');
        quickPrompts.forEach(function (p) {
            var btn = document.createElement('button');
            btn.className = 'chat-quick-btn';
            btn.textContent = getLang() === 'en' ? p.en : p.zh;
            btn.onclick = function () {
                document.getElementById('ai-chat-input').value = btn.textContent;
                sendMessage();
                qb.style.display = 'none';
            };
            qb.appendChild(btn);
        });

        // Welcome message
        addMessage('assistant', cfg.welcome_message || tr('你好！有什么可以帮助你的吗？', 'Hello! How can I help you?'));
    }

    function escHtml(s) {
        return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    function renderMarkdown(text) {
        if (!text) return '';
        var html = text;

        // Extract and protect code blocks (``` ... ```)
        var codeBlocks = [];
        html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, function(_, lang, code) {
            var idx = codeBlocks.length;
            codeBlocks.push('<pre><code>' + escHtml(code.replace(/^\n|\n$/g, '')) + '</code></pre>');
            return '\x00CB' + idx + '\x00';
        });

        // Extract and protect inline code (`code`)
        var inlineCodes = [];
        html = html.replace(/`([^`\n]+)`/g, function(_, code) {
            var idx = inlineCodes.length;
            inlineCodes.push('<code>' + escHtml(code) + '</code>');
            return '\x00IC' + idx + '\x00';
        });

        // Escape HTML in remaining text
        html = escHtml(html);

        // Restore inline code
        html = html.replace(/\x00IC(\d+)\x00/g, function(_, idx) { return inlineCodes[parseInt(idx)]; });

        // Headers: ### and ####
        html = html.replace(/^####\s+(.+)$/gm, '<h4>$1</h4>');
        html = html.replace(/^###\s+(.+)$/gm, '<h3>$1</h3>');
        html = html.replace(/^##\s+(.+)$/gm, '<h3>$1</h3>');

        // Horizontal rules
        html = html.replace(/^---+$/gm, '<hr>');

        // Blockquotes: > text
        html = html.replace(/^&gt;\s?(.+)$/gm, '<blockquote>$1</blockquote>');
        // Merge consecutive blockquotes
        html = html.replace(/<\/blockquote>\n<blockquote>/g, '<br>');

        // Bold: **text**
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

        // Italic: *text* (but not inside already-processed tags)
        html = html.replace(/\*([^*]+?)\*/g, '<em>$1</em>');

        // Tables: | col | col |
        var tableRegex = /((?:^\|.+\|$\n?)+)/gm;
        html = html.replace(tableRegex, function(tableBlock) {
            var rows = tableBlock.trim().split('\n').filter(function(r) { return r.trim(); });
            if (rows.length < 2) return tableBlock;
            // Check if second row is separator
            var isSep = /^\|[\s\-:|]+\|$/.test(rows[1]);
            var startIdx = isSep ? 2 : 1;
            var thead = '';
            if (isSep) {
                var hCells = rows[0].split('|').filter(function(c) { return c.trim(); });
                thead = '<thead><tr>' + hCells.map(function(c) { return '<th>' + c.trim() + '</th>'; }).join('') + '</tr></thead>';
            }
            var tbodyRows = rows.slice(isSep ? 0 : 0, isSep ? 1 : 0);
            var tbody = '<tbody>';
            for (var i = startIdx; i < rows.length; i++) {
                var cells = rows[i].split('|').filter(function(c) { return c.trim(); });
                tbody += '<tr>' + cells.map(function(c) { return '<td>' + c.trim() + '</td>'; }).join('') + '</tr>';
            }
            tbody += '</tbody>';
            return '<table>' + thead + tbody + '</table>';
        });

        // Unordered list items: - item or • item or * item (at start of line)
        html = html.replace(/^[\s]*[-•]\s+(.+)$/gm, '{{UL_ITEM}}$1{{/UL_ITEM}}');
        // Ordered list items: 1. item
        html = html.replace(/^[\s]*\d+\.\s+(.+)$/gm, '{{OL_ITEM}}$1{{/OL_ITEM}}');

        // Wrap consecutive list items
        html = html.replace(/((?:{{UL_ITEM}}.*?{{\/UL_ITEM}}\n?)+)/g, function(block) {
            return '<ul>' + block.replace(/{{UL_ITEM}}(.*?){{\/UL_ITEM}}/g, '<li>$1</li>') + '</ul>';
        });
        html = html.replace(/((?:{{OL_ITEM}}.*?{{\/OL_ITEM}}\n?)+)/g, function(block) {
            return '<ol>' + block.replace(/{{OL_ITEM}}(.*?){{\/OL_ITEM}}/g, '<li>$1</li>') + '</ol>';
        });

        // Line breaks (but not around block elements)
        html = html.replace(/\n/g, '<br>');

        // Clean up <br> around block elements
        html = html.replace(/<br>\s*(<(?:ul|ol|li|h[34]|pre|hr|table|blockquote|\/ul|\/ol|\/blockquote))/g, '$1');
        html = html.replace(/(<\/(?:ul|ol|h[34]|pre|hr|table|blockquote)>)\s*<br>/g, '$1');
        html = html.replace(/<br><li>/g, '<li>');
        html = html.replace(/<\/li><br>/g, '</li>');

        // Restore code blocks
        html = html.replace(/\x00CB(\d+)\x00/g, function(_, idx) { return codeBlocks[parseInt(idx)]; });

        return html;
    }

    function addMessage(role, content, animated) {
        var container = document.getElementById('ai-chat-messages');
        if (!container) return;

        var div = document.createElement('div');
        div.className = 'chat-msg ' + role;
        var bubble = document.createElement('div');
        bubble.className = 'chat-bubble';
        if (role === 'assistant') {
            bubble.innerHTML = renderMarkdown(content);
        } else {
            bubble.textContent = content;
        }
        var time = document.createElement('div');
        time.className = 'chat-time';
        time.textContent = now();
        div.appendChild(bubble);
        div.appendChild(time);
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        messages.push({ role: role, content: content });
        return div;
    }

    function showTyping() {
        var container = document.getElementById('ai-chat-messages');
        if (!container) return null;
        var div = document.createElement('div');
        div.className = 'chat-msg assistant';
        div.id = 'typing-indicator';
        div.innerHTML = '<div class="chat-bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>';
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        return div;
    }

    function removeTyping() {
        var el = document.getElementById('typing-indicator');
        if (el) el.remove();
    }

    function sendMessage() {
        if (isTyping) return;
        var input = document.getElementById('ai-chat-input');
        if (!input) return;
        var text = input.value.trim();
        if (!text) return;

        input.value = '';
        input.style.height = 'auto';
        document.getElementById('chatQuickBtns').style.display = 'none';

        addMessage('user', text);

        // Customer Service mode: send to contact endpoint
        if (csMode) {
            isTyping = true;
            document.getElementById('ai-chat-send').disabled = true;
            var fd = new FormData();
            fd.append('message', text);
            fd.append('name', (document.getElementById('ai-cs-name') || {}).value || '');
            fd.append('email', (document.getElementById('ai-cs-email') || {}).value || '');
            fd.append('csrfmiddlewaretoken', getCsrf());
            fetch(CONTACT_URL, { method: 'POST', body: fd })
                .then(function(r) { return r.json(); })
                .then(function(d) {
                    isTyping = false;
                    document.getElementById('ai-chat-send').disabled = false;
                    if (d.success) {
                        addMessage('assistant', tr('✅ 消息已发送给客服，请稍候回复。', '✅ Message sent to support. Please wait for a reply.'));
                    } else {
                        addMessage('assistant', '⚠️ ' + (d.message || tr('发送失败', 'Send failed')));
                    }
                })
                .catch(function() {
                    isTyping = false;
                    document.getElementById('ai-chat-send').disabled = false;
                    addMessage('assistant', '⚠️ ' + tr('网络错误，请稍后重试', 'Network error, please try again'));
                });
            return;
        }

        // AI mode: stream response
        isTyping = true;
        document.getElementById('ai-chat-send').disabled = true;

        showTyping();

        var fd = new FormData();
        fd.append('message', text);
        fd.append('csrfmiddlewaretoken', getCsrf());

        // Use streaming endpoint for real-time token display
        fetch(STREAM_URL, { method: 'POST', body: fd })
            .then(function (response) {
                // Check if we got a JSON error (non-streaming fallback)
                var ct = response.headers.get('content-type') || '';
                if (ct.indexOf('application/json') !== -1) {
                    return response.json().then(function (d) {
                        removeTyping();
                        isTyping = false;
                        document.getElementById('ai-chat-send').disabled = false;
                        if (d.success) {
                            addMessage('assistant', d.reply);
                        } else {
                            addMessage('assistant', '⚠️ ' + (d.message || tr('抱歉，发生了错误', 'Sorry, an error occurred')));
                        }
                    });
                }

                // SSE streaming
                removeTyping();
                var container = document.getElementById('ai-chat-messages');
                var div = document.createElement('div');
                div.className = 'chat-msg assistant';
                var bubble = document.createElement('div');
                bubble.className = 'chat-bubble';
                bubble.innerHTML = '';
                var timeEl = document.createElement('div');
                timeEl.className = 'chat-time';
                timeEl.textContent = now();
                div.appendChild(bubble);
                div.appendChild(timeEl);
                container.appendChild(div);

                var fullText = '';
                var reader = response.body.getReader();
                var decoder = new TextDecoder();
                var sseBuffer = '';

                function processStream() {
                    return reader.read().then(function (result) {
                        if (result.done) {
                            isTyping = false;
                            document.getElementById('ai-chat-send').disabled = false;
                            // Final markdown render
                            bubble.innerHTML = renderMarkdown(fullText);
                            container.scrollTop = container.scrollHeight;
                            messages.push({ role: 'assistant', content: fullText });
                            return;
                        }
                        sseBuffer += decoder.decode(result.value, { stream: true });
                        var lines = sseBuffer.split('\n');
                        sseBuffer = lines.pop(); // keep incomplete line

                        for (var i = 0; i < lines.length; i++) {
                            var line = lines[i].trim();
                            if (!line || !line.startsWith('data: ')) continue;
                            try {
                                var obj = JSON.parse(line.substring(6));
                                if (obj.token) {
                                    fullText += obj.token;
                                    // Live update with plain text (fast), re-render markdown at end
                                    bubble.textContent = fullText;
                                    container.scrollTop = container.scrollHeight;
                                } else if (obj.error) {
                                    bubble.innerHTML = '<span style="color:#ef4444">⚠️ ' + obj.error + '</span>';
                                    container.scrollTop = container.scrollHeight;
                                } else if (obj.done) {
                                    // Final render with markdown
                                    bubble.innerHTML = renderMarkdown(fullText);
                                    container.scrollTop = container.scrollHeight;
                                }
                            } catch (e) { /* skip malformed */ }
                        }
                        return processStream();
                    });
                }
                return processStream();
            })
            .catch(function () {
                removeTyping();
                isTyping = false;
                document.getElementById('ai-chat-send').disabled = false;
                addMessage('assistant', '⚠️ ' + tr('网络错误，请稍后重试', 'Network error, please try again'));
            });
    }

    function toggleChat() {
        if (isOpen) closeChat();
        else openChat();
    }

    function openChat() {
        isOpen = true;
        var win = document.getElementById('ai-chat-window');
        if (win) { win.classList.add('open'); }
        var badge = document.getElementById('ai-chat-badge');
        if (badge) badge.style.display = 'none';
        var toggle = document.getElementById('ai-chat-toggle');
        if (toggle) toggle.innerHTML = '<i class="fas fa-times"></i>';
        var input = document.getElementById('ai-chat-input');
        if (input) setTimeout(function () { input.focus(); }, 200);
    }

    function closeChat() {
        isOpen = false;
        var win = document.getElementById('ai-chat-window');
        if (win) { win.classList.remove('open'); }
        var toggle = document.getElementById('ai-chat-toggle');
        if (toggle) toggle.innerHTML = '<i class="fas fa-robot"></i><span id="ai-chat-badge"></span>';
    }

    function init() {
        fetch(CONFIG_URL)
            .then(function (r) { return r.json(); })
            .then(function (cfg) {
                if (!cfg.active) return;

                var isAdmin = document.body.classList.contains('admin-page') ||
                               !!document.querySelector('.sidebar, .main-content');
                var isPublic = !isAdmin;

                if (isPublic && !cfg.show_on_public) return;
                if (isAdmin && !cfg.show_on_admin) return;

                injectCSS(css);
                widgetConfig = cfg;
                buildWidget(cfg);
            })
            .catch(function () {
                // Chatbot not available — fail silently
            });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Customer Service mode toggle
    window._aiChatCSToggle = function() {
        csMode = !csMode;
        var btn = document.getElementById('ai-cs-toggle');
        var bar = document.getElementById('ai-cs-mode-bar');
        var info = document.getElementById('ai-cs-info');
        var inputEl = document.getElementById('ai-chat-input');
        if (csMode) {
            btn.classList.add('active');
            btn.innerHTML = '<i class="fas fa-robot"></i> ' + tr('AI', 'AI');
            bar.classList.add('show');
            if (info) info.style.display = 'block';
            if (inputEl) inputEl.placeholder = tr('输入消息给客服...', 'Message to support...');
            addMessage('assistant', tr(
                '🎧 您已切换到人工客服模式。请输入您的问题，客服人员会尽快回复。',
                '🎧 You are now in human support mode. Type your question and our team will reply soon.'
            ));
            // Start polling for replies
            startCSPoll();
        } else {
            btn.classList.remove('active');
            btn.innerHTML = '<i class="fas fa-headset"></i> ' + tr('客服', 'Support');
            bar.classList.remove('show');
            if (info) info.style.display = 'none';
            if (inputEl) inputEl.placeholder = tr('输入消息...', 'Type a message...');
            addMessage('assistant', tr(
                '🤖 已切换回 AI 助手模式。',
                '🤖 Switched back to AI assistant mode.'
            ));
            stopCSPoll();
        }
    };

    function startCSPoll() {
        stopCSPoll();
        csReplyPollTimer = setInterval(function() {
            var url = CONTACT_REPLIES_URL;
            if (csLastSeen) url += '?after=' + encodeURIComponent(csLastSeen);
            fetch(url)
                .then(function(r) { return r.json(); })
                .then(function(d) {
                    if (d.success && d.replies && d.replies.length > 0) {
                        d.replies.forEach(function(r) {
                            addMessage('assistant', '👤 ' + tr('客服回复', 'Support reply') + ':\n' + r.reply);
                            if (r.replied_at) csLastSeen = r.replied_at;
                        });
                    }
                })
                .catch(function() {});
        }, 5000); // Poll every 5 seconds
    }

    function stopCSPoll() {
        if (csReplyPollTimer) {
            clearInterval(csReplyPollTimer);
            csReplyPollTimer = null;
        }
    }

    // Public API
    window.aiChatbot = { open: openChat, close: closeChat, toggle: toggleChat };
})();
