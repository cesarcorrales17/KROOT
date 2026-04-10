import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { NgApexchartsModule } from 'ng-apexcharts';

import { AuthService } from '../../../../features/auth/services/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatIconModule,
    MatButtonModule,
    MatSelectModule,
    MatFormFieldModule,
    MatProgressSpinnerModule,
    NgApexchartsModule,
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  isLoading = true;
  currency = 'COP';
  selectedPeriod = 'this_month';

  kpis = { total_income: 0, total_expenses: 0, cash_flow: 0 };
  public areaChartOptions: any;
  public donutChartOptions: any;

  private authService = inject(AuthService);

  ngOnInit(): void {
    this.loadDashboardSummary();
  }

  loadDashboardSummary(): void {
    this.authService.getDashboardSummary().subscribe({
      next: (data) => {
        this.currency = data.currency;
        this.kpis = data.kpis;
        this.buildCharts(data.charts);
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error al cargar el dashboard', err);
        this.isLoading = false;
      },
    });
  }

  buildCharts(chartData: any): void {
    // GRÁFICO 1: ÁREA (Tendencia de Ingresos vs Gastos)
    this.areaChartOptions = {
      series: [
        {
          name: 'Ingresos',
          data: chartData.income_data || [0, 0, 0, 0, 0, 0, 0],
        },
        {
          name: 'Gastos',
          data: chartData.expense_data || [0, 0, 0, 0, 0, 0, 0],
        },
      ],
      chart: {
        type: 'area',
        height: 350,
        fontFamily: 'Inter, sans-serif',
        toolbar: { show: false },
      },
      colors: ['#10b981', '#ef4444'], // Verde y Rojo
      dataLabels: { enabled: false },
      stroke: { curve: 'smooth', width: 2 },
      fill: {
        type: 'gradient',
        gradient: {
          shadeIntensity: 1,
          opacityFrom: 0.4,
          opacityTo: 0.05,
          stops: [0, 90, 100],
        },
      },
      xaxis: {
        categories: chartData.labels || [
          'Lun',
          'Mar',
          'Mie',
          'Jue',
          'Vie',
          'Sab',
          'Dom',
        ],
        axisBorder: { show: false },
      },
      yaxis: {
        labels: { formatter: (val: number) => '$' + val.toLocaleString() },
      },
      grid: { strokeDashArray: 4, borderColor: '#e2e8f0' },
    };

    // GRÁFICO 2: DONA (Categorías) - En 0 por ahora
    this.donutChartOptions = {
      series: [0, 0, 0], // Vacío intencionalmente
      labels: ['Categoría A', 'Categoría B', 'Categoría C'],
      chart: { type: 'donut', height: 300, fontFamily: 'Inter, sans-serif' },
      colors: ['#e2e8f0', '#cbd5e1', '#94a3b8'], // Colores grises hasta que haya datos reales
      plotOptions: {
        pie: {
          donut: {
            labels: {
              show: true,
              total: { show: true, label: 'Sin datos', color: '#94a3b8' },
            },
          },
        },
      },
      dataLabels: { enabled: false },
      legend: { position: 'bottom' },
    };
  }

  logout(): void {
    this.authService.logout();
  }
}
