
// Enhanced Chart Configuration
const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            labels: {
                usePointStyle: true,
                padding: 20,
                font: { 
                    size: 12, 
                    weight: 'bold',
                    family: 'Inter, sans-serif'
                }
            }
        },
        tooltip: {
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            titleColor: '#2d3748',
            bodyColor: '#4a5568',
            borderColor: '#e2e8f0',
            borderWidth: 1,
            cornerRadius: 8,
            padding: 12
        }
    },
    animation: {
        duration: 1000,
        easing: 'easeOutQuart'
    }
};

// Enhanced Pie Chart: Students per Grade
new Chart(document.getElementById('studentsPie').getContext('2d'), {
    type: 'doughnut',
    data: {
        labels: {{ pie_labels|safe }},
        datasets: [{
            data: {{ pie_data|safe }},
            backgroundColor: [
                'rgba(102, 126, 234, 0.8)',
                'rgba(72, 187, 120, 0.8)',
                'rgba(237, 137, 54, 0.8)',
                'rgba(245, 101, 101, 0.8)',
                'rgba(156, 39, 176, 0.8)',
                'rgba(0, 150, 136, 0.8)',
                'rgba(255, 193, 7, 0.8)',
                'rgba(121, 85, 72, 0.8)',
                'rgba(96, 125, 139, 0.8)'
            ],
            borderColor: [
                '#667eea',
                '#48bb78',
                '#ed8936',
                '#f56565',
                '#9c27b0',
                '#009688',
                '#ffc107',
                '#795548',
                '#607d8b'
            ],
            borderWidth: 3,
            hoverBorderWidth: 4,
            hoverOffset: 8
        }]
    },
    options: {
        ...chartOptions,
        cutout: '60%',
        plugins: {
            ...chartOptions.plugins,
            legend: { position: 'bottom' }
        }
    }
});

// Enhanced Line Chart: Average Marks per Grade
new Chart(document.getElementById('avgMarksLine').getContext('2d'), {
    type: 'line',
    data: {
        labels: {{ line_labels|safe }},
        datasets: [{
            label: 'Average Marks',
            data: {{ line_data|safe }},
            borderColor: '#48bb78',
            backgroundColor: 'rgba(72, 187, 120, 0.1)',
            borderWidth: 3,
            fill: true,
            tension: 0.4,
            pointBackgroundColor: '#48bb78',
            pointBorderColor: '#ffffff',
            pointBorderWidth: 2,
            pointRadius: 6,
            pointHoverRadius: 8,
            pointHoverBackgroundColor: '#38a169',
            pointHoverBorderColor: '#ffffff',
            pointHoverBorderWidth: 3
        }]
    },
    options: {
        ...chartOptions,
        scales: {
            y: { 
                beginAtZero: true,
                grid: { 
                    color: 'rgba(226, 232, 240, 0.5)',
                    drawBorder: false
                },
                ticks: { 
                    font: { weight: 'bold' },
                    color: '#4a5568'
                }
            },
            x: { 
                grid: { display: false },
                ticks: { 
                    font: { weight: 'bold' },
                    color: '#4a5568'
                }
            }
        }
    }
});

// Enhanced Interactions
document.addEventListener('DOMContentLoaded', function() {
    // Add staggered animations
    const animatedElements = document.querySelectorAll('.fade-in');
    animatedElements.forEach((element, index) => {
        element.style.animationDelay = `${index * 0.1}s`;
    });

    // Enhanced form interactions
    const formSelects = document.querySelectorAll('.form-select');
    formSelects.forEach(select => {
        select.addEventListener('focus', function() {
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.15)';
        });
        
        select.addEventListener('blur', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '';
        });
    });

    // Enhanced hover effects for cards
    const cards = document.querySelectorAll('.student-card, .chart-container');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.willChange = 'transform, box-shadow';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.willChange = 'auto';
        });
    });

    console.log('🎉 Enhanced Academic Dashboard loaded successfully!');
});

