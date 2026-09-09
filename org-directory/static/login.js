(function () {
  var KEY = "hnwms_token";
  var demoPw = null;   // filled from /api/auth/accounts only when server is in demo mode
  var err = document.getElementById("gate-err");

  function fail(message) {
    err.textContent = message || "Could not sign in";
  }

  async function enter(username, pw) {
    err.textContent = "Signing in…";
    try {
      var password = pw || document.getElementById("gate-pw").value;
      if (!password) { fail("Password is required"); return; }
      var response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username, password: password })
      });
      var data = await response.json();
      if (!data.ok || !data.token) {
        fail(data.error || ("HTTP " + response.status));
        return;
      }
      window.__HNWMS_TOKEN = data.token;
      try {
        sessionStorage.setItem(KEY, data.token);
        localStorage.setItem(KEY, data.token);
      } catch (_) {}
      document.getElementById("gate").style.display = "none";
      document.body.classList.remove("guest");
      location.hash = "profile";
      if (window.hnwmsBoot) window.hnwmsBoot();
      else fail("App did not start. Refresh once.");
    } catch (error) {
      fail(String(error));
    }
  }

  document.querySelectorAll(".enter").forEach(function (button) {
    button.addEventListener("click", function () {
      enter(button.getAttribute("data-u"), demoPw);
    });
  });
  document.getElementById("gate-go").addEventListener("click", function () {
    var username = document.getElementById("gate-user").value;
    if (username) enter(username);
  });

  fetch("/api/auth/accounts")
    .then(function (response) { return response.json(); })
    .then(function (pack) {
      // If server is in demo mode it sends the password; otherwise the user types it
      if (pack.demo_password) {
        demoPw = pack.demo_password;
        var pwField = document.getElementById("gate-pw");
        if (pwField) pwField.style.display = "none";
      }
      var select = document.getElementById("gate-user");
      (pack.accounts || []).forEach(function (account) {
        var option = document.createElement("option");
        option.value = account.username;
        option.textContent = account.display_name + " — " + account.job_title;
        if (account.username === "fatimah.al.harbi") option.selected = true;
        select.appendChild(option);
      });
    })
    .catch(function () {});

  if (sessionStorage.getItem(KEY)) {
    document.getElementById("gate").style.display = "none";
    document.body.classList.remove("guest");
  }
})();
