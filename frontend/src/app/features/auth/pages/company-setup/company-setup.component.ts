import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { Router } from '@angular/router';

// MATERIAL DESIGN (Stepper y Formularios)
import { MatStepperModule } from '@angular/material/stepper';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

// SERVICIO
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-company-setup',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatStepperModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './company-setup.component.html',
  styleUrl: './company-setup.component.scss',
})
export class CompanySetupComponent implements OnInit {
  // LOS 4 PASOS DEL WIZARD
  step1Form: FormGroup;
  step2Form: FormGroup;
  step3Form: FormGroup;
  step4Form: FormGroup;

  isLoading = true; // Para la carga inicial
  isSaving = false; // Para el spinner del guardado automático

  // NUEVAS VARIABLES PARA LOS DATOS DINÁMICOS
  businessTypes: any[] = [];
  sectors: any[] = [];

  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private router = inject(Router);

  constructor() {
    // Paso 1: Información del negocio
    this.step1Form = this.fb.group({
      business_name: ['', Validators.required],
      business_type: ['', Validators.required],
    });

    // Paso 2: Sector o Industria
    this.step2Form = this.fb.group({
      industry: ['', Validators.required],
    });

    // Paso 3: Datos Financieros (Opcionales por si quieren saltar)
    this.step3Form = this.fb.group({
      estimated_income: [null],
      estimated_expenses: [null],
    });

    // Paso 4: Frecuencia
    this.step4Form = this.fb.group({
      tracking_frequency: ['', Validators.required],
    });
  }

  ngOnInit(): void {
    this.loadSectorsConfig(); // <-- 1. Cargamos las reglas (Sectores y Tipos)
    this.loadSavedProgress(); // <-- 2. Cargamos el progreso del usuario
  }

  // Consumir endpoint /business/sectors
  loadSectorsConfig(): void {
    this.authService.getBusinessSectors().subscribe({
      next: (data) => {
        this.sectors = data.sectors;
        this.businessTypes = data.business_types;
      },
      error: (err) => {
        console.error('Error al cargar sectores', err);
      },
    });
  }

  // Cargar datos si el usuario regresa
  loadSavedProgress(): void {
    this.authService.getBusinessSetup().subscribe({
      next: (data) => {
        // Rellenamos los formularios con lo que venga de la base de datos
        this.step1Form.patchValue(data);
        this.step2Form.patchValue(data);
        this.step3Form.patchValue(data);
        this.step4Form.patchValue(data);
        this.isLoading = false;
      },
      error: (err) => {
        // Si da error 404, significa que es un usuario 100% nuevo. No pasa nada.
        this.isLoading = false;
      },
    });
  }

  // TAREA: Guardado automático al avanzar
  saveStep(currentForm: FormGroup, isFinalStep: boolean = false): void {
    // Si el formulario es inválido, no hacemos petición al backend
    if (currentForm.invalid) {
      currentForm.markAllAsTouched();
      return;
    }

    this.isSaving = true;

    // Extraemos solo los datos de este paso
    const stepData = {
      ...currentForm.value,
      onboarding_completed: isFinalStep, // Si es el último paso, lo marcamos como completado
    };

    this.authService.updateBusinessSetup(stepData).subscribe({
      next: (response) => {
        this.isSaving = false;

        // Si fue el último paso, vamos al Dashboard
        if (isFinalStep) {
          this.router.navigate(['/dashboard']);
        }
      },
      error: (err) => {
        this.isSaving = false;
        console.error('Error al autoguardar', err);
      },
    });
  }
}
