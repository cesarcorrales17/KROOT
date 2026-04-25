import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { HttpHeaders } from '@angular/common/http';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private apiUrl = 'http://localhost:8000';
  private router = inject(Router);

  constructor(private http: HttpClient) {}

  // ==========================================
  // AUTENTICACIÓN PRINCIPAL
  // ==========================================

  // Inicio de sesión
  login(credentials: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/login`, credentials).pipe(
      tap((response) => {
        if (response.access_token) {
          localStorage.setItem('auth_token', response.access_token);
          localStorage.setItem('refresh_token', response.refresh_token);
        }
      }),
    );
  }

  // Registro de usuario 
  register(userData: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/register`, userData);
  }

  // NUEVO: Reenviar correo de verificación
  resendVerification(email: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/resend-verification`, { email });
  }

  // NUEVO: Login / Registro con Google OAuth
  loginWithGoogle(token: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/auth/google`, { token }).pipe(
      tap((response: any) => {
        if (response.access_token) {
          localStorage.setItem('auth_token', response.access_token);
          localStorage.setItem('refresh_token', response.refresh_token);
        }
      })
    );
  }

  // ==========================================
  // RECUPERACIÓN DE CONTRASEÑA
  // ==========================================

  // Paso 1: Solicitar el correo de recuperación
  forgotPassword(email: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/forgot-password`, { email });
  }

  // Paso 2: Enviar la nueva contraseña con el token
  resetPassword(token: string, new_password: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/reset-password`, {
      token,
      new_password,
    });
  }

  // ==========================================
  // GESTIÓN DE SESIÓN
  // ==========================================

  // Petición silenciosa para renovar tokens
  refreshToken(): Observable<any> {
    const refresh = localStorage.getItem('refresh_token');
    return this.http
      .post<any>(`${this.apiUrl}/refresh`, { refresh_token: refresh })
      .pipe(
        tap((response) => {
          if (response.access_token) {
            localStorage.setItem('auth_token', response.access_token);
            localStorage.setItem('refresh_token', response.refresh_token);
          }
        }),
      );
  }

  // Cierre de sesión
  logout(): void {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
    this.router.navigate(['/login']);
  }

  // ==========================================
  // WIZARD DE EMPRESA (ONBOARDING)
  // ==========================================

  // Función de apoyo para obtener el token
  private getHeaders() {
    const token = localStorage.getItem('auth_token');
    return { headers: new HttpHeaders({ Authorization: `Bearer ${token}` }) };
  }

  // Obtener progreso guardado
  getBusinessSetup(): Observable<any> {
    return this.http.get<any>(
      `${this.apiUrl}/business/setup`,
      this.getHeaders(),
    );
  }

  // Obtener los sectores y tipos de negocio desde el diccionario del backend
  getBusinessSectors(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/business/sectors`);
  }

  // Guardado automático (Upsert)
  updateBusinessSetup(data: any): Observable<any> {
    return this.http.patch<any>(
      `${this.apiUrl}/business/setup`,
      data,
      this.getHeaders(),
    );
  }

  // ==========================================
  // GESTIÓN DE PERFIL
  // ==========================================
  getBusinessProfile(): Observable<any> {
    return this.http.get<any>(
      `${this.apiUrl}/business/profile`,
      this.getHeaders(),
    );
  }

  updateBusinessProfile(data: any): Observable<any> {
    return this.http.put<any>(
      `${this.apiUrl}/business/profile`,
      data,
      this.getHeaders(),
    );
  }

  // ==========================================
  // DASHBOARD
  // ==========================================
  getDashboardSummary(): Observable<any> {
    return this.http.get<any>(
      `${this.apiUrl}/dashboard/summary`,
      this.getHeaders(),
    );
  }

  // ==========================================
  // VENTAS E INDICADORES
  // ==========================================
  createSale(saleData: any): Observable<any> {
    return this.http.post<any>(
      `${this.apiUrl}/sales/manual`,
      saleData,
      this.getHeaders(),
    );
  }

  getSalesSummary(periodType: string = 'monthly'): Observable<any> {
    return this.http.get<any>(
      `${this.apiUrl}/sales/summary?period_type=${periodType}`,
      this.getHeaders(),
    );
  }
  
  // Enviar Venta del Punto de Venta (POS)
  createPosSale(saleData: any): Observable<any> {
    return this.http.post<any>(
      `${this.apiUrl}/sales/pos`,
      saleData,
      this.getHeaders(),
    );
  }

  // ==========================================
  // GASTOS OPERATIVOS (ÉPICA 9)
  // ==========================================
  getExpenseCategories(): Observable<any> {
    return this.http.get<any>(
      `${this.apiUrl}/expenses/categories`,
      this.getHeaders(),
    );
  }

  createExpenseCategory(categoryData: any): Observable<any> {
    return this.http.post<any>(
      `${this.apiUrl}/expenses/categories`,
      categoryData,
      this.getHeaders(),
    );
  }

  createManualExpense(expenseData: any): Observable<any> {
    return this.http.post<any>(
      `${this.apiUrl}/expenses/manual`,
      expenseData,
      this.getHeaders(),
    );
  }

  getExpensesSummary(periodType: string = 'monthly'): Observable<any> {
    return this.http.get<any>(
      `${this.apiUrl}/expenses/summary?period_type=${periodType}`,
      this.getHeaders(),
    );
  }

  // ==========================================
  // CATÁLOGO E INVENTARIO (ÉPICA 10)
  // ==========================================

  getProducts(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/products`, this.getHeaders());
  }

  createProduct(productData: any): Observable<any> {
    return this.http.post<any>(
      `${this.apiUrl}/products`,
      productData,
      this.getHeaders(),
    );
  }

  updateProduct(productId: number, productData: any): Observable<any> {
    return this.http.put<any>(
      `${this.apiUrl}/products/${productId}`,
      productData,
      this.getHeaders(),
    );
  }

  deleteProduct(productId: number): Observable<any> {
    return this.http.delete<any>(
      `${this.apiUrl}/products/${productId}`,
      this.getHeaders(),
    );
  }

  toggleProductStatus(productId: number): Observable<any> {
    return this.http.patch<any>(
      `${this.apiUrl}/products/${productId}/status`,
      {},
      this.getHeaders(),
    );
  }
}