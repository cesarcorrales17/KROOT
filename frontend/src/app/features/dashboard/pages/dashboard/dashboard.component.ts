import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

// MATERIAL DESIGN & GRÁFICOS
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { NgApexchartsModule } from 'ng-apexcharts';

// SERVICIO
import { AuthService } from '../../../../features/auth/services/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatIconModule,
    MatProgressSpinnerModule,
    MatButtonModule,
    NgApexchartsModule, // <-- IMPORTANTE AÑADIRLO AQUÍ
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  isLoading = true;
  hasData = false;
  currency = 'COP';

  // KPIs inicializados en cero
  kpis = {
    total_income: 0,
    total_expenses: 0,
    cash_flow: 0,
  };

  // Variable que guardará la configuración del gráfico
  public chartOptions: any;

  private authService = inject(AuthService);

  ngOnInit(): void {
    this.loadDashboardSummary();
  }

  loadDashboardSummary(): void {
    this.authService.getDashboardSummary().subscribe({
      next: (data) => {
        this.hasData = data.has_data;
        this.currency = data.currency;
        this.kpis = data.kpis;

        // Si el usuario ya tiene registros, dibujamos la gráfica
        if (this.hasData) {
          this.initChart(data.charts);
        }

        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error al cargar el dashboard', err);
        this.isLoading = false;
      },
    });
  }

  // Configuración de ApexCharts
  initChart(chartData: any): void {
    this.chartOptions = {
      series: [
        {
          name: 'Ingresos',
          data: chartData.income_data,
          color: '#10b981', // Verde esmeralda
        },
        {
          name: 'Gastos',
          data: chartData.expense_data,
          color: '#ef4444', // Rojo
        },
      ],
      chart: {
        type: 'bar',
        height: 350,
        fontFamily: 'Inter, sans-serif',
        toolbar: { show: false },
      },
      plotOptions: {
        bar: {
          horizontal: false,
          columnWidth: '55%',
          borderRadius: 4,
        },
      },
      dataLabels: { enabled: false },
      stroke: { show: true, width: 2, colors: ['transparent'] },
      xaxis: { categories: chartData.labels },
      yaxis: {
        title: { text: `$ (${this.currency})` },
      },
      fill: { opacity: 1 },
      tooltip: {
        y: {
          formatter: (val: number) => {
            return '$' + val.toLocaleString();
          },
        },
      },
    };
  }

  logout(): void {
    this.authService.logout();
  }
}
