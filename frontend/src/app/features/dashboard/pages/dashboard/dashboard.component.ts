import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../../auth/services/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div style="padding: 2rem; font-family: sans-serif;">
      <h1>Panel de Control (Dashboard)</h1>
      
      <button (click)="logout()" style="padding: 10px; background: red; color: white; border: none; cursor: pointer;">
        Cerrar Sesión
      </button>

      <div style="margin-top: 2rem; padding: 1rem; background: #f5f5f5; border-radius: 8px;">
        <h3>Respuesta del Servidor Protegido:</h3>
        
        <p *ngIf="isLoading">Cargando datos seguros...</p>
        
        <pre *ngIf="serverData">{{ serverData | json }}</pre>
        
        <p *ngIf="error" style="color: red;">{{ error }}</p>
      </div>
    </div>
  `
})
export class DashboardComponent implements OnInit {
  // INYECCIÓN DE DEPENDENCIAS
  private http = inject(HttpClient);
  private authService = inject(AuthService);

  // ESTADO DE LA VISTA
  serverData: any = null;
  isLoading = true;
  error = '';

  ngOnInit() {
    this.fetchProtectedData();
  }

  // PETICIÓN A RUTA PROTEGIDA (El Interceptor actuará aquí automáticamente)
  fetchProtectedData() {
    this.http.get('http://localhost:8000/api/dashboard/stats').subscribe({
      next: (res) => {
        this.serverData = res;
        this.isLoading = false;
      },
      error: (err) => {
        this.error = 'No tienes permiso para ver estos datos (Token inválido o ausente).';
        this.isLoading = false;
      }
    });
  }

  // FUNCIÓN DE CIERRE DE SESIÓN
  logout() {
    this.authService.logout();
  }
}