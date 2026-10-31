
document.addEventListener('DOMContentLoaded', () => {
  const ctaBtn = document.getElementById('cta-start');
  const mainContent = document.getElementById('main-content');
  const form = document.getElementById('discover-form');
  const loadingDiv = document.getElementById('loading');
  const resultsDiv = document.getElementById('results');

  // Add contribution plan styling
  const styles = document.createElement('style');

  styles.textContent = `
    .plan-overlay {
      position: fixed;
      inset: 0;
      z-index: 9999;
      background: rgba(0, 0, 0, 0.78);
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 20px;
      overflow-y: auto;
    }

    .plan-modal {
      width: 100%;
      max-width: 760px;
      max-height: 90vh;
      overflow-y: auto;
      background: #151b2b;
      color: #e5e7eb;
      border: 1px solid #303b52;
      border-radius: 16px;
      padding: 28px;
      box-shadow: 0 20px 60px rgba(0,0,0,.5);
    }

    .plan-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 15px;
      margin-bottom: 20px;
    }

    .plan-header h2 {
      margin: 0 0 8px;
      color: #fff;
    }

    .plan-close {
      background: #29344a;
      color: white;
      border: none;
      border-radius: 8px;
      padding: 9px 13px;
      cursor: pointer;
    }

    .plan-summary {
      color: #aab6ca;
      line-height: 1.6;
      margin-bottom: 22px;
    }

    .plan-progress {
      background: #273248;
      height: 8px;
      border-radius: 20px;
      overflow: hidden;
      margin: 12px 0 8px;
    }

    .plan-progress-bar {
      height: 100%;
      width: 0%;
      background: #36c98f;
      transition: width .2s ease;
    }

    .plan-step {
      display: flex;
      gap: 14px;
      padding: 17px;
      margin-top: 12px;
      background: #1d273a;
      border: 1px solid #303b52;
      border-radius: 11px;
    }

    .plan-step input {
      width: 18px;
      height: 18px;
      accent-color: #36c98f;
      cursor: pointer;
      flex-shrink: 0;
      margin-top: 4px;
    }

    .plan-step-content {
      flex: 1;
      min-width: 0;
    }

    .plan-step h3 {
      font-size: 16px;
      margin: 0 0 8px;
      color: #fff;
    }

    .plan-step p {
      color: #bac5d7;
      line-height: 1.6;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      margin: 0;
    }

    .plan-command {
      background: #0c1220;
      padding: 12px;
      border-radius: 8px;
      margin-top: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
    }

    .plan-command code {
      color: #75e6b3;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }

    .copy-command {
      background: #34445f;
      color: white;
      border: none;
      padding: 7px 10px;
      border-radius: 6px;
      cursor: pointer;
      flex-shrink: 0;
    }

    .plan-step.completed {
      opacity: .65;
    }

    .plan-step.completed h3 {
      text-decoration: line-through;
    }

    .plan-footer {
      margin-top: 22px;
      padding-top: 16px;
      border-top: 1px solid #303b52;
      color: #9ba9bf;
      font-size: 13px;
    }

    @media(max-width: 600px) {
      .plan-modal {
        padding: 18px;
      }

      .plan-overlay {
        padding: 10px;
      }
    }
  `;

  document.head.appendChild(styles);

  // Utility to safely display text
  const escapeHTML = (value) => {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    })[char]);
  };

  const showMessage = (msg, isError = false) => {
    resultsDiv.textContent = msg;
    resultsDiv.style.color = isError ? '#f88' : '#8f8';
  };

  // Show discovery interface
  if (ctaBtn && mainContent) {
    ctaBtn.addEventListener('click', () => {
      mainContent.style.display = 'block';
      ctaBtn.style.display = 'none';
    });
  }

  // Search issues
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    resultsDiv.innerHTML = '';
    loadingDiv.classList.remove('hidden');

    const data = new FormData(form);

    const payload = {
      language: data.getAll('language'),
      topic: data.getAll('topic'),
      experience: data.get('experience'),
      keywords: data.get('keywords')?.trim() || undefined
    };

    try {
      const response = await fetch('/api/discover', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `Server ${response.status}`);
      }

      const issues = await response.json();

      if (!issues.length) {
        showMessage('No matching issues found.');
        return;
      }

      renderIssues(issues);

    } catch (error) {
      showMessage(`Error: ${error.message}`, true);

    } finally {
      loadingDiv.classList.add('hidden');
    }
  });

  // Render issue cards
  const renderIssues = (issues) => {
    resultsDiv.innerHTML = '';

    issues.forEach(issue => {
      const card = document.createElement('div');
      card.className = 'card';

      card.innerHTML = `
        <h3>
          <a href="${escapeHTML(issue.url)}"
             target="_blank"
             rel="noopener noreferrer">
             ${escapeHTML(issue.title)}
          </a>
        </h3>

        <p><strong>Repository:</strong>
          ${escapeHTML(issue.repo_name)}
        </p>

        <p><strong>Language:</strong>
          ${escapeHTML(issue.language)}
        </p>

        <p><strong>Topic:</strong>
          ${escapeHTML(issue.topic)}
        </p>

        <p><strong>Difficulty:</strong>
          ${escapeHTML(issue.difficulty_estimate || 'Not assessed')}
        </p>

        <button type="button" class="view-plan">
          View Contribution Plan
        </button>
      `;

      card.querySelector('.view-plan').addEventListener(
        'click',
        () => loadPlan(issue.url)
      );

      resultsDiv.appendChild(card);
    });
  };

  // Fetch contribution plan
  const loadPlan = async (url) => {
    try {
      const button = [...resultsDiv.querySelectorAll('.view-plan')]
        .find(btn => btn.closest('.card')?.querySelector('a')?.href === url);

      if (button) {
        button.disabled = true;
        button.textContent = 'Generating plan...';
      }

      const response = await fetch('/api/contribution-plan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ issue_url: url })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `Server ${response.status}`);
      }

      const plan = await response.json();

      renderPlan(plan);

    } catch (error) {
      alert(`Failed to generate plan: ${error.message}`);

    } finally {
      resultsDiv.querySelectorAll('.view-plan').forEach(button => {
        button.disabled = false;
        button.textContent = 'View Contribution Plan';
      });
    }
  };

  // Render interactive contribution roadmap
  const renderPlan = (plan) => {
    closePlan();

    const overlay = document.createElement('div');
    overlay.className = 'plan-overlay';
    overlay.id = 'plan-overlay';

    const stepsHTML = plan.steps.map((step, index) => `
      <div class="plan-step" data-step="${index}">
        <input type="checkbox" aria-label="Complete ${escapeHTML(step.title)}">

        <div class="plan-step-content">
          <h3>${index + 1}. ${escapeHTML(step.title)}</h3>

          <p>${escapeHTML(step.description)}</p>

          ${step.command ? `
            <div class="plan-command">
              <code>${escapeHTML(step.command)}</code>
              <button class="copy-command" type="button">
                Copy
              </button>
            </div>
          ` : ''}
        </div>
      </div>
    `).join('');

    overlay.innerHTML = `
      <div class="plan-modal" role="dialog" aria-modal="true"
           aria-labelledby="plan-title">

        <div class="plan-header">
          <div>
            <h2 id="plan-title">Your Contribution Roadmap</h2>
            <span style="color:#75e6b3;font-size:13px;">
              OPEN SOURCE CONTRIBUTION
            </span>
          </div>

          <button class="plan-close" type="button">
            Close ✕
          </button>
        </div>

        <div class="plan-summary">
          ${escapeHTML(plan.summary)}
        </div>

        <div>
          <strong>Progress:
            <span id="plan-count">0/${plan.steps.length}</span>
          </strong>

          <div class="plan-progress">
            <div class="plan-progress-bar" id="plan-progress-bar"></div>
          </div>
        </div>

        <div class="plan-steps">
          ${stepsHTML}
        </div>

        <div class="plan-footer">
          Follow these steps to prepare your contribution.
          Always check the repository's latest contribution guidelines.
          <br><br>
          <a href="${escapeHTML(plan.issue_url)}"
             target="_blank"
             rel="noopener noreferrer"
             style="color:#75e6b3;">
             Open original GitHub issue ↗
          </a>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    overlay.querySelector('.plan-close').addEventListener(
      'click',
      closePlan
    );

    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) {
        closePlan();
      }
    });

    // Update progress when a step is completed
    const checkboxes = overlay.querySelectorAll(
      '.plan-step input[type="checkbox"]'
    );

    checkboxes.forEach(checkbox => {
      checkbox.addEventListener('change', () => {
        const step = checkbox.closest('.plan-step');
        step.classList.toggle('completed', checkbox.checked);

        const completed = [...checkboxes]
          .filter(item => item.checked).length;

        const total = checkboxes.length;
        const percentage = total
          ? (completed / total) * 100
          : 0;

        overlay.querySelector('#plan-count').textContent =
          `${completed}/${total}`;

        overlay.querySelector('#plan-progress-bar').style.width =
          `${percentage}%`;
      });
    });

    // Copy Git commands
    overlay.querySelectorAll('.copy-command').forEach(button => {
      button.addEventListener('click', async () => {
        const command = button
          .parentElement
          .querySelector('code')
          .textContent;

        try {
          await navigator.clipboard.writeText(command);
          button.textContent = 'Copied!';
        } catch {
          button.textContent = 'Copy failed';
        }

        setTimeout(() => {
          button.textContent = 'Copy';
        }, 1500);
      });
    });

    // Escape key closes the roadmap
    document.addEventListener('keydown', handleEscape);
  };

  const handleEscape = (event) => {
    if (event.key === 'Escape') {
      closePlan();
    }
  };

  const closePlan = () => {
    document.getElementById('plan-overlay')?.remove();
    document.removeEventListener('keydown', handleEscape);
  };
});
