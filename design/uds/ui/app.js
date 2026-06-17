/* UDS application-UI — progressive enhancement (ADR-006, Slice C0 / #125).
 *
 * Behaviour for the archetypes whose contracts seal interaction:
 *   • shelf  — toggleable (sealed: collapse-behaviour)
 *   • modal  — focus-trap + Esc/scrim/close dismissal + focus restore (sealed)
 *   • control/login — the gateway → TwentyCRM auth contract (see submitLogin)
 *
 * Vanilla, dependency-free, additive: the markup is meaningful without it. The
 * server modes (ADR-006 §5, the nopilot-co-www save fan-out) re-implement the
 * same contracts; this is the canonical HTML behaviour.
 */
(() => {
  "use strict";

  /* ----- shelf toggles: [data-uds-toggle="<shelf-id>"] flips [data-collapsed] */
  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-uds-toggle]");
    if (!t) return;
    const shelf = document.getElementById(t.getAttribute("data-uds-toggle"));
    if (!shelf) return;
    const collapsed = shelf.getAttribute("data-collapsed") === "true";
    shelf.setAttribute("data-collapsed", String(!collapsed));
    t.setAttribute("aria-expanded", String(collapsed));
  });

  /* ----- navigation groups: a trigger discloses its sub-items; clicking any nav
     item in a collapsed rail re-expands the shelf first ----------------------- */
  document.addEventListener("click", (e) => {
    const item = e.target.closest(".uds-navigation__item");
    if (item) {
      const shelf = item.closest('.uds-shelf[data-collapsed="true"]');
      if (shelf) {                                  // rail click → expand, then act
        shelf.setAttribute("data-collapsed", "false");
        const tgl = document.querySelector(`[data-uds-toggle="${shelf.id}"]`);
        if (tgl) tgl.setAttribute("aria-expanded", "true");
      }
    }
    const trig = e.target.closest(".uds-navigation__trigger");
    if (!trig) return;
    e.preventDefault();
    const group = trig.closest(".uds-navigation__group");
    if (!group) return;
    const open = group.getAttribute("data-collapsed") === "false";
    group.setAttribute("data-collapsed", String(open));
    trig.setAttribute("aria-expanded", String(!open));
  });

  /* ----- modal: focus trap, Esc/scrim/close dismissal, focus restore --------- */
  let lastFocus = null;
  const focusables = (root) =>
    [...root.querySelectorAll('a[href],button:not([disabled]),input,select,textarea,[tabindex]:not([tabindex="-1"])')]
      .filter((el) => el.offsetParent !== null);

  function openModal(id) {
    const m = document.getElementById(id);
    if (!m) return;
    lastFocus = document.activeElement;
    m.hidden = false;
    const f = focusables(m);
    (f[0] || m).focus();
    m.addEventListener("keydown", trap);
  }
  function closeModal(m) {
    if (!m || m.hidden) return;
    m.hidden = true;
    m.removeEventListener("keydown", trap);
    if (lastFocus) lastFocus.focus();
  }
  function trap(e) {
    const m = e.currentTarget;
    if (e.key === "Escape") return closeModal(m);
    if (e.key !== "Tab") return;
    const f = focusables(m);
    if (!f.length) return;
    const [first, last] = [f[0], f[f.length - 1]];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }
  document.addEventListener("click", (e) => {
    const opener = e.target.closest("[data-uds-open]");
    if (opener) return openModal(opener.getAttribute("data-uds-open"));
    const closer = e.target.closest("[data-uds-close]");
    if (closer) return closeModal(closer.closest(".uds-modal"));
    if (e.target.classList.contains("uds-modal__scrim")) closeModal(e.target.closest(".uds-modal"));
  });

  /* ----- accordion: single/multiple disclosure -------------------------------- */
  document.addEventListener("click", (e) => {
    const trig = e.target.closest(".uds-accordion__trigger");
    if (!trig) return;
    const panel = document.getElementById(trig.getAttribute("aria-controls"));
    const open = trig.getAttribute("aria-expanded") === "true";
    const root = trig.closest(".uds-accordion");
    if (root && root.getAttribute("data-mode") !== "multiple") {
      root.querySelectorAll('.uds-accordion__trigger[aria-expanded="true"]').forEach((o) => {
        o.setAttribute("aria-expanded", "false");
        const p = document.getElementById(o.getAttribute("aria-controls"));
        if (p) p.hidden = true;
      });
    }
    trig.setAttribute("aria-expanded", String(!open));
    if (panel) panel.hidden = open;
  });

  /* ----- login → gateway → TwentyCRM -----------------------------------------
   * CONTRACT (the boundary this slice documents but does not stand up):
   *   POST <data-gateway>            body: { email, password }
   *   200 { ok:true, token, user }   → the gateway verified the credentials AND
   *                                     that the user is an AUTHORISED member in
   *                                     TwentyCRM (exists in the workspace, active,
   *                                     has access). Store token, go to redirect.
   *   401                            → invalid credentials
   *   403 { error }                  → authenticated but NOT an authorised
   *                                     TwentyCRM user (the brief's gate)
   * The real gateway/TwentyCRM wiring is a separate backend task. For the offline
   * proof, data-mock simulates the gate: demo@nopilot.co + an 8+ char password is
   * "authorised"; anything else returns the 403 path.
   */
  const form = document.querySelector("[data-uds-login]");
  if (form) form.addEventListener("submit", (e) => { e.preventDefault(); submitLogin(form); });

  async function submitLogin(form) {
    const btn = form.querySelector('button[type="submit"]');
    const errBox = form.querySelector("[data-uds-error]");
    const email = form.email.value.trim();
    const password = form.password.value;
    setError(form, errBox, "");

    if (!email || !password) return setError(form, errBox, "Enter your email and password.");
    btn.classList.add("is-loading");
    btn.disabled = true;

    try {
      const res = form.hasAttribute("data-mock")
        ? await mockGateway(email, password)
        : await fetch(form.getAttribute("data-gateway") || "/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
          });

      if (res.ok) {
        form.querySelector("[data-uds-success]")?.removeAttribute("hidden");
        form.setAttribute("data-state", "success");
        const { redirect } = await res.json().catch(() => ({}));
        // window.location.assign(redirect || "dashboard.html");  // wired in app
        return;
      }
      const { error } = await res.json().catch(() => ({}));
      setError(form, errBox,
        res.status === 403
          ? (error || "This account isn’t an authorised TwentyCRM user.")
          : (error || "Email or password not recognised."));
    } catch {
      setError(form, errBox, "Couldn’t reach the gateway. Try again.");
    } finally {
      btn.classList.remove("is-loading");
      btn.disabled = false;
    }
  }

  function setError(form, box, msg) {
    if (!box) return;
    box.textContent = msg;
    box.hidden = !msg;
    form.querySelectorAll(".uds-control").forEach((c) => c.setAttribute("aria-invalid", String(!!msg)));
  }

  // Offline stand-in for the gateway+TwentyCRM check. Replace with the real POST.
  function mockGateway(email, password) {
    const authorised = email.toLowerCase() === "demo@nopilot.co" && password.length >= 8;
    const body = authorised
      ? { ok: true, token: "demo.jwt.token", redirect: "dashboard.html" }
      : { error: "This account isn’t an authorised TwentyCRM user." };
    return Promise.resolve(new Response(JSON.stringify(body), {
      status: authorised ? 200 : 403,
      headers: { "Content-Type": "application/json" },
    }));
  }
})();
