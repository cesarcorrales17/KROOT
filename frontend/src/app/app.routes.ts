import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/pages/login/login.component';

export const routes: Routes = [
  {
    path: 'login',
    component: LoginComponent,
    title: 'Iniciar Sesión | Kroot' 
  },
  {
    path: '',
    redirectTo: 'login',
    pathMatch: 'full'
  }
];