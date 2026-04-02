import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  ReactiveFormsModule,
  FormBuilder,
  FormGroup,
  Validators,
  AbstractControl,
  ValidationErrors
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import {
  trigger,
  transition,
  style,
  animate,
  query,
  animateChild
} from '@angular/animations';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatButtonModule,
    MatSelectModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './register.component.html',
  styleUrl: './register.component.scss',
  animations: [
    trigger('fadeInUp', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(24px)' }),
        animate(
          '0.55s cubic-bezier(0.16, 1, 0.3, 1)',
          style({ opacity: 1, transform: 'translateY(0)' })
        )
      ])
    ]),
    trigger('stepFade', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateX(16px)' }),
        animate(
          '0.35s cubic-bezier(0.16, 1, 0.3, 1)',
          style({ opacity: 1, transform: 'translateX(0)' })
        )
      ]),
      transition(':leave', [
        animate(
          '0.2s ease-in',
          style({ opacity: 0, transform: 'translateX(-16px)' })
        )
      ])
    ])
  ]
})
export class RegisterComponent {
  registerForm: FormGroup;
  isLoading = false;
  hidePassword = true;
  hideConfirmPassword = true;

  // ── Multi-step state ──────────────────────────────────────────
  currentStep = 1;
  readonly totalSteps = 3;
  readonly stepTitles = ['Cuenta', 'Identidad', 'Confirmación'];

  /** Controls that belong to each step (used for validation gating) */
  private readonly stepFields: string[][] = [
    ['email', 'confirmEmail', 'password', 'confirmPassword'], // Step 1
    ['documentType', 'documentNumber', 'fullName'],           // Step 2
    []                                                        // Step 3 – review only
  ];

  private fb = inject(FormBuilder);
  private router = inject(Router);

  constructor() {
    this.registerForm = this.fb.group(
      {
        // Step 1
        email: ['', [Validators.required, Validators.email]],
        confirmEmail: ['', Validators.required],
        password: ['', [Validators.required, Validators.minLength(8)]],
        confirmPassword: ['', Validators.required],
        // Step 2
        documentType: ['', Validators.required],
        documentNumber: ['', [Validators.required, Validators.pattern('^[0-9]*$')]],
        fullName: ['', [Validators.required, Validators.minLength(3)]]
      },
      {
        validators: [
          this.matchValidator('email', 'confirmEmail'),
          this.matchValidator('password', 'confirmPassword')
        ]
      }
    );
  }

  // ── Validators ────────────────────────────────────────────────

  private matchValidator(source: string, target: string) {
    return (control: AbstractControl): ValidationErrors | null => {
      const src = control.get(source);
      const tgt = control.get(target);
      if (tgt?.errors && !tgt.errors['mismatch']) return null;
      if (src?.value !== tgt?.value) {
        tgt?.setErrors({ mismatch: true });
        return { mismatch: true };
      } else {
        tgt?.setErrors(null);
        return null;
      }
    };
  }

  // ── Password strength ─────────────────────────────────────────

  get passwordStrength(): number {
    const pwd: string = this.registerForm.get('password')?.value ?? '';
    if (!pwd) return 0;
    let strength = 0;
    if (pwd.length >= 8) strength++;
    if (/[A-Z]/.test(pwd) && /[0-9]/.test(pwd)) strength++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(pwd)) strength++;
    return strength;
  }

  get strengthLabel(): string {
    const labels = ['', 'Contraseña débil', 'Contraseña regular', 'Contraseña fuerte'];
    return labels[this.passwordStrength] ?? '';
  }

  // ── Step navigation ───────────────────────────────────────────

  isCurrentStepValid(): boolean {
    const fields = this.stepFields[this.currentStep - 1];
    return fields.every(f => this.registerForm.get(f)?.valid);
  }

  nextStep(): void {
    if (!this.isCurrentStepValid()) {
      this.stepFields[this.currentStep - 1].forEach(f =>
        this.registerForm.get(f)?.markAsTouched()
      );
      return;
    }
    if (this.currentStep < this.totalSteps) {
      this.currentStep++;
    }
  }

  prevStep(): void {
    if (this.currentStep > 1) {
      this.currentStep--;
    }
  }

  // ── Submit ────────────────────────────────────────────────────

  onSubmit(): void {
    if (this.registerForm.valid) {
      this.isLoading = true;
      // TODO: connect to FastAPI endpoint
      setTimeout(() => {
        this.isLoading = false;
        alert('¡Cuenta creada! Lista para conectar con FastAPI.');
      }, 1500);
    } else {
      this.registerForm.markAllAsTouched();
    }
  }
}