import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { RouterLink } from '@angular/router';

// MATERIAL DESIGN
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

// SERVICIO
import { AuthService } from '../../../../features/auth/services/auth.service';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './profile.component.html',
  styleUrl: './profile.component.scss',
})
export class ProfileComponent implements OnInit {
  profileForm: FormGroup;
  isLoading = true;
  isSaving = false;
  successMessage = '';
  errorMessage = '';

  sectors: any[] = []; // Cargaremos los sectores del backend

  // Opciones estáticas para tamaño y moneda
  businessSizes = [
    { value: 'micro', label: 'Micro (1-5 empleados)' },
    { value: 'small', label: 'Pequeña (6-50 empleados)' },
    { value: 'medium', label: 'Mediana (51-200 empleados)' },
  ];

  currencies = [
    { value: 'COP', label: 'Peso Colombiano (COP)' },
    { value: 'USD', label: 'Dólar Estadounidense (USD)' },
    { value: 'EUR', label: 'Euro (EUR)' },
    { value: 'MXN', label: 'Peso Mexicano (MXN)' },
  ];

  private fb = inject(FormBuilder);
  private authService = inject(AuthService);

  constructor() {
    this.profileForm = this.fb.group({
      business_name: ['', Validators.required],
      industry: ['', Validators.required],
      business_size: ['', Validators.required],
      currency: ['COP', Validators.required],
    });
  }

  ngOnInit(): void {
    this.loadSectors();
    this.loadProfileData();
  }

  loadSectors(): void {
    this.authService.getBusinessSectors().subscribe({
      next: (data) => (this.sectors = data.sectors),
      error: (err) => console.error('Error cargando sectores', err),
    });
  }

  loadProfileData(): void {
    this.authService.getBusinessProfile().subscribe({
      next: (data) => {
        this.profileForm.patchValue(data);
        this.isLoading = false;
      },
      error: (err) => {
        this.errorMessage = 'No se pudo cargar la información del perfil.';
        this.isLoading = false;
      },
    });
  }

  onSubmit(): void {
    if (this.profileForm.invalid) {
      this.profileForm.markAllAsTouched();
      return;
    }

    this.isSaving = true;
    this.successMessage = '';
    this.errorMessage = '';

    this.authService.updateBusinessProfile(this.profileForm.value).subscribe({
      next: (response) => {
        this.isSaving = false;
        this.successMessage =
          'Tus cambios se han guardado y el sistema se ha recalibrado con éxito.';

        // Ocultar mensaje después de 4 segundos
        setTimeout(() => (this.successMessage = ''), 4000);
      },
      error: (err) => {
        this.isSaving = false;
        this.errorMessage = 'Error al guardar los cambios. Intenta nuevamente.';
      },
    });
  }

  // EVENTO DE CERRAR SESIÓN
  logout(): void {
    this.authService.logout();
  }
}
