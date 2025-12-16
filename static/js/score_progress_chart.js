document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementById("scoreProgressChart");
  if (!canvas || typeof Chart === "undefined") return;

  const labels = JSON.parse(
    document.getElementById("labels-data").textContent
  );
  const values = JSON.parse(
    document.getElementById("values-data").textContent
  );

  new Chart(canvas.getContext("2d"), {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "Score (%)",
        data: values,
        borderColor: "#3b82f6",
        backgroundColor: "rgba(59,130,246,0.15)",
        tension: 0.35,
        fill: true,
        pointRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          ticks: {
            callback: v => v + "%",
            color: "#9ca3af"
          }
        },
        x: {
          ticks: { color: "#9ca3af" }
        }
      },
      plugins: {
        legend: {
          labels: { color: "#e5e7eb" }
        }
      }
    }
  });
});
