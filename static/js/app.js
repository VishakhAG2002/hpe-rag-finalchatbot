// =============================================
// HPE RAG Chatbot — Frontend Logic
// =============================================

const state = {
    chatHistory: [],          // {role, content} for current conversation
    conversations: [],        // [{id, title, messages}]
    currentConversationId: null,
    isLoading: false,
};

// --- DOM Elements ---
const chatArea = document.getElementById("chat-area");
const welcomeScreen = document.getElementById("welcome-screen");
const messagesContainer = document.getElementById("messages-container");
const typingIndicator = document.getElementById("typing-indicator");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const newChatBtn = document.getElementById("new-chat-btn");
const chatHistoryList = document.getElementById("chat-history-list");
const statusBadge = document.getElementById("status-badge");
const statusText = document.getElementById("status-text");
const statsDisplay = document.getElementById("stats-display");
const mobileToggle = document.getElementById("mobile-toggle");
const sidebar = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebar-overlay");

// --- Configure Marked.js ---
marked.setOptions({
    breaks: true,
    gfm: true,
});

// --- API Communication ---

async function sendMessage(message) {
    if (!message.trim() || state.isLoading) return;

    state.isLoading = true;
    sendBtn.disabled = true;

    // Hide welcome, show messages
    welcomeScreen.style.display = "none";
    messagesContainer.style.display = "flex";

    // Render user message
    renderMessage("user", message);
    state.chatHistory.push({ role: "user", content: message });

    // Show typing indicator
    typingIndicator.classList.add("visible");
    scrollToBottom();

    // Clear input
    messageInput.value = "";
    autoResizeTextarea();

    try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 30000);

        const resp = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: message,
                history: state.chatHistory.slice(0, -1), // exclude current message
            }),
            signal: controller.signal,
        });

        clearTimeout(timeout);

        if (resp.status === 429) {
            renderError("Rate limit reached. Please wait a moment and try again.");
            return;
        }

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: "Server error" }));
            renderError(err.detail || "Something went wrong.");
            return;
        }

        const data = await resp.json();

        // Hide typing, render bot response
        typingIndicator.classList.remove("visible");
        renderMessage("bot", data.answer, data.sources);
        state.chatHistory.push({ role: "assistant", content: data.answer });

        // Save conversation
        saveConversation();
    } catch (err) {
        typingIndicator.classList.remove("visible");
        if (err.name === "AbortError") {
            renderError("Request timed out. Please try again.");
        } else {
            renderError("Failed to connect to the server.");
        }
    } finally {
        state.isLoading = false;
        updateSendBtn();
    }
}

// --- Rendering ---

function renderMessage(role, content, sources = []) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${role}`;

    if (role === "bot") {
        const avatar = document.createElement("div");
        avatar.className = "bot-avatar";
        avatar.textContent = "H";
        messageDiv.appendChild(avatar);
    }

    const contentWrapper = document.createElement("div");

    const contentDiv = document.createElement("div");
    contentDiv.className = "message-content";

    if (role === "bot") {
        contentDiv.innerHTML = marked.parse(content);
    } else {
        contentDiv.textContent = content;
    }

    contentWrapper.appendChild(contentDiv);

    // Add sources
    if (sources && sources.length > 0) {
        contentWrapper.appendChild(renderSources(sources));
    }

    messageDiv.appendChild(contentWrapper);
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

function renderSources(sources) {
    const section = document.createElement("div");
    section.className = "sources-section";

    const toggle = document.createElement("button");
    toggle.className = "sources-toggle";
    toggle.innerHTML = `<span class="arrow">&#9654;</span> ${sources.length} source${sources.length > 1 ? "s" : ""}`;

    const list = document.createElement("div");
    list.className = "sources-list";

    sources.forEach((s) => {
        const card = document.createElement("div");
        card.className = "source-card";

        // Truncate long filenames
        let displayName = s.source;
        if (displayName.length > 40) {
            displayName = displayName.substring(0, 37) + "...";
        }

        card.innerHTML = `
            <span class="doc-icon">&#128196;</span>
            <span>${displayName}</span>
            <span class="page-badge">p. ${s.page}</span>
        `;
        list.appendChild(card);
    });

    toggle.addEventListener("click", () => {
        toggle.classList.toggle("expanded");
        list.classList.toggle("visible");
    });

    section.appendChild(toggle);
    section.appendChild(list);
    return section;
}

function renderError(message) {
    typingIndicator.classList.remove("visible");
    const errorDiv = document.createElement("div");
    errorDiv.className = "error-message";
    errorDiv.textContent = message;
    messagesContainer.appendChild(errorDiv);
    scrollToBottom();
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        chatArea.scrollTop = chatArea.scrollHeight;
    });
}

// --- Chat History / localStorage ---

function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
}

