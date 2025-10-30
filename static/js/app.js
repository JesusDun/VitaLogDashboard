var app = angular.module('myApp', []);

// --- Controlador para el Login ---
app.controller("loginCtrl", function ($scope, $http) {
    $("#frmLogin").on("submit", function (event) {
        event.preventDefault();
        $.post("/iniciarSesion", $(this).serialize())
            .done(function () { 
                window.location.href = '/dashboard'; 
            })
            .fail(function (response) { alert(response.responseJSON.error || "Error al iniciar sesión."); });
    });
});

// --- Controlador para el Registro ---
app.controller("registroCtrl", function ($scope, $http) {
    $("#frmRegistro").on("submit", function(event) {
        event.preventDefault();
        $.post("/registrarUsuario", $(this).serialize())
            .done(function(response) {
                alert(response.status);
                window.location.href = '/';
            })
            .fail(function(response) {
                alert(response.responseJSON.error || "Error en el registro.");
            });
    });
});


app.controller("dashboardCtrl", function ($scope, $http) {
    let heatmapInstance = null;
    let barrasFitnessInstance = null;

    // --- FUNCIONES DE INICIALIZACIÓN Y CARGA ---

    function inicializarTodo() {
        try {
            document.getElementById('fitnessDate').valueAsDate = new Date();
        } catch(e) { console.warn("Input de fecha no encontrado. ¿Estás en el dashboard?"); }
        
        cargarHabitosCheckin();
        cargarHeatmap();
        cargarStatsFitness();
    }

    function cargarHabitosCheckin() {
        $.get("/api/habitos", function (habitos) {
            const $lista = $("#listaHabitosCheckin").empty();
            if (habitos.length === 0) {
                $lista.append('<p class="text-muted small">Aún no has añadido hábitos. ¡Crea uno para empezar!</p>');
            }
            habitos.forEach(habito => {
                const checked = habito.completadoHoy ? 'checked' : '';
                $lista.append(`
                    <label class="list-group-item habito-item">
                        <div>
                            <i class="${habito.icono || 'bi-check-lg'} me-2"></i>
                            ${habito.nombre}
                        </div>
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" role="switch" data-id="${habito.idHabito}" ${checked}>
                        </div>
                    </label>
                `);
            });
        }).fail(function(err) {
            $("#listaHabitosCheckin").html('<p class="text-danger">Error al cargar hábitos.</p>');
        });
    }

    function cargarHeatmap() {
        $.get("/api/analytics/heatmap", function (data) {
            dibujarGraficoHeatmap(data);
        }).fail(function(err) {
            $("#graficoHeatmap").html('<p class="text-danger">Error al cargar heatmap.</p>');
        });
    }

    function cargarStatsFitness() {
        $.get("/api/analytics/fitness_stats", function (data) {
            $("#totalSesiones").text(data.resumen.total_sesiones);
            $("#totalMinutos").text(data.resumen.total_minutos);
            $("#totalCalorias").text(data.resumen.total_calorias);
            
            dibujarGraficoBarras(data.grafico_barras.labels, data.grafico_barras.series);
            
        }).fail(function(err) {
            console.error("Error cargando stats de fitness:", err);
        });
    }

    // --- FUNCIONES PARA DIBUJAR GRÁFICOS (APEXCHARTS) ---

    function dibujarGraficoHeatmap(seriesData) {
        if (heatmapInstance) {
            heatmapInstance.destroy();
        }
        const options = {
            series: [{ name: 'Hábitos Completados', data: seriesData }],
            chart: {
                type: 'heatmap',
                height: 350,
                toolbar: { show: false }
            },
            plotOptions: {
                heatmap: {
                    shadeIntensity: 0.5,
                    colorScale: {
                        ranges: [
                            { from: 0, to: 0, name: '0', color: '#ebedf0' },
                            { from: 1, to: 2, name: '1-2', color: '#9be9a8' },
                            { from: 3, to: 4, name: '3-4', color: '#40c463' },
                            { from: 5, to: 99, name: '5+', color: '#216e39' }
                        ]
                    }
                }
            },
            dataLabels: { enabled: false },
            title: { text: 'Constancia de Hábitos (Último Año)', style: { fontSize: '14px' } },
            tooltip: {
                y: { formatter: (value) => `${value} hábitos` }
            }
        };
        heatmapInstance = new ApexCharts(document.querySelector("#graficoHeatmap"), options);
        heatmapInstance.render();
    }

    function dibujarGraficoBarras(labels, series) {
        if (barrasFitnessInstance) {
            barrasFitnessInstance.destroy();
        }
        const options = {
            series: [{ name: 'Calorías Quemadas', data: series }],
            chart: {
                type: 'bar',
                height: 300,
                toolbar: { show: false }
            },
            xaxis: {
                categories: labels,
                labels: {
                    formatter: function(val) {
                        return new Date(val + 'T00:00:00Z').toLocaleDateString('es-ES', { month: 'short', day: 'numeric', timeZone: 'UTC' });
                    }
                }
            },
            yaxis: { title: { text: 'Calorías (kcal)' } },
            dataLabels: { enabled: false },
            colors: ['#0d6efd']
        };
        barrasFitnessInstance = new ApexCharts(document.querySelector("#graficoBarrasFitness"), options);
        barrasFitnessInstance.render();
    }


    // --- MANEJADORES DE EVENTOS ---

    // Registrar/Des-registrar un hábito (Check-in)
    $(document).on("change", "#frmCheckin .form-check-input", function () {
        const idHabito = $(this).data("id");
        $.post("/api/habito/registrar", { idHabito: idHabito })
            .done(function() {
                cargarHeatmap(); 
            })
            .fail(function(err) {
                alert(err.responseJSON.error || "Error al registrar hábito.");
                $(this).prop('checked', !$(this).prop('checked'));
            });
    });

    // Añadir nuevo ejercicio
    $("#frmFitness").on("submit", function (event) {
        event.preventDefault();
        $.post("/api/fitness", $(this).serialize())
            .done(function () {
                $("#frmFitness")[0].reset();
                document.getElementById('fitnessDate').valueAsDate = new Date();
                cargarStatsFitness();
            })
            .fail(function (err) {
                alert(err.responseJSON.error || "Error al añadir ejercicio.");
            });
    });

    // Botón de Cerrar Sesión
    $(document).on("click", "#btnCerrarSesion", function() {
        if (confirm("¿Estás seguro de que quieres cerrar sesión?")) {
            $.post("/cerrarSesion").done(function() {
                window.location.href = '/'; // Redirige al login
            });
        }
    });

    // --- INICIALIZACIÓN (Solo si estamos en el dashboard) ---
    if(window.location.pathname === '/dashboard') {
        inicializarTodo();
    }
});
