window.addEventListener("DOMContentLoaded", () => {
  if (window.gsap) {
    gsap.from(".tibo-hero-copy > *", { y: 18, opacity: 0, duration: 0.7, stagger: 0.08, ease: "power2.out" });
    gsap.from(".tibo-hero-stage", { y: 24, opacity: 0, duration: 0.8, delay: 0.12, ease: "power2.out" });
  }
  const chart = document.getElementById("tiboRevenueChart");
  if (chart && window.Chart) {
    new Chart(chart, {
      type: "line",
      data: {
        labels: ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin"],
        datasets: [{ label: "Revenus", data: [1200, 1800, 2400, 3200, 4700, 6200], borderColor: "#69e7ff", backgroundColor: "rgba(47,124,255,.18)", tension: .42, fill: true }]
      },
      options: { plugins: { legend: { labels: { color: "#e2e8f0" } } }, scales: { x: { ticks: { color: "#94a3b8" } }, y: { ticks: { color: "#94a3b8" } } } }
    });
  }
});

