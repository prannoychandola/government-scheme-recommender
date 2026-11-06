(() => {
  const messages = document.querySelector("#messages");
  const composerArea = document.querySelector("#composer-area");
  const recommendations = document.querySelector("#recommendations");
  const restartButton = document.querySelector("#restart-button");
  const beginButton = document.querySelector("#begin-button");
  const progressLabel = document.querySelector("#progress-label");
  const assistantStatus = document.querySelector("#assistant-status");
  const categoryList = document.querySelector("#category-list");
  const dialog = document.querySelector("#scheme-dialog");
  const dialogTitle = document.querySelector("#dialog-title");
  const dialogContent = document.querySelector("#dialog-content");
  const toast = document.querySelector("#toast");
  const state = { profile: {}, stage: "start", busy: false, started: false, schemes: new Map() };

  const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add("visible");
    window.clearTimeout(showToast.timeout);
    showToast.timeout = window.setTimeout(() => toast.classList.remove("visible"), 2800);
  }

  function addMessage(text, kind = "assistant") {
    const row = document.createElement("div");
    row.className = `message-row ${kind === "user" ? "user-row" : "assistant-row"}`;
    const bubble = document.createElement("div");
    bubble.className = `message-bubble ${kind === "user" ? "user-bubble" : "assistant-bubble"}`;
    bubble.textContent = text;
    row.append(bubble);
    messages.append(row);
    messages.scrollTop = messages.scrollHeight;
  }

  function setTyping(active) {
    messages.querySelector(".typing-row")?.remove();
    if (!active) return;
    const row = document.createElement("div");
    row.className = "message-row assistant-row typing-row";
    row.innerHTML = '<span class="message-bubble assistant-bubble typing-bubble" aria-label="Directory is checking the catalogue"><i></i><i></i><i></i></span>';
    messages.append(row);
    messages.scrollTop = messages.scrollHeight;
  }

  async function api(path, body) {
    const response = await fetch(path, {
      method: body ? "POST" : "GET",
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "The request could not be completed.");
    return payload;
  }

  function renderComposer(data) {
    composerArea.replaceChildren();
    if (!state.started) {
      const hint = document.createElement("p");
      hint.className = "composer-hint";
      hint.textContent = "Start a search to continue.";
      composerArea.append(hint);
      return;
    }

    if (data?.options?.length) {
      const options = document.createElement("div");
      options.className = "option-list";
      data.options.forEach((value) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "option-button";
        button.textContent = value;
        button.disabled = state.busy;
        button.addEventListener("click", () => submit(value));
        options.append(button);
      });
      composerArea.append(options);
    }

    const form = document.createElement("form");
    form.className = "input-row";
    const input = document.createElement("input");
    input.className = "chat-input";
    input.name = "message";
    input.maxLength = state.stage === "complete" ? 500 : 120;
    input.autocomplete = "off";
    input.setAttribute("aria-label", "Your answer");
    input.placeholder = state.stage === "complete" ? "Why this, show more, or restart" : "Type your answer";
    input.disabled = state.busy;
    form.append(input);
    if (data?.optional && state.stage !== "complete") {
      const skip = document.createElement("button");
      skip.type = "button";
      skip.className = "skip-button";
      skip.textContent = "Skip";
      skip.disabled = state.busy;
      skip.addEventListener("click", () => submit(""));
      form.append(skip);
    }
    const send = document.createElement("button");
    send.type = "submit";
    send.className = "send-button";
    send.textContent = "Send →";
    send.disabled = state.busy;
    form.append(send);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      submit(input.value.trim());
    });
    composerArea.append(form);
    if (!data?.options?.length) input.focus({ preventScroll: true });
  }

  function renderSchemeCard(scheme) {
    state.schemes.set(scheme.scheme_id, scheme);
    const safeWebsite = /^https:\/\//i.test(scheme.official_website) ? scheme.official_website : "";
    const reasons = (scheme.recommendation_reasons || []).map(escapeHTML).join(" · ");
    const notes = (scheme.verification_notes || []).map(escapeHTML).join(" · ");
    return `<article class="scheme-card">
      <div class="scheme-card-top"><div><h3 class="scheme-title">${escapeHTML(scheme.scheme_name)}</h3><span class="category-label">${escapeHTML(scheme.category)}</span></div><span class="score-label">${escapeHTML(scheme.relevance_score)} match</span></div>
      <p class="scheme-description">${escapeHTML(scheme.description)}</p>
      <div class="card-meta"><span><strong>Benefits:</strong> ${escapeHTML(scheme.benefits)}</span>${reasons ? `<span><strong>Why shown:</strong> ${reasons}</span>` : ""}${notes ? `<span><strong>Check:</strong> ${notes}</span>` : ""}</div>
      <span class="eligibility-badge ${scheme.eligibility_status === "No listed conflicts" ? "verified" : ""}">${escapeHTML(scheme.eligibility_status)}</span>
      <div class="scheme-card-actions"><button class="text-action" type="button" data-detail="${escapeHTML(scheme.scheme_id)}">View details</button>${safeWebsite ? `<a class="official-link" href="${escapeHTML(safeWebsite)}" target="_blank" rel="noopener noreferrer">Official source ↗</a>` : ""}</div>
    </article>`;
  }

  function renderRecommendations(items) {
    recommendations.replaceChildren();
    if (!items) return;
    if (!items.length) {
      recommendations.innerHTML = '<div class="empty-state">No catalogue entries matched the explicit criteria available. Try skipping fewer questions or broadening your focus. This does not mean you are ineligible for other programmes.</div>';
      return;
    }
    const heading = document.createElement("div");
    heading.className = "recommendation-heading";
    heading.innerHTML = `<h2>Possible matches <span>(${items.length})</span></h2><span>Rule-match score, not approval probability</span>`;
    const list = document.createElement("div");
    list.className = "scheme-list";
    list.innerHTML = items.map(renderSchemeCard).join("");
    recommendations.append(heading, list);
    messages.scrollTop = messages.scrollHeight;
  }

  async function submit(value) {
    if (state.busy) return;
    const message = String(value ?? "").trim();
    if (!message && state.stage !== "start" && !document.querySelector(".skip-button")) return;
    if (message) addMessage(message, "user");
    state.busy = true;
    assistantStatus.textContent = "Checking the catalogue…";
    renderComposer({ options: state.currentOptions, optional: state.currentOptional });
    setTyping(true);
    try {
      const result = await api("/api/chat", { message, profile: state.profile, stage: state.stage });
      setTyping(false);
      state.profile = result.profile || state.profile;
      state.stage = result.stage || "complete";
      state.currentOptions = result.options || [];
      state.currentOptional = Boolean(result.optional);
      if (result.progress) progressLabel.textContent = `Question ${result.progress.current} of ${result.progress.total}`;
      else progressLabel.textContent = state.stage === "complete" ? "Search complete" : "";
      assistantStatus.textContent = state.stage === "complete" ? "Ask a follow-up or start over" : "Guided search";
      addMessage(result.reply);
      if (result.recommendations) renderRecommendations(result.recommendations);
      renderComposer(result);
    } catch (error) {
      setTyping(false);
      addMessage(error.message);
      renderComposer({ options: state.currentOptions, optional: state.currentOptional });
      showToast(error.message);
    } finally {
      state.busy = false;
      restartButton.disabled = false;
      composerArea.querySelectorAll("button").forEach((button) => { button.disabled = false; });
      const input = composerArea.querySelector("input");
      if (input) input.disabled = false;
    }
  }

  function reset() {
    state.profile = {};
    state.stage = "start";
    state.busy = false;
    state.started = false;
    state.currentOptions = [];
    state.currentOptional = false;
    messages.innerHTML = '<div class="message-row assistant-row"><div class="message-bubble assistant-bubble">Hello. I can help you explore government scheme listings. We’ll take this one question at a time, and you can skip optional details.</div></div><div class="welcome-actions"><button id="begin-button" class="primary-button" type="button">Begin a search <span aria-hidden="true">→</span></button></div>';
    recommendations.replaceChildren();
    progressLabel.textContent = "";
    assistantStatus.textContent = "Ready when you are";
    restartButton.disabled = true;
    renderComposer();
    document.querySelector("#begin-button").addEventListener("click", start);
  }

  async function start() {
    state.started = true;
    state.stage = "start";
    document.querySelector(".welcome-actions")?.remove();
    await submit("");
  }

  function detailItem(label, value, wide = false) {
    const safeValue = escapeHTML(value || "Unknown - verify");
    return `<section class="detail-item ${wide ? "wide" : ""}"><h3>${escapeHTML(label)}</h3><p>${safeValue}</p></section>`;
  }

  async function showDetails(id) {
    try {
      const payload = await api(`/api/scheme/${encodeURIComponent(id)}`);
      const scheme = payload.scheme;
      dialogTitle.textContent = scheme.scheme_name;
      const website = /^https:\/\//i.test(scheme.official_website)
        ? `<a href="${escapeHTML(scheme.official_website)}" target="_blank" rel="noopener noreferrer">Open official source ↗</a>`
        : "No validated URL available";
      dialogContent.innerHTML = `<div class="detail-notice">${escapeHTML(scheme.verification_status)}. Confirm current eligibility, benefit details, documents, deadlines and application steps with the department before acting.</div>
        <div class="detail-grid">
          ${detailItem("Category", scheme.category)}${detailItem("Department", scheme.government_department)}
          ${detailItem("Description", scheme.description, true)}${detailItem("Eligibility criteria", scheme.eligibility_criteria, true)}
          ${detailItem("Age range", `${scheme.minimum_age} to ${scheme.maximum_age}`)}${detailItem("Gender eligibility", scheme.gender_eligibility)}
          ${detailItem("Income limit", scheme.income_limit)}${detailItem("State eligibility", scheme.state_eligibility)}
          ${detailItem("Education", scheme.education_requirement)}${detailItem("Occupation", scheme.occupation_requirement)}
          ${detailItem("Benefits", scheme.benefits, true)}${detailItem("Documents required", scheme.required_documents, true)}
          ${detailItem("Application procedure", scheme.application_process, true)}
          <section class="detail-item wide"><h3>Official website</h3><p>${website}</p></section>
          ${detailItem("Source note", scheme.source_note, true)}
        </div>`;
      dialog.showModal();
    } catch (error) {
      showToast(error.message);
    }
  }

  beginButton.addEventListener("click", start);
  restartButton.addEventListener("click", reset);
  document.querySelector("#close-dialog").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
  recommendations.addEventListener("click", (event) => {
    const button = event.target.closest("[data-detail]");
    if (button) showDetails(button.dataset.detail);
  });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && dialog.open) dialog.close(); });

  api("/api/schemes").then(({ schemes }) => {
    const categories = [...new Set(schemes.map((scheme) => scheme.category))].sort();
    categoryList.innerHTML = categories.map((category) => `<button type="button" class="category-chip">${escapeHTML(category)}</button>`).join("");
    categoryList.addEventListener("click", (event) => {
      const button = event.target.closest(".category-chip");
      if (!button) return;
      if (!state.started) start();
      const tryFocus = () => {
        const option = [...composerArea.querySelectorAll(".option-button")].find((item) => item.textContent.toLowerCase().includes(button.textContent.toLowerCase()));
        if (option) option.click();
        else showToast("Choose an area when the focus question appears.");
      };
      window.setTimeout(tryFocus, 80);
    });
  }).catch(() => {
    categoryList.textContent = "Categories unavailable";
  });
})();