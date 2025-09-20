/**
 * Expense Stats Page
 * 
 * Handles Chart.js initialization for expense statistics visualization.
 * This replaces the inline JavaScript in the expenses/stats.html template.
 */

document.addEventListener('DOMContentLoaded', () => {
  const ctx = document.getElementById('spendingChart').getContext('2d');

  // Get chart data from JSON script tag
  const chartDataElement = document.getElementById('chart-data');
  const chartDataJson = JSON.parse(chartDataElement.textContent);
  const chartLabels = chartDataJson.labels;
  const chartDataValues = chartDataJson.data;

  const chartData = {
    labels: chartLabels,
    datasets: [
      {
        label: 'Daily Spending',
        data: chartDataValues,
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1,
        tension: 0.3,
        fill: true,
      },
    ],
  };

  new Chart(ctx, {
    type: 'line',
    data: chartData,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          callbacks: {
            label(context) {
              return `$${context.parsed.y.toFixed(2)}`;
            },
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback(value) {
              return `$${value}`;
            },
          },
        },
        x: {
          ticks: {
            maxRotation: 45,
            minRotation: 45,
          },
        },
      },
    },
  });
});