function saveConversation() {
    if (state.chatHistory.length === 0) return;

    // Generate title from first user message
    const firstMsg = state.chatHistory.find((m) => m.role === "user");
    const title = firstMsg
        ? firstMsg.content.substring(0, 40) + (firstMsg.content.length > 40 ? "..." : "")
        : "New Chat";

    if (state.currentConversationId) {
        // Update existing
        const idx = state.conversations.findIndex(
            (c) => c.id === state.currentConversationId
        );
        if (idx >= 0) {
            state.conversations[idx].messages = [...state.chatHistory];
            state.conversations[idx].title = title;
        }
    } else {
        // Create new
        state.currentConversationId = generateId();
        state.conversations.unshift({
            id: state.currentConversationId,
            title: title,
            messages: [...state.chatHistory],
        });
    }

    // Keep max 20 conversations
    state.conversations = state.conversations.slice(0, 20);

    localStorage.setItem("hpe_rag_conversations", JSON.stringify(state.conversations));
    renderChatHistory();
}

function loadConversations() {
    try {
        const data = localStorage.getItem("hpe_rag_conversations");
        state.conversations = data ? JSON.parse(data) : [];
    } catch {
        state.conversations = [];
    }
    renderChatHistory();
}

function loadConversation(id) {
    const conv = state.conversations.find((c) => c.id === id);
    if (!conv) return;

    state.currentConversationId = id;
    state.chatHistory = [...conv.messages];

    // Clear and re-render messages
    messagesContainer.innerHTML = "";
    welcomeScreen.style.display = "none";
    messagesContainer.style.display = "flex";

    conv.messages.forEach((m) => {
        renderMessage(m.role === "assistant" ? "bot" : m.role, m.content);
    });

    renderChatHistory();
    closeSidebar();
}

function deleteConversation(id, event) {
    event.stopPropagation();
    state.conversations = state.conversations.filter((c) => c.id !== id);
    localStorage.setItem("hpe_rag_conversations", JSON.stringify(state.conversations));

    if (state.currentConversationId === id) {
        startNewChat();
    }

    renderChatHistory();
}

function renderChatHistory() {
    chatHistoryList.innerHTML = "";

    state.conversations.forEach((conv) => {
        const item = document.createElement("div");
        item.className = `history-item${conv.id === state.currentConversationId ? " active" : ""}`;
        item.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0">
                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </svg>
            <span style="overflow:hidden;text-overflow:ellipsis">${conv.title}</span>
            <button class="delete-btn" title="Delete">&times;</button>
        `;

        item.addEventListener("click", () => loadConversation(conv.id));
        item.querySelector(".delete-btn").addEventListener("click", (e) =>
            deleteConversation(conv.id, e)
        );

        chatHistoryList.appendChild(item);
    });
}

function startNewChat() {
    // Save current if it has messages
    if (state.chatHistory.length > 0 && state.currentConversationId) {
        saveConversation();
    }

    state.chatHistory = [];
    state.currentConversationId = null;

    messagesContainer.innerHTML = "";
    messagesContainer.style.display = "none";
    welcomeScreen.style.display = "flex";
    typingIndicator.classList.remove("visible");

    renderChatHistory();
    messageInput.focus();
    closeSidebar();
}

// --- Textarea ---

function autoResizeTextarea() {
    messageInput.style.height = "auto";
    const maxHeight = 120;
    messageInput.style.height = Math.min(messageInput.scrollHeight, maxHeight) + "px";
}

function updateSendBtn() {
    sendBtn.disabled = !messageInput.value.trim() || state.isLoading;
}

// --- Connection Status ---

async function checkHealth() {
    try {
        const resp = await fetch("/api/health");
        const data = await resp.json();

        statusBadge.classList.remove("disconnected");
        statusText.textContent = data.vector_store ? "Connected" : "No Documents";

        if (data.chunks > 0) {
            statsDisplay.textContent = `${data.chunks} chunks indexed`;
        }

        // Also fetch detailed stats
        const statsResp = await fetch("/api/stats");
        const stats = await statsResp.json();
        statsDisplay.textContent = `${stats.document_count} docs | ${stats.total_chunks} chunks`;
    } catch {
        statusBadge.classList.add("disconnected");
        statusText.textContent = "Disconnected";
        statsDisplay.textContent = "Server unavailable";
    }
}

// --- Mobile Sidebar ---

function openSidebar() {
    sidebar.classList.add("open");
    sidebarOverlay.classList.add("visible");
}

function closeSidebar() {
    sidebar.classList.remove("open");
    sidebarOverlay.classList.remove("visible");
}

// --- Init ---

function init() {
    // Load saved conversations
    loadConversations();

    // Event: Send on Enter
    messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            const msg = messageInput.value.trim();
            if (msg) sendMessage(msg);
        }
    });

    // Event: Textarea resize + send button state
    messageInput.addEventListener("input", () => {
        autoResizeTextarea();
        updateSendBtn();
    });

    // Event: Send button click
    sendBtn.addEventListener("click", () => {
        const msg = messageInput.value.trim();
        if (msg) sendMessage(msg);
    });

    // Event: Suggestion chips
    document.querySelectorAll(".chip").forEach((chip) => {
        chip.addEventListener("click", () => {
            const query = chip.getAttribute("data-query");
            if (query) sendMessage(query);
        });
    });

    // Event: New chat
    newChatBtn.addEventListener("click", startNewChat);

    // Event: Mobile sidebar
    mobileToggle.addEventListener("click", openSidebar);
    sidebarOverlay.addEventListener("click", closeSidebar);

    // Health check on load + interval
    checkHealth();
    setInterval(checkHealth, 30000);

    // Focus input
    messageInput.focus();
}

document.addEventListener("DOMContentLoaded", init);
