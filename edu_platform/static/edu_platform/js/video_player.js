/**
 * EduCam Pro — Lecteur vidéo sécurisé
 * Désactive les contrôles de téléchargement et protège le contenu.
 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const videos = document.querySelectorAll('video');

    videos.forEach(function (video) {
      // Désactiver clic droit
      video.addEventListener('contextmenu', function (e) {
        e.preventDefault();
        return false;
      });

      // Désactiver les raccourcis clavier de téléchargement
      video.addEventListener('keydown', function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
          e.preventDefault();
        }
      });

      // Enregistrer la progression de lecture
      video.addEventListener('timeupdate', function () {
        if (video.duration) {
          const progress = Math.round((video.currentTime / video.duration) * 100);
          sessionStorage.setItem('edu_video_progress_' + getVideoId(), progress);
        }
      });
    });

    function getVideoId() {
      const match = window.location.pathname.match(/\/videos\/(\d+)\//);
      return match ? match[1] : '0';
    }
  });
})();
