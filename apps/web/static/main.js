document.addEventListener("DOMContentLoaded", () => {
  const createRfpForm = document.getElementById("create-rfp-form");
  if (createRfpForm) {
    createRfpForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const status = document.getElementById("create-rfp-status");
      status.textContent = "Creating...";
      status.className = "form-status";

      const formData = new FormData(createRfpForm);
      const requirementsText = (formData.get("requirements") || "").toString();
      const requirements = requirementsText
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .map((text, idx) => ({ id: `req-${idx + 1}`, text }));

      const budgetRaw = formData.get("budget");
      const budget = budgetRaw ? Number(budgetRaw) : null;
      if (!budget || Number.isNaN(budget)) {
        status.textContent = "Please enter a budget.";
        status.className = "form-status error";
        return;
      }
      if (budget < 500 || budget % 500 !== 0) {
        status.textContent = "Budget must be at least 500 and change in steps of 500.";
        status.className = "form-status error";
        return;
      }

      const payload = {
        title: formData.get("title"),
        description: formData.get("description") || null,
        budget,
        currency: formData.get("currency") || "USD",
        deadline: formData.get("deadline") || null,
        requirements,
      };

      try {
        const res = await fetch("/api/rfps", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        status.textContent = "Created! Redirecting...";
        status.className = "form-status success";
        window.location.href = `/rfps/${data.id}`;
      } catch (err) {
        status.textContent = "Error creating RFP.";
        status.className = "form-status error";
        console.error(err);
      }
    });
  }

  const createProposalForm = document.getElementById("create-proposal-form");
  if (createProposalForm) {
    createProposalForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const status = document.getElementById("create-proposal-status");
      status.textContent = "Submitting...";
      status.className = "form-status";

      const rfpId = createProposalForm.dataset.rfpId;
      const formData = new FormData(createProposalForm);
      const hasFile = formData.get("file") && formData.get("file").name;

      try {
        let res;
        if (hasFile) {
          formData.set("rfp_id", rfpId);
          res = await fetch("/api/proposals/upload", {
            method: "POST",
            body: formData,
          });
        } else {
          const payload = {
            rfp_id: rfpId,
            contractor: formData.get("contractor"),
            price: formData.get("price") ? Number(formData.get("price")) : null,
            currency: formData.get("currency") || "USD",
            start_date: formData.get("start_date") || null,
            summary: formData.get("summary") || null,
          };
          res = await fetch("/api/proposals", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
        }
        if (!res.ok) throw new Error(await res.text());
        status.textContent = "Submitted! Refreshing...";
        status.className = "form-status success";
        window.location.reload();
      } catch (err) {
        status.textContent = "Error submitting proposal.";
        status.className = "form-status error";
        console.error(err);
      }
    });
  }

  const chatForm = document.getElementById("chat-form");
  if (chatForm) {
    const chatLog = document.getElementById("chat-log");
    const status = document.getElementById("chat-status");
    chatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      status.textContent = "";
      status.className = "form-status";

      const proposalId = chatForm.dataset.proposalId;
      const formData = new FormData(chatForm);
      const message = formData.get("message");

      const userBubble = document.createElement("div");
      userBubble.className = "chat-message user";
      userBubble.textContent = message;
      chatLog.appendChild(userBubble);
      chatLog.scrollTop = chatLog.scrollHeight;

      try {
        const res = await fetch(`/api/proposals/${proposalId}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ proposal_id: proposalId, message }),
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        const botBubble = document.createElement("div");
        botBubble.className = "chat-message bot";
        botBubble.textContent = data.reply;
        chatLog.appendChild(botBubble);
        chatLog.scrollTop = chatLog.scrollHeight;
      } catch (err) {
        status.textContent = "Error sending message.";
        status.className = "form-status error";
        console.error(err);
      }
      chatForm.reset();
    });
  }

  // Approve / reject buttons on RFP detail page
  const approveButtons = document.querySelectorAll(".approve-btn");
  const rejectButtons = document.querySelectorAll(".reject-btn");

  approveButtons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      const proposalId = btn.dataset.proposalId;
      try {
        const res = await fetch(`/api/proposals/${proposalId}/approve`, {
          method: "POST",
        });
        if (!res.ok) throw new Error(await res.text());
        window.location.reload();
      } catch (err) {
        alert("Error approving proposal.");
        console.error(err);
      }
    });
  });

  rejectButtons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      const proposalId = btn.dataset.proposalId;
      const confirmReject = window.confirm("Reject this proposal and send a feedback email?");
      if (!confirmReject) return;
      try {
        const res = await fetch(`/api/proposals/${proposalId}/reject`, {
          method: "POST",
        });
        if (!res.ok) throw new Error(await res.text());
        window.location.reload();
      } catch (err) {
        alert("Error rejecting proposal.");
        console.error(err);
      }
    });
  });
});

