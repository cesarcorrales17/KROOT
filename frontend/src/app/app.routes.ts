import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard'; // Asegúrate de que esta ruta coincida con tu estructura

// DEFINICIÓN DE RUTAS DEL FRONTEND
export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./features/auth/pages/login/login.component').then(m => m.LoginComponent)
  },
  {
    path: 'dashboard',
    canActivate: [authGuard], // PROTECCIÓN: El guardia evalúa antes de cargar el componente
    loadComponent: () => import('./features/dashboard/pages/dashboard/dashboard.component').then(m => m.DashboardComponent)
  },
  { 
    path: '', 
    redirectTo: 'login', 
    pathMatch: 'full' 
  }
];