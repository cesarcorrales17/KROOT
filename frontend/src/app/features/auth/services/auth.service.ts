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

  // AUTENTICACIÓN PRINCIPAL

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

  // RECUPERACIÓN DE CONTRASEÑA

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

  // GESTIÓN DE SESIÓN

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

  // WIZARD DE EMPRESA (ONBOARDING)

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

  // Guardado automático (Upsert)
  updateBusinessSetup(data: any): Observable<any> {
    return this.http.patch<any>(
      `${this.apiUrl}/business/setup`,
      data,
      this.getHeaders(),
    );
  }
}
