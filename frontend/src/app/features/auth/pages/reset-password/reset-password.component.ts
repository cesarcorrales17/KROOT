import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  ReactiveFormsModule,
  FormBuilder,
  FormGroup,
  Validators,
} from '@angular/forms';
import { Router, ActivatedRoute, RouterLink } from '@angular/router';

import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { trigger, transition, style, animate } from '@angular/animations';

// RUTA CORREGIDA HACIA TU SERVICIO
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-reset-password',
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
  templateUrl: './reset-password.component.html',
  styleUrl: './reset-password.component.scss',
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
export class ResetPasswordComponent implements OnInit {
  resetForm: FormGroup;
  isLoading = false;
  hidePassword = true;
  token: string | null = null;

  successMessage = '';
  errorMessage = '';

  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private route = inject(ActivatedRoute);

  constructor() {
    this.resetForm = this.fb.group({
      new_password: [
        '',
        [
          Validators.required,
          Validators.minLength(8),
          Validators.pattern(
            /(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*(),.?":{}|<>])/,
          ),
        ],
      ],
    });
  }

  ngOnInit(): void {
    this.route.queryParams.subscribe((params) => {
      this.token = params['token'];
      if (!this.token) {
        this.errorMessage =
          'El enlace de recuperación no es válido o está incompleto.';
      }
    });
  }

  onSubmit(): void {
    if (this.resetForm.valid && this.token) {
      this.isLoading = true;
      this.errorMessage = '';
      this.successMessage = '';

      const newPassword = this.resetForm.get('new_password')?.value;

      this.authService.resetPassword(this.token, newPassword).subscribe({
        next: (response: any) => {
          // Añadido : any
          this.isLoading = false;
          this.successMessage =
            response.message || 'Contraseña actualizada con éxito.';
          this.resetForm.reset();
        },
        error: (err: any) => {
          // Añadido : any
          this.isLoading = false;
          if (err.status === 400 || err.status === 404) {
            this.errorMessage =
              err.error.detail ||
              'El enlace expiró o la contraseña es inválida.';
          } else {
            this.errorMessage =
              'Ocurrió un error en el servidor. Inténtalo más tarde.';
          }
        },
      });
    } else {
      this.resetForm.markAllAsTouched();
    }
  }
}
