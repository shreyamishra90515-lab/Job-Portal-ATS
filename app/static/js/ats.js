/**
 * Job Portal & Application Tracking System (ATS)
 * Phase 5: Vanilla JavaScript API & Security Integration
 * - Zero inline scripts (strict CSP compliant)
 * - Automatic X-CSRF-Token injection from <meta name="csrf-token">
 */

(function () {
    "use strict";

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute("content") : "";
    }

    function updateCsrfToken(newToken) {
        if (!newToken) return;
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) meta.setAttribute("content", newToken);
        document.querySelectorAll('input[name="csrf_token"]').forEach((el) => {
            el.value = newToken;
        });
    }

    function showToast(message, type = "success") {
        const container = document.getElementById("ats-toast-container");
        if (!container) return;

        const alertEl = document.createElement("div");
        alertEl.className = `alert alert-${type} alert-dismissible fade show shadow-sm`;
        alertEl.setAttribute("role", "alert");
        alertEl.textContent = message;

        const closeBtn = document.createElement("button");
        closeBtn.type = "button";
        closeBtn.className = "btn-close";
        closeBtn.setAttribute("data-bs-dismiss", "alert");
        closeBtn.setAttribute("aria-label", "Close");
        alertEl.appendChild(closeBtn);

        container.appendChild(alertEl);
        window.setTimeout(() => {
            alertEl.remove();
        }, 6000);
    }

    async function apiRequest(url, method = "GET", payload = null) {
        const headers = { Accept: "application/json" };
        if (method !== "GET" && method !== "HEAD") {
            headers["X-CSRF-Token"] = getCsrfToken();
        }
        const options = { method, headers, credentials: "same-origin" };
        if (payload !== null) {
            headers["Content-Type"] = "application/json";
            options.body = JSON.stringify(payload);
        }

        const resp = await fetch(url, options);
        const rotated = resp.headers.get("X-CSRF-Token");
        if (rotated) updateCsrfToken(rotated);

        let data = {};
        try {
            data = await resp.json();
        } catch (_) {
            data = {};
        }

        if (!resp.ok) {
            throw new Error(data.error || `Request failed (${resp.status})`);
        }
        return data;
    }

    function formToObject(form) {
        const obj = {};
        const formData = new FormData(form);
        for (const [key, value] of formData.entries()) {
            if (key === "csrf_token") continue;
            const input = form.elements[key];
            if (input && input.type === "checkbox") {
                obj[key] = input.checked;
            } else if (input && input.type === "number") {
                obj[key] = value === "" ? null : Number(value);
            } else {
                obj[key] = value;
            }
        }
        // Include unchecked checkboxes
        form.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
            if (cb.name && !(cb.name in obj)) {
                obj[cb.name] = false;
            }
        });
        return obj;
    }

    function bindGenericApiForms() {
        document.querySelectorAll("form[data-api-url]").forEach((form) => {
            form.addEventListener("submit", async (e) => {
                e.preventDefault();
                const url = form.getAttribute("data-api-url");
                const method = (form.getAttribute("data-api-method") || "POST").toUpperCase();
                const reload = form.getAttribute("data-reload") === "true";
                const redirectTo = form.getAttribute("data-redirect");
                const payload = formToObject(form);

                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) submitBtn.disabled = true;

                try {
                    const result = await apiRequest(url, method, payload);
                    showToast(result.message || "Saved successfully.", "success");
                    if (redirectTo) {
                        window.location.href = redirectTo;
                    } else if (reload) {
                        window.setTimeout(() => window.location.reload(), 650);
                    }
                } catch (err) {
                    showToast(err.message, "danger");
                } finally {
                    if (submitBtn) submitBtn.disabled = false;
                }
            });
        });
    }

    function bindGenericApiButtons() {
        document.querySelectorAll("[data-api-action]").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const confirmMsg = btn.getAttribute("data-confirm");
                if (confirmMsg && !window.confirm(confirmMsg)) return;

                const url = btn.getAttribute("data-api-action");
                const method = (btn.getAttribute("data-api-method") || "POST").toUpperCase();
                let payload = null;
                const rawPayload = btn.getAttribute("data-api-payload");
                if (rawPayload) {
                    try {
                        payload = JSON.parse(rawPayload);
                    } catch (_) {
                        payload = null;
                    }
                }

                btn.disabled = true;
                try {
                    const result = await apiRequest(url, method, payload);
                    showToast(result.message || "Action completed.", "success");
                    window.setTimeout(() => window.location.reload(), 650);
                } catch (err) {
                    showToast(err.message, "danger");
                    btn.disabled = false;
                }
            });
        });
    }

    function bindCandidateTimelineModal() {
        const modalEl = document.getElementById("applicationHistoryModal");
        if (!modalEl) return;

        const bodyEl = document.getElementById("historyModalBody");
        document.querySelectorAll(".btn-view-history").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const appId = btn.getAttribute("data-app-id");
                const jobTitle = btn.getAttribute("data-job-title") || "Application";
                const titleEl = document.getElementById("historyModalTitle");
                if (titleEl) titleEl.textContent = `Status History — ${jobTitle}`;
                if (bodyEl) bodyEl.innerHTML = '<div class="text-muted py-3">Loading audit history...</div>';

                try {
                    const data = await apiRequest(`/api/applications/${appId}/history`, "GET");
                    const items = data.history || [];
                    if (!items.length) {
                        bodyEl.innerHTML = '<p class="text-muted mb-0">No status history recorded.</p>';
                        return;
                    }
                    const list = document.createElement("ul");
                    list.className = "list-group list-group-flush";
                    items.forEach((h) => {
                        const li = document.createElement("li");
                        li.className = "list-group-item px-0";

                        const header = document.createElement("div");
                        header.className = "d-flex justify-content-between align-items-center";

                        const transition = document.createElement("strong");
                        transition.textContent = h.old_status
                            ? `${h.old_status} → ${h.new_status}`
                            : `INITIAL → ${h.new_status}`;

                        const ts = document.createElement("small");
                        ts.className = "text-muted";
                        ts.textContent = h.changed_at || "";

                        header.appendChild(transition);
                        header.appendChild(ts);
                        li.appendChild(header);

                        if (h.change_notes) {
                            const notes = document.createElement("div");
                            notes.className = "small text-secondary mt-1";
                            notes.textContent = h.change_notes;
                            li.appendChild(notes);
                        }
                        list.appendChild(li);
                    });
                    bodyEl.innerHTML = "";
                    bodyEl.appendChild(list);
                } catch (err) {
                    bodyEl.textContent = err.message;
                }
            });
        });
    }

    function bindRecruiterJobEditModal() {
        const form = document.getElementById("editJobForm");
        if (!form) return;

        document.querySelectorAll(".btn-edit-job").forEach((btn) => {
            btn.addEventListener("click", () => {
                const jobId = btn.getAttribute("data-job-id");
                form.setAttribute("data-api-url", `/api/jobs/${jobId}`);
                form.elements["title"].value = btn.getAttribute("data-title") || "";
                form.elements["description"].value = btn.getAttribute("data-description") || "";
                form.elements["location"].value = btn.getAttribute("data-location") || "";
                form.elements["employment_type"].value = btn.getAttribute("data-employment-type") || "FULL_TIME";
                form.elements["workplace_type"].value = btn.getAttribute("data-workplace-type") || "ON_SITE";
                form.elements["min_experience_years"].value = btn.getAttribute("data-min-exp") || "0";
                form.elements["salary_min"].value = btn.getAttribute("data-salary-min") || "";
                form.elements["salary_max"].value = btn.getAttribute("data-salary-max") || "";
                form.elements["status"].value = btn.getAttribute("data-status") || "ACTIVE";
                form.elements["deadline_date"].value = btn.getAttribute("data-deadline") || "";
            });
        });
    }

    function bindRecruiterJobSkillModal() {
        const form = document.getElementById("addJobSkillForm");
        if (!form) return;

        document.querySelectorAll(".btn-manage-job-skills").forEach((btn) => {
            btn.addEventListener("click", () => {
                const jobId = btn.getAttribute("data-job-id");
                const jobTitle = btn.getAttribute("data-job-title") || "Job";
                form.setAttribute("data-api-url", `/api/jobs/${jobId}/skills`);
                const titleEl = document.getElementById("jobSkillsModalTitle");
                if (titleEl) titleEl.textContent = `Manage Skills — ${jobTitle}`;
            });
        });
    }

    function bindRecruiterApplicantControls() {
        const statusForm = document.getElementById("updateAppStatusForm");
        if (statusForm) {
            document.querySelectorAll(".btn-open-status-modal").forEach((btn) => {
                btn.addEventListener("click", () => {
                    const appId = btn.getAttribute("data-app-id");
                    const current = btn.getAttribute("data-current-status") || "UNDER_REVIEW";
                    const candName = btn.getAttribute("data-candidate-name") || "";
                    statusForm.setAttribute("data-api-url", `/api/applications/${appId}/status`);
                    statusForm.elements["status"].value = current;
                    statusForm.elements["change_notes"].value = "";
                    const titleEl = document.getElementById("statusModalTitle");
                    if (titleEl) titleEl.textContent = `Update Status — ${candName}`;
                });
            });
        }

        const intForm = document.getElementById("scheduleInterviewForm");
        if (intForm) {
            document.querySelectorAll(".btn-open-interview-modal").forEach((btn) => {
                btn.addEventListener("click", () => {
                    const appId = btn.getAttribute("data-app-id");
                    const candName = btn.getAttribute("data-candidate-name") || "";
                    intForm.elements["application_id"].value = appId;
                    const titleEl = document.getElementById("interviewModalTitle");
                    if (titleEl) titleEl.textContent = `Schedule Interview — ${candName}`;
                });
            });
        }
    }

    function bindRecruiterInterviewEditModal() {
        const form = document.getElementById("editInterviewForm");
        if (!form) return;

        document.querySelectorAll(".btn-edit-interview").forEach((btn) => {
            btn.addEventListener("click", () => {
                const intId = btn.getAttribute("data-interview-id");
                const candName = btn.getAttribute("data-candidate-name") || "";
                form.setAttribute("data-api-url", `/api/interviews/${intId}`);
                form.elements["status"].value = btn.getAttribute("data-status") || "SCHEDULED";
                form.elements["rating"].value = btn.getAttribute("data-rating") || "";
                form.elements["feedback"].value = btn.getAttribute("data-feedback") || "";
                const titleEl = document.getElementById("editInterviewModalTitle");
                if (titleEl) titleEl.textContent = `Evaluate Interview — ${candName}`;
            });
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        bindGenericApiForms();
        bindGenericApiButtons();
        bindCandidateTimelineModal();
        bindRecruiterJobEditModal();
        bindRecruiterJobSkillModal();
        bindRecruiterApplicantControls();
        bindRecruiterInterviewEditModal();
    });
})();

