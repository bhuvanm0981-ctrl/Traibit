
document.addEventListener("DOMContentLoaded", () => {
    // =========================================
    // ELEMENTS
    // =========================================

    const ctaButton = document.getElementById("cta-start");
    const heroButton = document.getElementById("hero-start");
    const mainContent = document.getElementById("main-content");
    const discoverSection = document.getElementById("discover-section");
    const form = document.getElementById("discover-form");
    const loading = document.getElementById("loading");
    const results = document.getElementById("results");

    if (!form || !results || !loading || !mainContent) {
        console.error("Trailbit: Required HTML elements are missing.");
        return;
    }

    // =========================================
    // STATE
    // =========================================

    let currentIssues = [];
    let activeModal = null;

    // =========================================
    // UTILITIES
    // =========================================

    const escapeHTML = (value) => {
        return String(value ?? "").replace(/[&<>"']/g, (char) => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        })[char]);
    };

    const isGitHubURL = (value) => {
        try {
            const url = new URL(value);
            return (
                url.protocol === "https:" &&
                ["github.com", "www.github.com"].includes(url.hostname)
            );
        } catch {
            return false;
        }
    };

    const safeGitHubLink = (value) => {
        if (!isGitHubURL(value)) return "";
        return escapeHTML(value);
    };

    const getErrorMessage = async (response) => {
        try {
            const data = await response.json();

            if (typeof data.detail === "string") {
                return data.detail;
            }

            if (Array.isArray(data.detail)) {
                return data.detail
                    .map(item => item.msg || "Invalid request")
                    .join(", ");
            }

            return `Request failed (${response.status})`;
        } catch {
            return `Request failed (${response.status})`;
        }
    };

    const apiRequest = async (endpoint, payload) => {
        const response = await fetch(endpoint, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(await getErrorMessage(response));
        }

        return response.json();
    };

    const showMessage = (message, type = "info") => {
        results.innerHTML = `
            <div class="issue-card message-card">
                <div class="step-icon">${type === "error" ? "!" : "✦"}</div>
                <h3>${escapeHTML(
                    type === "error" ? "Something went wrong" : "No results yet"
                )}</h3>
                <p>${escapeHTML(message)}</p>
            </div>
        `;
    };

    const setLoading = (isLoading) => {
        loading.classList.toggle("hidden", !isLoading);

        const submitButton = form.querySelector('[type="submit"]');

        if (submitButton) {
            submitButton.disabled = isLoading;
            submitButton.innerHTML = isLoading
                ? "Searching..."
                : 'Discover issues <span>→</span>';
        }
    };

    // =========================================
    // NAVIGATION
    // =========================================

    const openDiscovery = () => {
        mainContent.style.display = "block";

        discoverSection?.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    };

    ctaButton?.addEventListener("click", openDiscovery);
    heroButton?.addEventListener("click", openDiscovery);

    // =========================================
    // DISCOVERY FORM
    // =========================================

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const formData = new FormData(form);

        const payload = {
            language: formData.getAll("language"),
            topic: formData.getAll("topic"),
            experience: formData.get("experience"),
            keywords: formData.get("keywords")?.trim() || null
        };

        if (!payload.language.length) {
            showMessage("Please select at least one programming language.", "error");
            return;
        }

        if (!payload.topic.length) {
            showMessage("Please select at least one area of interest.", "error");
            return;
        }

        results.innerHTML = "";
        setLoading(true);

        try {
            const issues = await apiRequest("/api/discover", payload);

            if (!Array.isArray(issues)) {
                throw new Error("The server returned an unexpected response.");
            }

            currentIssues = issues;

            if (issues.length === 0) {
                showMessage(
                    "We couldn't find matching issues. Try different languages, topics or keywords."
                );
                return;
            }

            renderIssues(issues);

        } catch (error) {
            console.error("Trailbit discovery error:", error);

            showMessage(
                error.message || "Unable to discover issues. Please try again.",
                "error"
            );

        } finally {
            setLoading(false);
        }
    });

    // =========================================
    // ISSUE STATUS
    // =========================================

    const getStatusClass = (status) => {
        if (!status) return "status-unknown";

        const value = status.toLowerCase();

        if (value.includes("unassigned")) return "status-open";
        if (value.includes("assigned")) return "status-assigned";
        if (value.includes("linked pr")) return "status-pr";
        if (value.includes("archived")) return "status-archived";

        return "status-unknown";
    };

    const getStatusLabel = (issue) => {
        if (issue.repo_archived) return "Repository archived";
        return issue.status || "Status not verified";
    };

    const renderEvidenceLinks = (links) => {
        if (!Array.isArray(links) || !links.length) {
            return "";
        }

        const safeLinks = links
            .filter(isGitHubURL)
            .slice(0, 4);

        if (!safeLinks.length) return "";

        return `
            <div class="evidence-links">
                <span>Verification evidence:</span>
                ${safeLinks.map((url, index) => `
                    <a
                        href="${safeGitHubLink(url)}"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        ${index === 0 ? "Issue" : `Evidence ${index}`}
                        ↗
                    </a>
                `).join("")}
            </div>
        `;
    };

    // =========================================
    // RENDER ISSUE CARDS
    // =========================================

    const renderIssues = (issues) => {
        results.innerHTML = `
            <div class="results-heading">
                <div>
                    <div class="section-eyebrow">MATCHING OPPORTUNITIES</div>
                    <h2>${issues.length} opportunities found</h2>
                    <p>Review the evidence before choosing an issue.</p>
                </div>
            </div>

            <div class="results-grid">
                ${issues.map((issue, index) => createIssueCard(issue, index)).join("")}
            </div>
        `;

        results.querySelectorAll(".view-plan").forEach(button => {
            button.addEventListener("click", () => {
                const index = Number(button.dataset.index);
                const issue = currentIssues[index];

                if (issue) {
                    loadPlan(issue, button);
                }
            });
        });
    };

    const createIssueCard = (issue, index) => {
        const issueURL = safeGitHubLink(issue.url);

        const assigned = Array.isArray(issue.assignees)
            ? issue.assignees
            : [];

        const difficulty = issue.difficulty_estimate || "Needs review";

        const archived = issue.repo_archived === true;

        const status = getStatusLabel(issue);

        return `
            <article class="issue-card">

                <div class="issue-card-top">
                    <span class="issue-number">
                        OPPORTUNITY ${String(index + 1).padStart(2, "0")}
                    </span>

                    <span class="status-pill ${getStatusClass(status)}">
                        ${escapeHTML(status)}
                    </span>
                </div>

                <div class="issue-repo">
                    <span class="repo-icon">⌘</span>
                    ${escapeHTML(issue.repo_name || "GitHub repository")}
                </div>

                <h3>
                    ${
                        issueURL
                            ? `<a href="${issueURL}" target="_blank"
                                rel="noopener noreferrer">
                                ${escapeHTML(issue.title)}
                               </a>`
                            : escapeHTML(issue.title)
                    }
                </h3>

                <p class="issue-description">
                    ${escapeHTML(
                        (issue.description || "Open the GitHub issue to read its complete description.")
                            .slice(0, 220)
                    )}${(issue.description || "").length > 220 ? "..." : ""}
                </p>

                <div class="issue-tags">
                    <span>${escapeHTML(issue.language || "Unknown language")}</span>
                    <span>${escapeHTML(issue.topic || "Open source")}</span>
                    <span>${escapeHTML(difficulty)}</span>
                </div>

                <div class="issue-details">
                    <div>
                        <span>Assignees</span>
                        <strong>
                            ${assigned.length
                                ? escapeHTML(assigned.join(", "))
                                : "None listed"}
                        </strong>
                    </div>

                    <div>
                        <span>Comments</span>
                        <strong>${Number(issue.comments_count) || 0}</strong>
                    </div>

                    <div>
                        <span>Linked PR</span>
                        <strong>
                            ${issue.active_pr === true
                                ? "Detected"
                                : issue.active_pr === false
                                    ? "Not detected"
                                    : "Unknown"}
                        </strong>
                    </div>

                    <div>
                        <span>Repository</span>
                        <strong>${archived ? "Archived" : "Active"}</strong>
                    </div>
                </div>

                ${renderEvidenceLinks(issue.evidence_links)}

                <div class="issue-card-actions">
                    ${
                        issueURL
                            ? `<a class="secondary-button issue-link"
                                href="${issueURL}"
                                target="_blank"
                                rel="noopener noreferrer">
                                View issue ↗
                               </a>`
                            : ""
                    }

                    <button
                        type="button"
                        class="primary-button view-plan"
                        data-index="${index}"
                        ${archived ? "disabled" : ""}
                    >
                        ${archived ? "Repository archived" : "Build my roadmap →"}
                    </button>
                </div>

            </article>
        `;
    };

    // =========================================
    // CONTRIBUTION PLAN
    // =========================================

    const loadPlan = async (issue, button) => {
        if (!isGitHubURL(issue.url)) {
            showMessage("This issue does not have a valid GitHub URL.", "error");
            return;
        }

        const originalText = button.textContent;

        button.disabled = true;
        button.textContent = "Building roadmap...";

        try {
            const plan = await apiRequest("/api/contribution-plan", {
                issue_url: issue.url
            });

            if (!plan || !Array.isArray(plan.steps)) {
                throw new Error("The server returned an invalid contribution plan.");
            }

            renderPlan(plan);

        } catch (error) {
            console.error("Contribution plan error:", error);

            showMessage(
                `Unable to generate your roadmap: ${error.message}`,
                "error"
            );

        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    };

    // =========================================
    // CONTRIBUTION ROADMAP MODAL
    // =========================================

    const renderPlan = (plan) => {
        closePlan();

        const overlay = document.createElement("div");
        overlay.className = "plan-overlay modal-overlay";
        overlay.id = "plan-overlay";

        const steps = plan.steps || [];

        const stepsHTML = steps.map((step, index) => `
            <div class="plan-step" data-step="${index}">

                <input
                    type="checkbox"
                    class="plan-checkbox"
                    id="plan-step-${index}"
                    aria-label="Complete ${escapeHTML(step.title)}"
                >

                <div class="plan-step-content">

                    <h3>${index + 1}. ${escapeHTML(step.title)}</h3>

                    <p>${escapeHTML(step.description)}</p>

                    ${step.command ? `
                        <div class="plan-command">
                            <code>${escapeHTML(step.command)}</code>

                            <button
                                type="button"
                                class="copy-command"
                                data-command="${index}"
                            >
                                Copy
                            </button>
                        </div>
                    ` : ""}

                </div>
            </div>
        `).join("");

        const issueLink = safeGitHubLink(plan.issue_url);

        overlay.innerHTML = `
            <div
                class="plan-modal modal-content"
                role="dialog"
                aria-modal="true"
                aria-labelledby="plan-title"
                tabindex="-1"
            >

                <div class="plan-header">

                    <div>
                        <div class="section-eyebrow">YOUR NEXT STEPS</div>
                        <h2 id="plan-title">Your contribution roadmap</h2>
                        <p class="plan-summary">
                            ${escapeHTML(plan.summary)}
                        </p>
                    </div>

                    <button
                        type="button"
                        class="plan-close"
                        aria-label="Close roadmap"
                    >
                        ✕
                    </button>

                </div>

                <div class="plan-progress-section">

                    <div class="plan-progress-label">
                        <strong>Your progress</strong>
                        <span id="plan-count">0/${steps.length} completed</span>
                    </div>

                    <div
                        class="plan-progress"
                        role="progressbar"
                        aria-label="Contribution roadmap progress"
                        aria-valuemin="0"
                        aria-valuemax="100"
                        aria-valuenow="0"
                    >
                        <div
                            class="plan-progress-bar"
                            id="plan-progress-bar"
                        ></div>
                    </div>

                </div>

                <div class="plan-steps">
                    ${stepsHTML || "<p>No roadmap steps were returned.</p>"}
                </div>

                <div class="plan-footer">

                    <p>
                        Take it one step at a time. Always follow the
                        repository's latest contribution guidelines.
                    </p>

                    ${issueLink ? `
                        <a href="${issueLink}"
                           target="_blank"
                           rel="noopener noreferrer">
                            Open original GitHub issue ↗
                        </a>
                    ` : ""}

                </div>

            </div>
        `;

        document.body.appendChild(overlay);
        activeModal = overlay;

        const modal = overlay.querySelector(".plan-modal");

        modal.focus();

        overlay.querySelector(".plan-close")
            .addEventListener("click", closePlan);

        overlay.addEventListener("click", (event) => {
            if (event.target === overlay) {
                closePlan();
            }
        });

        // Update progress
        const checkboxes = overlay.querySelectorAll(".plan-checkbox");
        const count = overlay.querySelector("#plan-count");
        const progressBar = overlay.querySelector("#plan-progress-bar");
        const progress = overlay.querySelector(".plan-progress");

        checkboxes.forEach(checkbox => {
            checkbox.addEventListener("change", () => {
                const step = checkbox.closest(".plan-step");

                step.classList.toggle("completed", checkbox.checked);

                const completed = [...checkboxes]
                    .filter(item => item.checked).length;

                const percentage = checkboxes.length
                    ? (completed / checkboxes.length) * 100
                    : 0;

                count.textContent =
                    `${completed}/${checkboxes.length} completed`;

                progressBar.style.width = `${percentage}%`;

                progress.setAttribute(
                    "aria-valuenow",
                    String(Math.round(percentage))
                );
            });
        });

        // Copy commands
        overlay.querySelectorAll(".copy-command").forEach(button => {
            button.addEventListener("click", async () => {
                const step = button.closest(".plan-step");
                const command = step.querySelector("code")?.textContent;

                if (!command) return;

                try {
                    await copyText(command);
                    button.textContent = "Copied!";
                } catch {
                    button.textContent = "Copy failed";
                }

                setTimeout(() => {
                    if (button.isConnected) {
                        button.textContent = "Copy";
                    }
                }, 1600);
            });
        });

        document.addEventListener("keydown", handleEscape);
    };

    // =========================================
    // CLIPBOARD
    // =========================================

    const copyText = async (text) => {
        if (navigator.clipboard && window.isSecureContext) {
            return navigator.clipboard.writeText(text);
        }

        const textarea = document.createElement("textarea");

        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";

        document.body.appendChild(textarea);

        textarea.select();

        const success = document.execCommand("copy");

        textarea.remove();

        if (!success) {
            throw new Error("Clipboard copy was unsuccessful.");
        }
    };

    // =========================================
    // CLOSE MODAL
    // =========================================

    const handleEscape = (event) => {
        if (event.key === "Escape") {
            closePlan();
        }
    };

    const closePlan = () => {
        activeModal?.remove();
        activeModal = null;

        document.removeEventListener("keydown", handleEscape);
    };

    // =========================================
    // INITIALIZE
    // =========================================

    console.log("Trailbit frontend initialized successfully.");
});
