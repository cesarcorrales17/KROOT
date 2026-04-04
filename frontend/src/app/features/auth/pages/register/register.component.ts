// IMPORTACIONES PRINCIPALES DE ANGULAR
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

// IMPORTACIÓN DEL SERVICIO DE AUTENTICACIÓN
import { AuthService } from '../../services/auth.service';

// IMPORTACIONES DE COMPONENTES DE MATERIAL DESIGN
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

// IMPORTACIONES PARA LAS ANIMACIONES DEL WIZARD
import {
  trigger,
  transition,
  style,
  animate,
  query,
  animateChild
} from '@angular/animations';

// CONFIGURACIÓN DEL COMPONENTE Y ANIMACIONES
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
    // ANIMACIÓN DE ENTRADA DE LA TARJETA PRINCIPAL
    trigger('fadeInUp', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(24px)' }),
        animate(
          '0.55s cubic-bezier(0.16, 1, 0.3, 1)',
          style({ opacity: 1, transform: 'translateY(0)' })
        )
      ])
    ]),
    // ANIMACIÓN DE TRANSICIÓN ENTRE PASOS DEL WIZARD
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

  // ESTADO DE LA INTERFAZ
  registerForm: FormGroup;
  isLoading = false;
  hidePassword = true;
  hideConfirmPassword = true;

  // VARIABLES PARA EL FEEDBACK VISUAL AL USUARIO
  errorMessage: string = '';
  successMessage: string = '';

  // CONTROL DEL WIZARD (PASOS DEL FORMULARIO)
  currentStep = 1;
  readonly totalSteps = 3;
  readonly stepTitles = ['Cuenta', 'Identidad', 'Confirmación'];

  // CAMPOS QUE PERTENECEN A CADA PASO — USADOS PARA VALIDAR ANTES DE AVANZAR
  private readonly stepFields: string[][] = [
    ['email', 'confirmEmail', 'password', 'confirmPassword'], // Paso 1
    ['documentType', 'documentNumber', 'fullName'],           // Paso 2
    []                                                        // Paso 3 — solo revisión
  ];

  // INYECCIÓN DE DEPENDENCIAS
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private authService = inject(AuthService);

  constructor() {
    // INICIALIZACIÓN DEL FORMULARIO CON SUS VALIDACIONES
    this.registerForm = this.fb.group(
      {
        // Campos del Paso 1
        email: ['', [Validators.required, Validators.email]],
        confirmEmail: ['', Validators.required],
        password: ['', [Validators.required, Validators.minLength(8)]],
        confirmPassword: ['', Validators.required],
        // Campos del Paso 2
        documentType: ['', Validators.required],
        documentNumber: ['', [Validators.required, Validators.pattern('^[0-9]*$')]],
        fullName: ['', [Validators.required, Validators.minLength(3)]]
      },
      {
        // VALIDADORES A NIVEL DE GRUPO — COMPRUEBAN QUE LOS PARES COINCIDAN
        validators: [
          this.matchValidator('email', 'confirmEmail'),
          this.matchValidator('password', 'confirmPassword')
        ]
      }
    );
  }

  // VALIDADOR PERSONALIZADO — COMPRUEBA QUE DOS CAMPOS TENGAN EL MISMO VALOR
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

  // CALCULA LA FORTALEZA DE LA CONTRASEÑA (0 = vacía, 1 = débil, 2 = regular, 3 = fuerte)
  get passwordStrength(): number {
    const pwd: string = this.registerForm.get('password')?.value ?? '';
    if (!pwd) return 0;
    let strength = 0;
    if (pwd.length >= 8) strength++;
    if (/[A-Z]/.test(pwd) && /[0-9]/.test(pwd)) strength++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(pwd)) strength++;
    return strength;
  }

  // DEVUELVE LA ETIQUETA TEXTUAL DE LA FORTALEZA PARA MOSTRAR EN EL HTML
  get strengthLabel(): string {
    const labels = ['', 'Contraseña débil', 'Contraseña regular', 'Contraseña fuerte'];
    return labels[this.passwordStrength] ?? '';
  }

  // VERIFICA SI TODOS LOS CAMPOS DEL PASO ACTUAL SON VÁLIDOS
  isCurrentStepValid(): boolean {
    const fields = this.stepFields[this.currentStep - 1];
    return fields.every(f => this.registerForm.get(f)?.valid);
  }

  // AVANZA AL SIGUIENTE PASO — SI HAY ERRORES, LOS MARCA COMO TOCADOS PARA MOSTRARLOS
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

  // RETROCEDE AL PASO ANTERIOR
  prevStep(): void {
    if (this.currentStep > 1) {
      this.currentStep--;
    }
  }

  // PROCESAMIENTO DEL FORMULARIO — COMUNICACIÓN CON EL BACKEND
  onSubmit(): void {
    if (this.registerForm.valid) {
      this.isLoading = true;
      this.errorMessage = '';
      this.successMessage = '';

      // FASTAPI SOLO NECESITA EMAIL Y PASSWORD — DESCARTAMOS LAS CONFIRMACIONES
      const userData = {
        email: this.registerForm.get('email')?.value,
        password: this.registerForm.get('password')?.value
      };

      this.authService.register(userData).subscribe({
        next: (response) => {
          this.isLoading = false;
          // ÉXITO — MOSTRAMOS EL MENSAJE PARA QUE EL USUARIO REVISE SU CORREO
          this.successMessage = '¡Cuenta creada con éxito! Hemos enviado un correo de verificación a tu bandeja de entrada.';
          // Opcional: resetear el formulario tras el registro exitoso
          // this.registerForm.reset();
        },
        error: (err) => {
          this.isLoading = false;

          // ERROR 400: CORREO DUPLICADO — LO ENVIAMOS DE VUELTA AL PASO 1
          if (err.status === 400) {
            this.errorMessage = err.error.detail || 'Este correo electrónico ya está registrado.';
            this.currentStep = 1;
          } else {
            // ERROR GENÉRICO — SERVIDOR CAÍDO O SIN CONEXIÓN
            this.errorMessage = 'Ocurrió un error en el servidor. Inténtalo más tarde.';
          }
        }
      });
    }
  }
}