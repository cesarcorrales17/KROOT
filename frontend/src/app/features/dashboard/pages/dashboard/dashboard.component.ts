import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';

import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { NgApexchartsModule } from 'ng-apexcharts';

import { AuthService } from '../../../../features/auth/services/auth.service';
import { DashboardService } from './dashboard.service'; // <--- Ruta corregida

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
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
  isMobileMenuOpen = false;

  kpis = { total_income: 0, total_expenses: 0, cash_flow: 0 };
  operationalKpis = {
    units_sold_today: 0,
    low_stock_alerts: 0,
    active_branches: 1,
  };
  topProducts: any[] = [];

  public areaChartOptions: any;
  public donutChartOptions: any;

  private authService = inject(AuthService);
  private dashboardService = inject(DashboardService);

  ngOnInit(): void {
    this.loadDashboardData();
  }

  toggleMobileMenu(): void {
    this.isMobileMenuOpen = !this.isMobileMenuOpen;
  }

  onPeriodChange(period: string): void {
    this.selectedPeriod = period;
    this.loadDashboardData();
  }

  loadDashboardData(): void {
    this.isLoading = true;

    forkJoin({
      financial: this.dashboardService.getFinancialMetrics(this.selectedPeriod),
      operational: this.dashboardService.getOperationalMetrics(
        this.selectedPeriod,
      ),
    }).subscribe({
      next: (result) => {
        this.kpis = {
          total_income: result.financial.total_income || 0,
          total_expenses: result.financial.total_expenses || 0,
          cash_flow: result.financial.cash_flow || 0,
        };

        this.operationalKpis = {
          units_sold_today: result.operational.units_sold_today || 0,
          low_stock_alerts: result.operational.low_stock_alerts || 0,
          active_branches: result.operational.active_branches || 1,
        };
        this.topProducts = result.operational.top_products || [];

        this.initCharts(result.financial);
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error al cargar datos del dashboard', err);
        // Si el backend no está listo, evitamos que la pantalla se rompa
        this.initCharts({
          chart_labels: [],
          chart_incomes: [],
          chart_expenses: [],
        });
        this.isLoading = false;
      },
    });
  }

  initCharts(financialData: any): void {
    this.areaChartOptions = {
      series: [
        { name: 'Ingresos', data: financialData.chart_incomes || [] },
        { name: 'Egresos', data: financialData.chart_expenses || [] },
      ],
      chart: {
        type: 'area',
        height: 320,
        width: '100%',
        toolbar: { show: false },
        fontFamily: 'Inter, sans-serif',
      },
      colors: ['#10b981', '#ef4444'],
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
        categories: financialData.chart_labels || [],
        axisBorder: { show: false },
      },
      yaxis: {
        labels: { formatter: (val: number) => '$' + val.toLocaleString() },
      },
      grid: { strokeDashArray: 4, borderColor: '#e2e8f0' },
    };

    const donutSeries =
      this.topProducts.length > 0 ? this.topProducts.map((p) => p.sold) : [1];
    const donutLabels =
      this.topProducts.length > 0
        ? this.topProducts.map((p) => p.name)
        : ['Sin datos'];

    this.donutChartOptions = {
      series: donutSeries,
      labels: donutLabels,
      chart: {
        type: 'donut',
        height: 280,
        width: '100%',
        fontFamily: 'Inter, sans-serif',
      },
      colors:
        this.topProducts.length > 0
          ? ['#4f46e5', '#0ea5e9', '#10b981', '#f59e0b', '#8b5cf6']
          : ['#e2e8f0'],
      plotOptions: {
        pie: {
          donut: {
            size: '75%',
            labels: { show: true, name: { show: true }, value: { show: true } },
          },
        },
      },
      dataLabels: { enabled: false },
      legend: { position: 'bottom' },
      stroke: { show: false },
      tooltip: { enabled: this.topProducts.length > 0 },
    };
  }

  logout(): void {
    this.authService.logout();
  }
}
