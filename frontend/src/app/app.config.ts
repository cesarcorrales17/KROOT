import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { routes } from './app.routes';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
// Asegúrate de importar withInterceptors
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http'; 
import { authInterceptor } from './core/interceptors/auth.interceptor'; // <-- Tu nuevo interceptor

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideAnimationsAsync(),
    // ACTIVACIÓN DEL INTERCEPTOR GLOBAL
    provideHttpClient(
      withFetch(),
      withInterceptors([authInterceptor]) 
    )
  ]
};