import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface FinancialData {
  total_income: number;
  total_expenses: number;
  cash_flow: number;
  chart_labels: string[];
  chart_incomes: number[];
  chart_expenses: number[];
}

export interface OperationalData {
  units_sold_today: number;
  low_stock_alerts: number;
  active_branches: number;
  top_products: { name: string; sold: number; revenue: number }[];
}

@Injectable({
  providedIn: 'root',
})
export class DashboardService {
  private http = inject(HttpClient);

  // URL directa a tu backend de FastAPI (ajusta el 8000 si usas otro puerto)
  private apiUrl = 'http://localhost:8000/api/dashboard';

  getFinancialMetrics(period: string): Observable<FinancialData> {
    return this.http.get<FinancialData>(
      `${this.apiUrl}/financial?period=${period}`,
    );
  }

  getOperationalMetrics(period: string): Observable<OperationalData> {
    return this.http.get<OperationalData>(
      `${this.apiUrl}/operational?period=${period}`,
    );
  }
}
