import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  ReactiveFormsModule,
  FormBuilder,
  FormGroup,
  Validators,
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router'; 
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { trigger, transition, style, animate } from '@angular/animations';

import { AuthService } from '../../services/auth.service';

declare var google: any;

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink, MatFormFieldModule,
    MatInputModule, MatIconModule, MatButtonModule, MatCheckboxModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
  animations: [
    trigger('fadeInUp', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(20px)' }),
        animate('0.6s cubic-bezier(0.16, 1, 0.3, 1)', style({ opacity: 1, transform: 'translateY(0)' })),
      ]),
    ]),
  ],
})
export class LoginComponent implements OnInit {
  loginForm: FormGroup;
  hidePassword = true;
  logoError = false;
  isLoading = false;
  errorMessage = '';

  private authService = inject(AuthService);
  private router = inject(Router);

  constructor(private fb: FormBuilder) {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(8)]],
      rememberMe: [false],
    });
  }

  ngOnInit(): void {
    if (typeof google !== 'undefined') {
      google.accounts.id.initialize({
        // RECUERDA PONER TU CLIENT ID REAL AQUÍ PARA QUE FUNCIONE LA VENTANA
        client_id: "TU_CLIENT_ID_DE_GOOGLE.apps.googleusercontent.com", 
        callback: this.handleGoogleResponse.bind(this)
      });

      // Renderiza el botón oficial pero quedará invisible gracias al HTML
      google.accounts.id.renderButton(
        document.getElementById("google-btn-container"),
        { theme: "outline", size: "large", type: "standard", width: 400 } 
      );
    }
  }

  handleLogoError() {
    this.logoError = true;
  }

  onSubmit() {
    if (this.loginForm.valid) {
      this.isLoading = true;
      this.errorMessage = '';
      const loginData = this.loginForm.value;

      this.authService.login(loginData).subscribe({
        next: (response) => {
          this.authService.getBusinessSetup().subscribe({
            next: (businessData) => {
              this.isLoading = false;
              if (businessData && businessData.onboarding_completed) {
                this.router.navigate(['/dashboard']);
              } else {
                this.router.navigate(['/company-setup']);
              }
            },
            error: (err) => {
              this.isLoading = false;
              this.router.navigate(['/company-setup']);
            },
          });
        },
        error: (err) => {
          this.isLoading = false;
          if (err.status === 401) {
            this.errorMessage = err.error?.detail || 'Correo o contraseña incorrectos.';
          } else if (err.status === 403) {
            this.errorMessage = err.error?.detail || 'Cuenta bloqueada temporalmente.';
          } else {
            this.errorMessage = 'Error de conexión con el servidor.';
          }
        },
      });
    } else {
      this.loginForm.markAllAsTouched();
    }
  }

  handleGoogleResponse(response: any) {
    this.isLoading = true;
    this.errorMessage = '';
    const googleToken = response.credential;
    
    this.authService.loginWithGoogle(googleToken).subscribe({
      next: (res) => {
        this.authService.getBusinessSetup().subscribe({
          next: (businessData) => {
            this.isLoading = false;
            if (businessData && businessData.onboarding_completed) {
              this.router.navigate(['/dashboard']);
            } else {
              this.router.navigate(['/company-setup']);
            }
          },
          error: (err) => {
            this.isLoading = false;
            this.router.navigate(['/company-setup']);
          },
        });
      },
      error: (err) => {
        this.isLoading = false;
        console.error('Error con Google OAuth', err);
        this.errorMessage = 'Hubo un error al iniciar sesión con Google.';
      }
    });
  }
}