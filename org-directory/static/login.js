(function () {
  var KEY = "hnwms_token";
  var PW = "Demo@2026";
  var err = document.getElementById("gate-err");

  function fail(message) {
    err.textContent = message || "Could not sign in";
  }

  async function enter(username) {
    err.textContent = "Signing in…";
    try {
      var response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username, password: PW })
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
      enter(button.getAttribute("data-u"));
    });
  });
  document.getElementById("gate-go").addEventListener("click", function () {
    var username = document.getElementById("gate-user").value;
    if (username) enter(username);
  });
  fetch("/api/auth/accounts")
    .then(function (response) { return response.json(); })
    .then(function (pack) {
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
