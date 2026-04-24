import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () =>
      import('./features/auth/pages/login/login.component').then(
        (m) => m.LoginComponent,
      ),
  },
  {
    path: 'register',
    loadComponent: () =>
      import('./features/auth/pages/register/register.component').then(
        (m) => m.RegisterComponent,
      ),
  },
  {
    path: 'company-setup',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/auth/pages/company-setup/company-setup.component').then(
        (m) => m.CompanySetupComponent,
      ),
  },
  // ----------------------------------------
  {
    path: 'dashboard',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/dashboard/pages/dashboard/dashboard.component').then(
        (m) => m.DashboardComponent,
      ),
  },
  {
    path: '',
    redirectTo: 'login',
    pathMatch: 'full',
  },
  {
    path: 'forgot-password',
    loadComponent: () =>
      import('./features/auth/pages/forgot-password/forgot-password.component').then(
        (m) => m.ForgotPasswordComponent,
      ),
  },
  {
    path: 'reset-password',
    loadComponent: () =>
      import('./features/auth/pages/reset-password/reset-password.component').then(
        (m) => m.ResetPasswordComponent,
      ),
  },
  {
    path: 'profile',
    canActivate: [authGuard], // Seguridad añadida
    loadComponent: () =>
      import('./features/dashboard/pages/profile/profile.component').then(
        (m) => m.ProfileComponent,
      ),
  },
  {
    path: 'sales',
    canActivate: [authGuard], // Seguridad añadida
    loadComponent: () =>
      import('./features/dashboard/pages/sales/sales.component').then(
        (m) => m.SalesComponent,
      ),
  },
  {
    path: 'expenses',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/dashboard/pages/expenses/expenses.component').then(
        (m) => m.ExpensesComponent,
      ),
  },
  {
    path: 'inventory',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/dashboard/pages/inventory/inventory.component').then(
        (m) => m.InventoryComponent,
      ),
  },
];
