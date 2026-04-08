import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  ReactiveFormsModule,
  FormBuilder,
  FormGroup,
  Validators,
} from '@angular/forms';
import { RouterLink } from '@angular/router';

// IMPORTACIONES DE MATERIAL DESIGN
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { trigger, transition, style, animate } from '@angular/animations';

// RUTA CORREGIDA HACIA TU SERVICIO
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './forgot-password.component.html',
  styleUrl: './forgot-password.component.scss',
  animations: [
    trigger('fadeInUp', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(24px)' }),
        animate(
          '0.55s cubic-bezier(0.16, 1, 0.3, 1)',
          style({ opacity: 1, transform: 'translateY(0)' }),
        ),
      ]),
    ]),
  ],
})
export class ForgotPasswordComponent {
  forgotForm: FormGroup;
  isLoading = false;

  successMessage = '';
  errorMessage = '';

  private fb = inject(FormBuilder);
  private authService = inject(AuthService);

  constructor() {
    this.forgotForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
    });
  }

  onSubmit(): void {
    if (this.forgotForm.valid) {
      this.isLoading = true;
      this.errorMessage = '';
      this.successMessage = '';

      const email = this.forgotForm.get('email')?.value;

      this.authService.forgotPassword(email).subscribe({
        next: (response: any) => {
          // Añadido : any para el modo estricto
          this.isLoading = false;
          this.successMessage =
            response.message ||
            'Si el correo está registrado en Kroot, recibirás un enlace de recuperación en los próximos minutos.';
          this.forgotForm.reset();
        },
        error: (err: any) => {
          // Añadido : any para el modo estricto
          this.isLoading = false;
          if (err.status === 429) {
            this.errorMessage =
              'Has realizado demasiadas solicitudes. Por favor, espera unos minutos.';
          } else {
            this.errorMessage =
              'Ocurrió un error al procesar la solicitud. Inténtalo más tarde.';
          }
        },
      });
    } else {
      this.forgotForm.markAllAsTouched();
    }
  }
}
