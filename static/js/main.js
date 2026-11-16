/* Répét'Ivoire — scripts communs (JavaScript natif, sans dépendance). */
(function () {
  "use strict";

  // Ferme automatiquement le menu mobile après un clic sur un lien d'ancre.
  document.querySelectorAll(".site-navbar .nav-link[href^='#']").forEach(function (link) {
    link.addEventListener("click", function () {
      var menu = document.getElementById("mainNav");
      if (menu && menu.classList.contains("show") && window.bootstrap) {
        window.bootstrap.Collapse.getOrCreateInstance(menu).hide();
      }
    });
  });

  // Masque les messages flash de succès après 6 secondes.
  document.querySelectorAll(".alert-success[data-autodismiss]").forEach(function (el) {
    setTimeout(function () {
      if (window.bootstrap) window.bootstrap.Alert.getOrCreateInstance(el).close();
    }, 6000);
  });
})();
