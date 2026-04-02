import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router,RouterLink } from '@angular/router'; // <-- IMPORTACIÓN DEL ENRUTADOR
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { trigger, transition, style, animate } from '@angular/animations';

// IMPORTACIÓN DE SERVICIOS
import { AuthService } from '../../services/auth.service';

// CONFIGURACIÓN DEL COMPONENTE Y ANIMACIONES
@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatButtonModule,
    MatCheckboxModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
  animations: [
    trigger('fadeInUp', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(20px)' }),
        animate('0.6s cubic-bezier(0.16, 1, 0.3, 1)', style({ opacity: 1, transform: 'translateY(0)' }))
      ])
    ])
  ]
})
export class LoginComponent {
  // ESTADO DE LA INTERFAZ
  loginForm: FormGroup;
  hidePassword = true;
  logoError = false;
  isLoading = false;
  errorMessage = ''; 

  // INYECCIÓN DE DEPENDENCIAS
  private authService = inject(AuthService);
  private router = inject(Router); // <-- INYECCIÓN DEL ENRUTADOR

  constructor(private fb: FormBuilder) {
    // INICIALIZACIÓN DEL FORMULARIO
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(8)]],
      rememberMe: [false]
    });
  }

  // MANEJO DE IMAGEN FALLIDA
  handleLogoError() {
    this.logoError = true;
  }

  // PROCESAMIENTO DEL FORMULARIO
  onSubmit() {
    if (this.loginForm.valid) {
      this.isLoading = true;
      this.errorMessage = ''; 
      
      const loginData = this.loginForm.value;

      // COMUNICACIÓN CON EL BACKEND
      this.authService.login(loginData).subscribe({
        next: (response) => {
          this.isLoading = false;
          
          // REDIRECCIÓN AL DASHBOARD TRAS ÉXITO
          this.router.navigate(['/dashboard']);
        },
        error: (err) => {
          this.isLoading = false;
          
          // MANEJO DE CÓDIGOS DE ESTADO HTTP
          if (err.status === 401) {
            // Error 401: Contraseña incorrecta (Muestra los intentos restantes que envía FastAPI)
            this.errorMessage = err.error.detail || 'Correo o contraseña incorrectos.';
          } else if (err.status === 403) {
            // Error 403: Cuenta bloqueada por seguridad (15 minutos)
            this.errorMessage = err.error.detail || 'Cuenta bloqueada temporalmente.';
          } else {
            // Error genérico de servidor apagado o sin internet
            this.errorMessage = 'Error de conexión con el servidor.';
          }
        }
      });
    } else {
      this.loginForm.markAllAsTouched();
    }
  }
  // NAVEGACIÓN HACIA EL REGISTRO
  goToRegister() {
    this.router.navigate(['/register']);
  }
}