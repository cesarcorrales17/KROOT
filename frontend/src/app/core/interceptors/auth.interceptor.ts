import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../../features/auth/services/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  let token = localStorage.getItem('auth_token');
  let clonedRequest = req;

  if (token) {
    clonedRequest = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` }
    });
  }

  return next(clonedRequest).pipe(
    catchError((error: HttpErrorResponse) => {
      // Validamos que sea 401 y que no estemos intentando hacer login o refresh (para evitar bucles infinitos)
      if (error.status === 401 && !req.url.includes('/login') && !req.url.includes('/refresh')) {
        
        // Pausamos y pedimos un nuevo token
        return authService.refreshToken().pipe(
          switchMap((response) => {
            // Si tiene éxito, actualizamos la cabecera con el nuevo token y reintentamos la petición original
            const newToken = response.access_token;
            const retryRequest = req.clone({
              setHeaders: { Authorization: `Bearer ${newToken}` }
            });
            return next(retryRequest);
          }),
          catchError((refreshError) => {
            // Si la llave maestra también expiró, ahora sí expulsamos al usuario
            authService.logout();
            return throwError(() => refreshError);
          })
        );
      }
      
      return throwError(() => error);
    })
  );
};