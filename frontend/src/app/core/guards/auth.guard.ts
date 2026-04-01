import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

// GUARDIA DE AUTENTICACIÓN
export const authGuard: CanActivateFn = (route, state) => {
  const router = inject(Router);
  
  // VERIFICACIÓN DEL TOKEN EN LOCALSTORAGE
  const token = localStorage.getItem('auth_token');

  if (token) {
    return true; // Tiene el token, permite el acceso a la ruta
  } else {
    router.navigate(['/login']); // No tiene token, redirige a la pantalla de login
    return false;
  }
};