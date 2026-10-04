(() => {
    const root = document.querySelector(".social-actions");
    if (!root) return;

    const csrf = document.querySelector(".account-shell").dataset.csrf;
    const socket = io();
    const userId = root.dataset.userId;

    async function friendshipAction(action) {
        const response = await fetch(`/api/friends/${action}/${encodeURIComponent(userId)}`, {
            method: "POST", headers: {"X-CSRF-Token": csrf},
        });
        const payload = await response.json();
        if (!response.ok) throw Error(payload.error || "İşlem başarısız.");
        location.reload();
    }

    root.addEventListener("click", event => {
        const button = event.target.closest("button");
        if (!button) return;

        // The invite control intentionally has an empty data attribute in the template.
        // Check attribute presence, not its string value, so it always remains Socket.IO-only.
        if (button.hasAttribute("data-invite")) {
            socket.emit("send_game_invite", {
                target_user_id: userId,
                game_mode: "possession",
            });
            return;
        }

        friendshipAction(button.dataset.action).catch(error => alert(error.message));
    });

    socket.on("friend_presence", data => {
        if (data.user_id !== userId) return;
        const indicator = document.getElementById("presence");
        indicator.textContent = data.status === "online" ? "● Çevrim içi" : "Çevrim dışı";
        indicator.classList.toggle("online", data.status === "online");
    });
    socket.on("game_invite_accepted", data => {
        const target = `/possession?room=${encodeURIComponent(data.room_code)}`;
        if (window.MobileBridge) window.MobileBridge.navigate(target);
        else location.href = target;
    });
    socket.on("game_invite_error", data => alert(data.message));
})();
